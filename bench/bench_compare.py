#!/usr/bin/env python3
"""Comparative reading benchmark: fluidfoam vs PyFoam vs Ofpp vs foamlib.

Protocol:
- 4 datasets (A: ASCII, B: binary, C: gzipped binary, D: decomposed 64 procs)
- median of N runs, warm cache; cold-cache runs optional
- peak memory via tracemalloc
- value equality check between tools (guard-rail against comparing
  different things)

Usage:
    python bench_compare.py --case /path/to/case --nproc 64 --runs 10
"""

import argparse
import os
import time
import statistics
import tracemalloc

import numpy as np

TOOLS = {}
TOOLS_DECOMPOSED = {"fluidfoam": lambda c, t, n: __import__("fluidfoam").readscalar(c, t, n)}

# ---------------------------------------------------------------- fluidfoam
try:
    import fluidfoam

    def read_fluidfoam(case, time, name):
        return fluidfoam.readscalar(case, time, name)

    def read_fluidfoam_decomposed(case, time, name):
        return fluidfoam.readscalar(case, time, name)

    TOOLS["fluidfoam"] = read_fluidfoam
except ImportError:
    pass

# ----------------------------------------------------------------- foamlib
try:
    from foamlib import FoamFieldFile

    def read_foamlib(case, time, name):
        path = os.path.join(case, time, name)
        # foamlib needs the explicit .gz path when the file is compressed
        if not os.path.exists(path) and os.path.exists(path + ".gz"):
            path += ".gz"
        f = FoamFieldFile(path)
        arr = np.asarray(f.internal_field)
        del f
        return arr

    # decomposed: foamlib has no transparent reconstruction, so read
    # per-processor and note the extra user code required (counted in time)
    def read_foamlib_decomposed(case, time, name):
        procs = sorted(
            (d for d in os.listdir(case) if d.startswith("processor")),
            key=lambda d: int(d[len("processor"):] or 0),
        )
        parts = []
        for p in procs:
            path = os.path.join(case, p, time, name)
            if not os.path.exists(path) and os.path.exists(path + ".gz"):
                path += ".gz"
            f = FoamFieldFile(path)
            parts.append(np.asarray(f.internal_field))
            del f
        return np.concatenate(parts)

    TOOLS["foamlib"] = read_foamlib
    TOOLS_DECOMPOSED["foamlib"] = read_foamlib_decomposed
except ImportError:
    pass

# ------------------------------------------------------------------- Ofpp
try:
    import ofpp

    def read_ofpp(case, time, name):
        return ofpp.parse_field(os.path.join(case, time, name))

    TOOLS["Ofpp"] = read_ofpp
except ImportError:
    pass

# ------------------------------------------------------------------ PyFoam
try:
    from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

    def read_pyfoam(case, time, name):
        f = ParsedParameterFile(os.path.join(case, time, name))
        # non-uniform List<scalar> payload
        val = f.content["internalField"] if isinstance(
            f.content, dict
        ) else None
        if val is None:
            raise RuntimeError("PyFoam: unexpected content structure")
        return np.asarray(val)

    TOOLS["PyFoam"] = read_pyfoam
except ImportError:
    pass


# ------------------------------------------------------------------- driver
def run_benchmark(reader, case, timename, fieldname, nruns):
    # Timing first, WITHOUT tracemalloc: it slows down allocations by an
    # order of magnitude and would bias the comparison between tools.
    times = []
    result = None
    for _ in range(nruns):
        t0 = time.perf_counter()
        result = reader(case, timename, fieldname)
        times.append(time.perf_counter() - t0)
    # Memory measured ONCE, separately, with tracemalloc.
    tracemalloc.start()
    result = reader(case, timename, fieldname)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "median_s": statistics.median(times),
        "min_s": min(times),
        "peak_mb": peak / 1e6,
        "shape": np.asarray(result).shape,
    }


def check_equality(results, tol=1e-12):
    """All tools that produced a result must agree bit-for-bit-ish."""
    names = list(results)
    for i in range(1, len(names)):
        a = np.asarray(results[names[0]])
        b = np.asarray(results[names[i]])
        if a.shape != b.shape:
            return f"shape mismatch {names[0]}{a.shape} vs {names[i]}{b.shape}"
        if not np.allclose(a, b, rtol=tol, atol=tol):
            return f"value mismatch between {names[0]} and {names[i]}"
    return "OK"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--time", default="latestTime", help="'latestTime' or e.g. '25'")
    ap.add_argument("--field", default="alpha")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--decomposed", action="store_true")
    ap.add_argument("--nproc", type=int, default=0)
    args = ap.parse_args()

    print(f"case={args.case} field={args.field} runs={args.runs}")
    print(f"tools available: {', '.join(TOOLS)}")
    if not TOOLS:
        raise SystemExit("no tool installed")

    # resolve 'latestTime'
    timename = args.time
    if timename == "latestTime":
        if args.decomposed:
            # time dirs live inside processorN/, e.g. processor0/0
            procs = sorted(d for d in os.listdir(args.case)
                           if d.startswith("processor"))
            if not procs:
                raise SystemExit(
                    f"no processorN dirs in {args.case}: not a decomposed case?"
                )
            scan = os.path.join(args.case, procs[0])
        else:
            scan = args.case
        dirs = [d for d in os.listdir(scan)
                if d[0].isdigit() and float(d) >= 0]
        if not dirs:
            raise SystemExit(f"no time directories found in {scan}")
        timename = max(dirs, key=float)
        print(f"latest time = {timename}")

    results = {}
    values = {}
    for name, reader in TOOLS.items():
        fn = reader
        if args.decomposed:
            fn = TOOLS_DECOMPOSED.get(name)
            if fn is None:
                print(f"{name}: skipped (no decomposed support)")
                continue
        try:
            r = run_benchmark(fn, args.case, timename, args.field, args.runs)
            results[name] = r
            values[name] = fn(args.case, timename, args.field)
            print(f"{name:12s} median={r['median_s']:.3f}s  "
                  f"min={r['min_s']:.3f}s  peak={r['peak_mb']:.1f}MB  "
                  f"shape={r['shape']}")
        except Exception as e:
            print(f"{name:12s} FAILED: {e}")

    if values:
        print("equality check:", check_equality(values))


if __name__ == "__main__":
    main()
