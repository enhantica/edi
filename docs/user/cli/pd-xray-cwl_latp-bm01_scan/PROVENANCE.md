# pd-xray-cwl_latp-bm01_scan — provenance

The owner's LATP project: 73 constant-wavelength synchrotron X-ray patterns (λ = 0.69687 Å) measured on BM01 at SNBL,
fitted in sequence with three phases, Li1.3Al0.3Ti1.7(PO4)3 (R-3c) and two AlPO4 phases (C222₁ and P6₃mc). The owner
made it in edi's app and gave it to edi for its examples on 2026-10-22.

## What changed from the owner's project

Naming, session state and the template dataset; every free flag, constraint, excluded region and scan data point is as
the owner left it, and every parameter value is one of his fitted values.

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

- The template: the owner's `experiments/bm01.edi` still held the data of an earlier file, `latp_001.dat`, on an
  intensity scale about 40 times below the scan files, with the values fitted to it, while the scan's template file
  was `latp_312.dat`. Opened, that template's calculation sat about 40 times below its measured pattern. The template
  experiment now holds `latp_312.dat`'s data (`_data_source.file_name latp_312.dat`), and every free value in
  `structures/` and `experiments/bm01.edi` is the owner's own fit of `latp_312.dat`, from the scan results his
  session wrote (73 files, one row each), at the uncertainty rule's precision as edi saves them. A single fit of the
  template then converges in 5 iterations to R<sub>wp</sub> 4.51 % and reduced χ² 1.4223·10⁸ (his run: 1.4226·10⁸),
  and the sequential run reproduces his reduced χ² for every file within 2·10⁻⁴.

The reduced χ² is in the 10⁷–10⁸ range because the files' third column, the integration's own error, is small: about
1.8·10³ at the strongest peak (9.8·10⁸), a median 0.03 √I over the fitted range, so R<sub>exp</sub> is about 0.0005 %.
R<sub>wp</sub> is the measure to read for this case.
