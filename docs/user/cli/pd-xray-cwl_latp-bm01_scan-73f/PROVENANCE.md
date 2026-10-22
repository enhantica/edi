# pd-xray-cwl_latp-bm01_scan-73f — provenance

The owner's LATP project: 73 constant-wavelength synchrotron X-ray patterns (λ = 0.69687 Å) measured on BM01 at SNBL,
fitted in sequence with three phases, Li1.3Al0.3Ti1.7(PO4)3 (R-3c) and two AlPO4 phases (C222₁ and P6₃mc). The owner
made it in edi's app and gave it to edi for its examples on 2026-10-22.

## What changed from the owner's project

Only naming and session state; every parameter value, free flag, constraint and data point is as the owner left it.

- `project.edi`: the name, title and description follow the other examples (`pd_xray_cwl_latp_bm01_scan_73f`,
  "LATP [R-3c] / AlPO₄ [C222₁] / AlPO₄ [P6₃mc] · BM01 @ SNBL"), with the instrument BM01, the facility SNBL and the
  example tags. The creation and modification dates and the uncertainty format are kept.
- `analysis/analysis.edi`: the last fit's results (`_fit_result`, `_fit_result_bank`, `_fit_result_phase`), its start
  values (`_fit_parameter`) and its correlations are removed; the fitting mode, aliases, constraints and scan settings
  are kept.
- Removed files: `analysis/.edi-set-aside/`, `analysis/scan-run.json`, `analysis/scan-notes.csv`,
  `analysis/results-provenance.csv`, `analysis/results.csv` and the empty `reports/` folder.
- `experiments/bm01_scan/*.dat`: each file's header line naming its path on the facility's file system is removed;
  the data lines are unchanged.

`structures/` and `experiments/bm01.edi` are byte-identical to the owner's.
