# Changelog for version 0.4.0 (API-candidate release on the road to 1.0)

## New features

  - getVolumes now reads decomposed cases (cells scattered back in the global
  order via cellProcAddressing); box and structured are not supported in this
  mode and raise NotImplementedError
  - **Parallel reading of decomposed cases** (`processor*`, `processors<N>`):
  new module-level setting `NTHREADS`, configurable through the
  `FLUIDFOAM_NTHREADS` environment variable or at runtime via
  `fluidfoam.readof.set_nthreads(n)`.
  - `0` or `1` (default): sequential reading (unchanged behaviour);
  - `n > 1`: at most `min(n, number of processors)` threads;
  - `n < 0`: automatic, `min(number of processors, 2 * cpu_count())`.
  The speed-up is significant for binary and gzipped cases (I/O and NumPy
  buffer conversions release the GIL); smaller for pure ASCII cases.

## Behaviour changes (breaking changes)

- **`sys.exit(1)` replaced by `ValueError`**: requesting a nonexistent
  `boundary` now raises `ValueError` instead of terminating the process.
  Scripts that relied on the implicit exit must catch the exception.
- **Messages go through `logging`**: the `print` calls (including the ANSI
  colour codes) are replaced by the `fluidfoam.readof` logger (silent by
  default). To get the messages back:
  `logging.basicConfig(level=logging.INFO)`. The `verbose` keyword of the
  reading functions still works as the simple on/off switch.
- `OpenFoamFile.dimensions` is now a `tuple` (was a `list`).
- Minimum supported Python version raised to 3.10 (3.8/3.9 are EOL);
  CI matrix is now 3.10-3.13.

## Bug fixes

- **Reading a `boundaryField` whose `value` is a multiline
  `nonuniform List<...>`** no longer crashes with `IndexError`
  (pre-existing bug); the patch data is now read correctly.

## Internal quality and robustness

- Removed the `eval()` call on file content (dimensions parsing):
  native parsing, no more arbitrary code execution from an OpenFOAM
  file.
- Bare `except:` clauses replaced with targeted exceptions.
- Factored out the duplicated field parsing (~95 lines) into
  `OpenFoamFile._parse_field_values`, used by `_parse_data` and
  `_nearest_data`.

## Documentation

- Module docstring extended: new sections "Parallel reading of
  decomposed cases", "Logging", "Errors" and "Precision of the read
  values" (the `np.around(precision=15)` rounding is intentional:
  blockMesh sometimes shifts mesh points slightly, which would break
  the structured-grid detection and the `structured=True` reshape).
- `set_nthreads` documented and exposed in the Sphinx reference.

## Notes for 1.0

- Freeze the public API (`readmesh`, `readfield`, `readscalar`,
  `readvector`, `readsymmtensor`, `readtensor`, `typefield`,
  `getVolumes`, `set_nthreads`).
- Formalize a deprecation policy: `DeprecationWarning` plus a
  two-release grace period.
- Tag `v1.0.0` once 0.4.0 has been in production for a few months
  without API breakage; GitHub release + PyPI, and optionally a Zenodo
  DOI for academic citation.
