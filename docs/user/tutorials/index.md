# Tutorials

Hands-on walkthroughs of complete edi workflows, ported from diffraction-lib: define or load a
project, refine or simulate, and inspect the results.

⛔ **Execution-disabled for now.** These notebooks are committed ahead of the API they exercise
(durability over runnability): each is excluded from notebook execution until the `C34` task
named in [`execution-exclusions.yml`](execution-exclusions.yml) lands, and the exclusion list
shrinks to empty as those tasks land. The pages below render the unexecuted notebooks.

| tutorial | what it shows |
| --- | --- |
| [refine-lbco-hrpt-from-data](refine-lbco-hrpt-from-data.ipynb) | Rietveld refinement of La0.5Ba0.5CoO3 (HRPT, constant wavelength), structure and experiment defined in code |
| [refine-si-sepd](refine-si-sepd.ipynb) | Si standard refinement (SEPD, time-of-flight) |
| [refine-ncaf-wish](refine-ncaf-wish.ipynb) | Joint multi-bank refinement of Na2Ca3Al2F14 (WISH) |
| [refine-cosio-d20-tscan](refine-cosio-d20-tscan.ipynb) | Sequential refinement over a D20 temperature scan (CoSiO) |
| [simulate-si-tof](simulate-si-tof.ipynb) | Forward simulation of a Si time-of-flight pattern |
