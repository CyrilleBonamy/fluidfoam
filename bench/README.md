# fluidfoam benchmark

Reproducible benchmark comparing OpenFOAM output reading performance of
fluidfoam against other Python tools (PyFoam, Ofpp, foamlib).

## Layout

```
bench/
    README.md                 # this file
    generate_bench_data.py    # writes the datasets into bench/data/
    bench_compare.py          # runs the comparative benchmark
    data/                     # generated datasets (gitignored)
        case_ascii/          # ASCII FoamFile, 1e6 cells
        case_binary/          # binary (LSB) FoamFile, 1e6 cells
        case_binary_gz/       # binary, whole file gzipped (alpha.gz)
        case_decomp/          # decomposed case, N processor dirs
```

## Protocol

Four datasets are generated purely from Python (no OpenFOAM installation
needed), each containing the same deterministic non-uniform scalar field
`alpha` (seeded RNG, reproducible bit-for-bit):

| Dataset | Format | What it exercises |
|---|---|---|
| `case_ascii` | ASCII | text parsing |
| `case_binary` | binary, LSB | binary decoding (zero-copy path) |
| `case_binary_gz` | binary + gzip | compressed reading |
| `case_decomp` | decomposed, N procs | transparent reconstruction |

The decomposed case uses contiguous chunks and includes the
`cellProcAddressing` / `faceProcAddressing` / `boundaryProcAddressing`
files that fluidfoam uses for global reconstruction.

Metrics measured by `bench_compare.py`:

- end-to-end wall time (median over N runs, warm cache)
- peak memory (`tracemalloc`)
- value equality across all tools (`np.allclose`, guard-rail against
  comparing different data)

## Usage

Generate the datasets (a few seconds for 10k cells, ~20 s for 1e6):

```bash
python bench/generate_bench_data.py --outdir bench/data --ncells 1000000 --nproc 64
```

Run the comparison (each tool is used only if installed):

```bash
pip install fluidfoam foamlib Ofpp PyFoam   # subset is fine

# reconstructed cases
python bench/bench_compare.py --case bench/data/case_ascii  --time 0 --runs 10
python bench/bench_compare.py --case bench/data/case_binary --time 0 --runs 10
python bench/bench_compare.py --case bench/data/case_binary_gz --time 0 --runs 10

# decomposed case (fluidfoam: one call; others: per-processor, timed
# including the assembly code)
python bench/bench_compare.py --case bench/data/case_decomp --decomposed --runs 10
```

Optional threaded reading for fluidfoam:

```bash
FLUIDFOAM_NTHREADS=8 python bench/bench_compare.py --case bench/data/case_decomp --decomposed
```

## Datasets are gitignored

`bench/data/` is excluded from the repository because it is large and
fully regenerable. Continuous integration regenerates a small version
(10k cells) and checks that all datasets are written and read back
identically (see `.github/workflows/bench.yml`).

## Notes for the JOSS paper

The numbers quoted in the paper's *Performance* section come from:

```bash
python bench/generate_bench_data.py --ncells 1000000 --nproc 64
python bench/bench_compare.py --case bench/data/case_binary --time 0 --runs 10
python bench/bench_compare.py --case bench/data/case_decomp --decomposed --runs 10
```

on the machine specified in the paper. Raw outputs are archived with the
release. When comparing with foamlib, note that it has no transparent
reconstruction of decomposed cases: the benchmark times the per-processor
reading *plus* the concatenation code, which is what a real user would
have to write.
