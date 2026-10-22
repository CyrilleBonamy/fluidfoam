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
    affiliation: 2
    orcid: '0000-0002-5979-0620'
  - name: 'Quentin Clemencot'
    affiliation: 3
  - name: 'Eduard Puig Montellà'
    affiliation: 4
    orcid: '0000-0001-7184-0945'
  - name: 'Rémi Chassagne'
    affiliation: 1
    orcid: '0000-0002-6448-7909'
affiliations:
  - index: 1
    name: Université Grenoble Alpes, CNRS, LEGI, Grenoble, France
    ror: '02rx3b187'
  - index: 2
    name: Université Grenoble Alpes, INRAE, IRD, CNRS, IGE, Grenoble, France
    ror: '02rx3b187'
  - index: 3
    name: Alstom, France
    ror: '00t4db855'
  - index: 4
    name: Centro Oceanográfico de Canarias, Instituto Español de Oceanografía,Consejo Superior de Investigaciones Científicas (IEO-CSIC), Santa Cruz de Tenerife, Spain 
    ror: '0580ctc67'
date: '1 November 2026'
bibliography: paper.bib
---

# Summary

Computational fluid dynamics (CFD) researchers often use OpenFOAM
[@openfoam; @opencfd], an open-source toolbox distributed by two
organisations sharing a common file format, to simulate flows such as
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
compute statistics and spectra, to apply modal decompositions to snapshot
matrices, and to couple simulation output with data-driven workflows.

fluidfoam is designed for researchers and students who need scriptable,
reproducible post-processing of OpenFOAM results: research groups running
parametric studies, teachers preparing course material, and analysts on
machines where OpenFOAM itself is not installed. Studies of canonical flows
typically read tens to hundreds of time steps of several fields, often from
decomposed parallel runs stored on network file systems, so reading files
is a large share of the analysis time; the package aims to keep this cost
modest and to hide the bookkeeping of parallel layouts from the user.

# State of the field

Several Python tools address OpenFOAM data, with different emphases. PyFoam
[@gschaider2023] focuses on case configuration and running rather than
analytical post-processing. Ofpp [@xianghua2023] is a minimal reader that
appears to be no longer actively maintained (no commit since August 2023).
fluidsimfoam [@augier2025] sets up and runs simulations within the fluidsim
framework, relying on HDF5 output rather than native OpenFOAM files. foamlib
[@gerlero2025] is a comprehensive, fully type-hinted library for interacting
with OpenFOAM files and running cases, including asynchronous and Slurm-based
execution. Turbulucid [@mukha2019] provides scripted post-processing and
plotting of plane 2D simulations based on VTK. Generic readers such as the
OpenFOAM reader of ParaView, accessible from Python through PyVista
[@sullivan2019], give access to cases through the VTK data model. A different
approach is taken by PythonFOAM [@maulik2021] and by embedded-interpreter
approaches [@rodriguez2022], which call Python from within the solver for
in-situ analysis;
these require compiling against OpenFOAM and are complementary to the offline
post-processing addressed here.

To our knowledge, fluidfoam offers a specific combination of features that
is not found together in these tools: (i) reconstruction of decomposed
parallel cases directly into global, ordered fields; (ii) automatic reshaping of
structured meshes into multi-dimensional arrays; and (iii) a minimal
dependency footprint (NumPy and SciPy only), which matters for shared
analysis scripts, teaching, and continuous integration.
These tools are largely complementary: a workflow may use foamlib or
fluidsimfoam to launch simulations and fluidfoam to analyse their output.

# Software design

The package is organised in layers. The reading functions (fields, meshes,
patches) form the low-level core; on top of them, an OpenFoamSimu class
loads, in one step, all fields saved at a given time step of a simulation
(or of any simulation found in a directory tree), which is the typical entry
point for exploratory analysis; and specialised modules handle
postProcessing function-object output, 1D profile generation for boundary
conditions, and mesh design and visualisation for simple configurations —
including the generation of vector figures (SVG, PDF) of 2D meshes via
Matplotlib [@hunter2007] line collections, for publication-quality mesh
illustrations.

Three further design choices structure the core. First, it is a standalone
reader: it does not wrap OpenFOAM commands and does not link to the
OpenFOAM C++ API. It reads the file format shared by the two OpenFOAM
distributions (the OpenFOAM Foundation and OpenCFD), which removes any
dependence on a particular version or distribution, at the cost of
maintaining a parser for the OpenFOAM file format — a cost kept low because
the format is stable and because the parser handles ASCII, binary (either byte
order, taken from the FoamFile header), and gzip-compressed files uniformly.

Second, decomposed parallel cases (uncollated and collated layouts) are
reconstructed transparently using the cell, face, and boundary addressing
files that OpenFOAM writes at decomposition time, so the same call returns
identical arrays for reconstructed and decomposed data, and this
reconstruction is shared by all layers. This correctness-critical path is
validated in the test suite against reconstructed references.

Third, a benchmark released with the package compares reading times with
foamlib and PyFoam on fields of $10^6$ cells (warm file cache, one machine).
fluidfoam is not the fastest reader: a binary field is read in 32 ms
(median), against 3 ms for foamlib and 3.9 s for PyFoam, and a decomposed
case in 0.43–0.61 s (minimum–median), against 0.27 s for foamlib. Its
contribution lies in the combination of features described above, at a cost
that remains small for typical analyses. The benchmark also indicates that
reading time of large binary fields is dominated by file input rather than
decoding, which motivated optional multi-threaded reading of decomposed
cases (bit-exact results), and yields practical guidance: write results in
binary format and load each time series once.

# Research impact statement

fluidfoam has been developed since 2017 and is the post-processing layer
of SedFoam [@chauchat2017], a two-phase-flow sediment-transport model
used in morphodynamics research. It has been used in the post-processing of simulations for studies of
unsteady effects in oscillatory sheet flows [@mathieu2022], finite-size
effects in two-fluid large-eddy simulation of particle-laden boundary layers
[@mathieu2021], a frictional–collisional model for bedload transport
[@chassagne2023], the three-phase solver sedInterFoam [@mathieu2025], an
Exner diagnosis method for two-fluid morphodynamics simulations
[@gilletta2026], and the Exner-based morphodynamics model sedExnerFoam
[@renaud2026].
It is also the interface for reading OpenFOAM output in the
SedFoam tutorials [@sedfoamdoc].

Beyond its developers' group, the package is distributed on PyPI and
conda-forge. As of 22 October 2026, it totals over 125,000 downloads from PyPI
since its first release, about 800 per month over the last month with mirrors
excluded, and 376 downloads from conda-forge over the last six months.
Its GitHub repository has 201 stars and 54 forks, and a Google Scholar
full-text search finds it mentioned in 36 publications (after removing
homonyms). Third-party uses include a tidal-flow monopile scour solver
unrelated to SedFoam, in which fluidfoam reads the velocity and pressure
fields at the end of each half tidal cycle to initialise the next one
[@liu2024]; a machine-learning study of transient flow prediction around airfoils,
where fluidfoam extracts the grid and the dynamic flow-field data from the
numerical simulations [@xie2024]; the independent package openfoam-postprocessing [@martins2025]; and a series of
independent tutorials on proper orthogonal decomposition of OpenFOAM snapshots
[@goswami2024; @goswami2025], on function-object post-processing
[@goswami2024fo] and on extracting and analysing OpenFOAM data
[@goswami2024dive]. It is also listed in
a survey of open-source CFD tools [@kodman2024].
The Sphinx-Gallery example gallery and the benchmark datasets provide
reproducible materials for new users.

# AI usage disclosure

In accordance with the JOSS AI usage policy, we disclose the following use
of generative AI. Two assistants were used: the Mistral AI "Vibe Code" agent
(model zai-glm-5-3) and Anthropic's
Claude (model Claude Sonnet 5.5).

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
