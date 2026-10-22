---
title: CLI projects
description: >-
  Complete edi projects you fit from the command line with python -m edi, each checked in CI
  against its expected results.
---

# CLI projects

Complete projects you can fit from the command line — structure, experiments with their
measured data, and the analysis settings, in one directory:

```bash
python -m edi fit docs/user/cli/<project>/project --dry
```

Every project here also carries an `expected.json`, and CI and `pixi run verify` run each one
through `python -m edi` on every pull request and compare the results: a project in the
executing set is known to fit the way it says. Every project here is in it. The set grows with edi — a new feature adds a project or extends
one that exercises it.

⛔ The first nine are edi's internal fitting-regression cases, copied from crysta's fitting corpus;
whether they are the right user-facing examples is still open. Their expected values are mostly
**regression pins** (they catch drift, not errors); each page and `PROVENANCE.md` says which values
are independent references.

| project | what it fits |
| --- | --- |
| [pd-neut-cwl_cosio-d20_start-1](pd-neut-cwl_cosio-d20_start-1/index.md) | Co2SiO4 on D20 (constant wavelength), 43 parameters, start-1 |
| [pd-neut-cwl_cosio-d20_start-4](pd-neut-cwl_cosio-d20_start-4/index.md) | the same fit from start-4 |
| [pd-neut-cwl_cosio-d20_scan-3f](pd-neut-cwl_cosio-d20_scan-3f/index.md) | Co2SiO4 sequential scan over three D20 temperatures |
| [pd-neut-cwl_cosio-d20_scan-162f](pd-neut-cwl_cosio-d20_scan-162f/index.md) | Co2SiO4 sequential scan over 162 D20 files, cooling |
| [pd-neut-cwl_cosio-d20_scan-324f](pd-neut-cwl_cosio-d20_scan-324f/index.md) | Co2SiO4 sequential scan over 324 D20 files, down and up |
| [pd-neut-cwl_lbco-hrpt_start-2](pd-neut-cwl_lbco-hrpt_start-2/index.md) | La0.5Ba0.5CoO3 on HRPT (constant wavelength), 17 parameters (preferred orientation), start-2 |
| [pd-neut-cwl_lbco-hrpt_start-4](pd-neut-cwl_lbco-hrpt_start-4/index.md) | the same fit from start-4 |
| [pd-neut-tof_ncaf-wish-2bank_start-3](pd-neut-tof_ncaf-wish-2bank_start-3/index.md) | Na2Ca3Al2F14 joint two-bank WISH (time of flight), 20 parameters |
| [pd-neut-tof_ncaf-wish-3bank_start-5](pd-neut-tof_ncaf-wish-3bank_start-5/index.md) | Na2Ca3Al2F14 joint three-bank WISH, 108 parameters, FullProf-verified |
| [pd-neut-tof_si-sepd_start-2](pd-neut-tof_si-sepd_start-2/index.md) | Si on SEPD (time of flight), 23 parameters, start-2 |
| [pd-neut-tof_si-sepd_start-5](pd-neut-tof_si-sepd_start-5/index.md) | the same fit from start-5 |
| [pd-neut-tof_diamond-dream_basic](pd-neut-tof_diamond-dream_basic/index.md) | diamond on DREAM (time of flight), scale only, against FullProf |
| [pd-neut-cwl_lab6-echidna_fcj-asymmetry](pd-neut-cwl_lab6-echidna_fcj-asymmetry/index.md) | LaB6 on Echidna (constant wavelength), FCJ asymmetry, scale only, against FullProf |
| [pd-neut-cwl_pbso4_beba-asymmetry](pd-neut-cwl_pbso4_beba-asymmetry/index.md) | PbSO4 on D1A (constant wavelength), the pseudo-Voigt with Bérar-Baldinozzi asymmetry, profile and scale re-fitted |
| [pd-neut-cwl_yap-spodi_3k](pd-neut-cwl_yap-spodi_3k/index.md) | YAlO3 and Al2O3 on SPODI (constant wavelength), two phases, pseudo-Voigt with Bérar-Baldinozzi, against FullProf |
| [pd-neut-tof_fe_pseudo-voigt](pd-neut-tof_fe_pseudo-voigt/index.md) | ferrite on BEER (time of flight), TOF pseudo-Voigt, scale only, against FullProf |
| [pd-neut-tof_cecoal-polaris_chebyshev](pd-neut-tof_cecoal-polaris_chebyshev/index.md) | CeCoAl3 on POLARIS (time of flight), Chebyshev background, 32 parameters, against FullProf |
| [pd-neut-tof_ceo2-pearl_polynomial](pd-neut-tof_ceo2-pearl_polynomial/index.md) | CeO2 on PEARL (time of flight), polynomial background, 19 parameters, against FullProf |
| [pd-neut-cwl_lab6-11b-echidna_tch-fcj](pd-neut-cwl_lab6-11b-echidna_tch-fcj/index.md) | 11B LaB6 on ECHIDNA (constant wavelength), TCH x FCJ, polynomial background, 17 parameters, against FullProf |
| [pd-xray-cwl_lif_single](pd-xray-cwl_lif_single/index.md) | LiF with Cu Kα X-rays (constant wavelength), the doublet's intensity ratio and the absorption's muR, against FullProf |
| [pd-xray-cwl_pbso4-lab_round-robin](pd-xray-cwl_pbso4-lab_round-robin/index.md) | PbSO4 from the X-ray round robin (constant wavelength), the Kα doublet and the pseudo-Voigt with Bérar-Baldinozzi asymmetry, profile and scale fitted |
| [pd-neut-cwl_y2o3_beta-adp](pd-neut-cwl_y2o3_beta-adp/index.md) | Y2O3 (constant wavelength), anisotropic beta ADPs tied by site symmetry, scale only, against FullProf |
| [pd-xray-cwl_latp_scan-4f](pd-xray-cwl_latp_scan-4f/index.md) | LATP with two AlPO4 phases, synchrotron X-ray sequential scan over four files, 54 parameters, against FullProf |

The single-crystal projects below reproduce diffraction-lib's verification pages against FullProf's fits; all five execute, and the three app examples are registered without reference values.

| project | what it fits |
| --- | --- |
| [sc-neut-cwl_pr2nio4-5c2_basic](sc-neut-cwl_pr2nio4-5c2_basic/index.md) | Pr2NiO4 single crystal (constant wavelength), anisotropic displacements, scale only |
| [sc-neut-cwl_tb2ti2o7-heidi_basic](sc-neut-cwl_tb2ti2o7-heidi_basic/index.md) | Tb2Ti2O7 on HEiDi (constant wavelength), scale only |
| [sc-neut-cwl_tb2ti2o7-heidi_anisotropic-adp](sc-neut-cwl_tb2ti2o7-heidi_anisotropic-adp/index.md) | Tb2Ti2O7 on HEiDi, anisotropic displacements, scale only |
| [sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction](sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction/index.md) | Tb2Ti2O7 on HEiDi, Becker-Coppens extinction, scale and crystal radius |
| [sc-neut-tof_taurine-unknown_basic](sc-neut-tof_taurine-unknown_basic/index.md) | taurine single crystal (time of flight), scale only |
| [sc-neut-cwl_tb2ti2o7-heidi_fit](sc-neut-cwl_tb2ti2o7-heidi_fit/index.md) | Tb2Ti2O7 on HEiDi from a rough start (app example) |
| [sc-neut-cwl_pr2nio4-5c2_fit](sc-neut-cwl_pr2nio4-5c2_fit/index.md) | Pr2NiO4 on 5C2 from a rough start (app example) |
| [sc-neut-tof_taurine_fit](sc-neut-tof_taurine_fit/index.md) | taurine (time of flight) from a rough start (app example) |

The registry of projects and which of them execute is [`projects.yml`](projects.yml).

The measured runtime of each executing project is banked in [`runtimes.tsv`](runtimes.tsv)
(`python tools/checks/cli_projects.py --bank docs/user/cli/runtimes.tsv`).
