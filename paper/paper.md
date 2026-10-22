---
title: 'fluidfoam: from OpenFOAM cases to NumPy arrays in one call'
tags:
  - fluid dynamics
  - CFD
  - post-processing
  - OpenFOAM
  - Python
authors:
  - name: Cyrille Bonamy
    affiliation: 1
    orcid: '0000-0003-3868-7090'
  - name: 'Julien Chauchat'
    affiliation: '[2]'
affiliations:
  - index: 1
    name: Université Grenoble Alpes, CNRS, LEGI, Grenoble, France
    ror: 'https://ror.org/02rx3b187'
  - index: 2
    name: Université Grenoble Alpes, INRAE, CNRS, IGE, Grenoble, France
    ror: 'https://ror.org/02rx3b187'
date: '1 November 2026'
bibliography: paper.bib
---

# Summary

Computational fluid dynamics (CFD) researchers often use OpenFOAM
[@openfoam], a widely adopted open-source toolbox, to simulate flows such as
turbulent currents, sediment transport in rivers, or erosion around marine
structures. Each simulation produces large output files in OpenFOAM's own
file format, which must then be analysed to compute statistics, plot
profiles, or compare with experiments. fluidfoam is a Python package that
reads these output files directly, converting meshes and flow fields into
NumPy arrays [@harris2020], the standard array format of the scientific
Python ecosystem, in a single function call. It requires neither an OpenFOAM
installation nor conversion to intermediate formats, and runs on a laptop
analysing data copied from a supercomputer. Results from parallel
simulations, which are split across multiple directories, are reassembled
transparently. Beyond reading, fluidfoam processes the outputs of OpenFOAM
function objects (forces, probes), writes and reads 1D profiles for
boundary-condition imposition via swak4Foam [@swak4foam], and generates mesh
dictionaries for simple configurations. The package is pure Python, depends
only on NumPy and SciPy [@virtanen2020], and is released under GPL-3.0.

# Statement of need

Post-processing is a significant fraction of the working time of CFD
researchers. The native OpenFOAM toolchain is oriented towards interactive
visualisation in ParaView [@paraview] or requires converting data to
intermediate formats (VTK, HDF5) before analysis. Many practitioners instead
analyse results in Python, where the scientific ecosystem makes it easy to
compute statistics and spectra, and to couple simulation output with
data-driven workflows.

fluidfoam is designed for researchers and students who need scriptable,
reproducible post-processing of OpenFOAM results: research groups running
parametric studies, teachers preparing course material, and analysts on
machines where OpenFOAM itself is not installed. Studies of canonical flows
typically read tens to hundreds of time steps of several fields, so
per-call overhead dominates the analysis cost; the package is built to keep
that cost low.

# State of the field

Several Python tools address OpenFOAM data, with different emphases. PyFoam
[@gschaider2023] focuses on case configuration and running rather than
analytical post-processing. Ofpp [@xianghua2023] is a minimal reader that is
no longer actively maintained. fluidsimfoam [@augier2025] sets up and runs
simulations within the fluidsim framework, relying on HDF5 output rather
than native OpenFOAM files. foamlib [@gerlero2025] is a comprehensive,
fully type-hinted library for interacting with OpenFOAM files and running
cases, including asynchronous and Slurm-based execution.

fluidfoam contributes a specific combination that alternatives do not
provide together: (i) transparent reconstruction of decomposed parallel
cases directly into global, ordered fields, in a single call and with no
user-side bookkeeping; (ii) automatic reshaping of structured meshes into
multi-dimensional arrays; and (iii) a minimal dependency footprint (NumPy
and SciPy only), which matters for shared analysis scripts, teaching, and
continuous integration. Existing alternatives either require per-processor
assembly code from the user, do not reshape structured meshes, or pull in
heavier dependencies. These tools are largely complementary: a workflow may
use foamlib or fluidsimfoam to launch simulations and fluidfoam to analyse
their output.

# Software design

The package is organised in layers. The reading functions (fields, meshes,
patches) form the low-level core; on top of them, an OpenFoamSimu class
loads, in one step, all fields saved at a given time step of a simulation
(or of any simulation found in a directory tree), which is the typical entry
point for exploratory analysis; and specialised modules handle
postProcessing function-object output, 1D profile generation for boundary
conditions, and mesh design and visualisation for simple configurations —
including the generation of vector figures (SVG, PDF) of 2D meshes via
Matplotlib line collections, for publication-quality mesh illustrations.

Three further design choices structure the core. First, it is a standalone
reader: it does not wrap OpenFOAM commands and does not link to the
OpenFOAM C++ API. This removes any dependence on a particular OpenFOAM
version or distribution, at the cost of maintaining a parser for the
OpenFOAM file format — a cost kept low because the format is stable and
because the parser handles ASCII, binary (either byte order, taken from the
FoamFile header), and gzip-compressed files uniformly.

Second, decomposed parallel cases (uncollated and collated layouts) are
reconstructed transparently using the cell, face, and boundary addressing
files that OpenFOAM writes at decomposition time, so the same call returns
identical arrays for reconstructed and decomposed data, and this
reconstruction is shared by all layers. This correctness-critical path is
validated in the test suite against reconstructed references.

Third, performance was measured, not assumed: a benchmark released with
the package shows that reading time of large binary fields is dominated by
file input rather than decoding, which motivated zero-copy NumPy decoding
of binary payloads and optional multi-threaded reading of decomposed cases
(bit-exact results, wall-clock gains on parallel network file systems such
as Lustre). The benchmark also yields practical guidance: write results in
binary format and load each time series once.

# Research impact statement

fluidfoam has been developed since 2017 and is the post-processing layer
of SedFoam [@chauchat2017], a two-phase-flow sediment-transport model
widely used in morphodynamics research. It enabled, among others, the
numerical investigation of unsteady effects in oscillatory sheet flows
[@mathieu2022] and studies of scour and erosion around marine structures.
The package is used in research groups working on turbulent,
sediment-transport, and gravity-current flows, in teaching, and in external
projects — for example, it is the interface for reading OpenFOAM output in
the SedFoam tutorial suite and in machine-learning datasets built from
OpenFOAM simulations. The Sphinx-Gallery example gallery and the benchmark
datasets provide reproducible materials for new users.

# AI usage disclosure

In accordance with the JOSS AI usage policy, we disclose the following use
of generative AI. Two assistants were used: the Mistral AI "Vibe Code" agent
(model zai-glm-5-3) and Anthropic's Claude (model Claude Sonnet 5.5).

- *Paper text:* drafting and copy-editing of sections of this manuscript
  from source material provided by the authors.
- *Benchmark code:* generation of the comparative benchmark scripts and of
  synthetic OpenFOAM-format test datasets, with iterative debugging against
  real OpenFOAM output files.
- *Software:* the most recent changes to the fluidfoam codebase —
  essentially the transparent support of decomposed cases and the optional
  multi-threaded reading — were made with AI assistance.
- *Documentation:* restructuring of the benchmark documentation.

AI was not used for interactions with editors or reviewers. The human
authors reviewed and validated all AI-assisted outputs, ran the benchmarks
on their own hardware, verified the reported numbers, and made all design
decisions. All modified code is covered by the package's test suite and
continuous integration. The authors remain fully responsible for the
accuracy, originality, licensing, and ethical and legal compliance of all
submitted materials.

# Acknowledgements

The OpenFOAM simulations whose post-processing motivated and shaped
fluidfoam were performed using HPC resources provided by GENCI (Grand
Équipement National de Calcul Intensif) under projects A0160107567,
A0172A14636, A0180107567, A0192A14636 and A0212A14636.
We are thankful to the developers involved in OpenFOAM.

# References
