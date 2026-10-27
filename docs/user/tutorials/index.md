# Tutorials

One tutorial for each example: it loads the example's project with `edi.Project.load` and works through it with
edi's Python API, from the model to the fit and the report. The same project is the one the command line fits and
the app opens.

The tutorials are not run when the documentation is built yet: they load their projects from the edi repository,
and run once a tutorial runner can provide the projects elsewhere. [`execution-exclusions.yml`](execution-exclusions.yml)
lists each one with what it waits for.

## Calculations without data

| tutorial | what it shows |
| --- | --- |
| [Calculation without data: La₀.₅Ba₀.₅CoO₃, HRPT](pd-neut-cwl_lbco_simulation.ipynb) | La₀.₅Ba₀.₅CoO₃ [Pm-3m] · HRPT @ PSI |
| [Calculation without data: Si, time of flight](pd-neut-tof_si_simulation.ipynb) | Silicon [Fd-3m] · SEPD @ Argonne |
| [Calculation without data: NaCl, laboratory X-ray](pd-xray-cwl_nacl_simulation.ipynb) | NaCl [Fm-3m] · Laboratory X-ray |

## Constant-wavelength neutron

| tutorial | what it shows |
| --- | --- |
| [Rietveld fit: La₀.₅Ba₀.₅CoO₃, HRPT](pd-neut-cwl_lbco-hrpt.ipynb) | La₀.₅Ba₀.₅CoO₃ [Pm-3m] · HRPT @ PSI |
| [Rietveld fit: herbertsmithite, HRPT](pd-neut-cwl_hs-hrpt.ipynb) | ZnCu₃(OD)₆Cl₂ [R-3m] · HRPT @ PSI |
| [Rietveld fit: Co₂SiO₄, D20](pd-neut-cwl_cosio-d20.ipynb) | Co₂SiO₄ [Pnma] · D20 @ ILL |
| [Rietveld fit: LiNiO₂, ECHIDNA](pd-neut-cwl_lmo-echidna.ipynb) | LiNiO₂ [R-3m] · ECHIDNA @ ANSTO |
| [Rietveld fit: Y₂O₃, SPODI](pd-neut-cwl_y2o3-spodi.ipynb) | Y₂O₃ [Ia-3] · SPODI @ FRM II |
| [Two-phase fit: YAlO₃ and Al₂O₃, SPODI](pd-neut-cwl_yalo3-al2o3-spodi.ipynb) | YAlO₃ [Pbnm] / Al₂O₃ [R-3c] · SPODI @ FRM II |

## Time-of-flight neutron

| tutorial | what it shows |
| --- | --- |
| [Rietveld fit: Si, SEPD](pd-neut-tof_si-sepd.ipynb) | Silicon [Fd-3m] · SEPD @ Argonne |
| [Rietveld fit: CeCoAl₃, POLARIS](pd-neut-tof_cecoal-polaris.ipynb) | CeCoAl₃ [Pmma] · POLARIS @ ISIS |
| [Calibration fit: CeO₂, PEARL](pd-neut-tof_ceo2-pearl.ipynb) | CeO₂ [Fm-3m] · PEARL @ ISIS |
| [Two-phase fit: La₀.₅Ba₀.₅CoO₃ and Si, McStas](pd-neut-tof_lbco-si-mcstas.ipynb) | La₀.₅Ba₀.₅CoO₃ [Pm-3m] / Silicon [Fd-3m] · McStas simulation |
| [Joint fit: Na₂Ca₃Al₂F₁₄, WISH](pd-neut-tof_ncaf-wish.ipynb) | Na₂Ca₃Al₂F₁₄ [I2₁3] · WISH @ ISIS |
| [Joint fit: ferrite and austenite, BEER](pd-neut-tof_ferrite-austenite-beer.ipynb) | Ferrite [Im-3m] / Austenite [Fm-3m] · BEER @ ESS |

## X-ray

| tutorial | what it shows |
| --- | --- |
| [Rietveld fit: PbSO₄, laboratory X-ray](pd-xray-cwl_pbso4-lab.ipynb) | PbSO₄ [Pnma] · Laboratory X-ray |
| [Rietveld fit: high-entropy perovskite, P02.1](pd-xray-cwl_lam7o3-p021.ipynb) | La(Ti,Cr,Mn,Fe,Co,Ni,Cu)O₃ [Pnma] · P02.1 @ PETRA III |

## Neutron and X-ray joint

| tutorial | what it shows |
| --- | --- |
| [Joint fit: PbSO₄, neutron and X-ray](pd-neut-xray-cwl_pbso4-d1a-lab.ipynb) | PbSO₄ [Pnma] · D1A @ ILL and laboratory X-ray |

## Scans

| tutorial | what it shows |
| --- | --- |
| [Sequential fit: Co₂SiO₄, D20 temperature scan](pd-neut-cwl_cosio-d20_scan.ipynb) | Co₂SiO₄ [Pnma] · D20 @ ILL |
| [Sequential fit: LATP, BM01](pd-xray-cwl_latp-bm01_scan.ipynb) | LATP [R-3c] / AlPO₄ [C222₁] / AlPO₄ [P6₃mc] · BM01 @ ESRF |

## Single crystal

| tutorial | what it shows |
| --- | --- |
| [Single-crystal fit: Tb₂Ti₂O₇, HEiDi](sc-neut-cwl_tb2ti2o7-heidi.ipynb) | Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II) |
| [Single-crystal fit: Pr₂NiO₄, 5C2](sc-neut-cwl_pr2nio4-5c2.ipynb) | Pr₂NiO₄ [Fmmm] · 5C2 @ LLB |
| [Single-crystal fit: taurine, SENJU](sc-neut-tof_taurine-senju.ipynb) | Taurine [P2₁/c] · SENJU @ J-PARC |
