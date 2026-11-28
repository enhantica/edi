# 0109. Le Bail and Pawley fits

- **Status:** Proposed
- **Date:** 2026-11-28
- **Implementation:** ⬜ Not implemented
- **Priority:** High
- **Forward constraint (binding on new features):** which calculation methods a structure may take, the switch and
  what a fit can free under each come from crysta (`calc_method_options`, `set_calc_method`, the fit marks of
  ADR-0053), reached through one core function each; no surface lists methods or keeps its own rule. A project whose
  structures are all Rietveld opens, fits and saves as before.

## Context

Users asked to switch between Rietveld and Le Bail, for single and sequential fits (feedback #141). Rietveld takes each
reflection's intensity from the atoms. Le Bail shares the measured intensity out between reflections, and Pawley fits
one intensity per reflection; both need only the cell, space group, peak shape, background and zero. They are used to
settle those before Rietveld, to test a space group or a propagation vector, and to extract |F|² for structure
solution.

The owner decided on 2026-11-28 that each structure has a calculation method, Rietveld by default, chosen in a new
Calculation column of the Structures table. One workflow must work end to end: load a CIF with atoms, switch to Le
Bail, fit cell, peak profile, background and zero, switch back to Rietveld with every atom, ADP and moment of the CIF
still there, and continue the fit from the Le Bail cell and profile.

crysta ADR-0138 does the computing: the method token, the extracted intensities and their file loop, the Le Bail and
Pawley fits, the fit marks, the outputs and the scale start after a switch back. This ADR decides edi's model, pages,
Python, command line and importers.

## Decision

1. **Model and files.** `edi::Structure` gains `calc_method` (crysta's token, empty for Rietveld) and
   `edi::ExperimentBase` gains `extracted_intensities` (rows of structure id, h, k, l and a `Parameter f_squared`),
   both as crysta holds them. `io.cpp` reads and writes `_structure.calc_method` in the structure file, only when it is
   not `rietveld`, and the `_extracted_intensity` loop in the experiment file, only when it has rows, by crysta's
   names and rules (ADR-0051). The adapter converts both ways. After a fit the extracted rows are copied back from
   crysta's project before the parameter states, because `copy_parameter_states` needs both walks to name the same
   parameters.
2. **The switch.** `edi::calc_method_choice(project, structure)` (`selectors.hpp`) returns crysta's offered tokens and
   its reason when only Rietveld applies. `edi::select_calc_method(project, structure, token)` runs crysta's
   `set_calc_method`. Switching to Rietveld then gives every enabled link of the structure, in an experiment with
   measured data, crysta's `rietveld_scale_start`, or leaves the scale and says so in Messages when there is none.
   The app makes the switch and its scale starts one undo step (`edi::Edit`). Atoms, ADPs, moments and their free
   flags are never changed; they stay in the structure file under every method.
3. **Structure page.** The Structures table gets a Calculation column after the Type and Structure columns: a combo
   box with crysta's options, labelled from the label registry, disabled with crysta's reason as its tooltip when only
   Rietveld applies (a link to a single crystal or a total-scattering experiment). Its kind is `text`, and it shows at
   every width (ADR-0103: only the Analysis table drops columns). For a Le Bail or Pawley structure the Atom sites,
   Atomic displacement and Magnetic moments groups are hidden and keep their content; a hidden group does no work
   (ADR-0102). The category list asks the core which groups the current structure shows. The structure view is
   unchanged.
4. **Experiment page.** In Linked structures, a Le Bail or Pawley link's Scale has its Free box disabled with crysta's
   reason (ADR-0053). Every weight fraction of an experiment holding such a link shows "—", as crysta gives none. In
   the fit results, its R Bragg, R F and magnetic R show "—" with the tooltip "No R factor: the structure's
   intensities are extracted" (ADR-0045). The structure combo box disables a Le Bail or Pawley structure on a single
   crystal, with crysta's reason; a structure that still has such a link shows the link's Scale with crysta's
   fit mark, never a refusal of edi's own. In Reflections, a Le Bail or Pawley structure's rows show F² extracted
   (`_refln.f_squared_meas`) and, for Pawley, its s.u., in place of F calc, F² calc and |F_M⊥|²; the columns are
   declared (ADR-0105).
5. **Analysis page.** A Pawley structure's intensities show as one row per structure and experiment, "Pawley
   intensities (N)", with one Free box that sets or clears every row's flag; a mix shows the box partly checked. The
   status bar counts N parameters. Le Bail intensities are not listed. The atoms, ADPs and moments of a Le Bail or
   Pawley structure keep their rows, not fittable with crysta's reason, under the "not measured in this fit" filter.
   The correlation chart has no intensity rows, since crysta writes none.
6. **Fits.** `fit_policy.cpp` refuses a structure without atom sites only when it is Rietveld; exports that need atoms
   keep refusing it. Single, joint, independent and sequential fits run through crysta as before. A sequential scan's
   per-point intensities are crysta's `analysis/results_intensities.csv`. Parametric fits take a Le Bail structure
   once crysta's parametric fit has merged (crysta ADR-0138 §9): built in this work if that happens while it is open,
   otherwise with the work that integrates the two. Pawley stays out of parametric fits.
7. **Python.** `Structure.calc_method` is a string; its setter is `select_calc_method` and raises `ValueError` with
   crysta's reason. `ExperimentBase.extracted_intensities` is a read-only list of rows with `structure_id`, `index_h`,
   `index_k`, `index_l`, `f_squared` and `f_squared_su`. diffraction-lib has neither, so each gets a necessity-register
   row (ADR-0011).
8. **Command line.** No new flag: `edi fit` reads the method from the project (ADR-0007) and saves the extracted rows
   with it.
9. **Importers and exporters.** FullProf (ADR-0096): a phase with `Jbt=2` imports as Le Bail, with its atoms when it
   gives any; an `Irf=2` intensity file is not read and is listed as a gap; `Jbt=-2` and `±3` stay refused. Export
   writes `Jbt=2` and `Irf=0` for a Le Bail structure, with its atoms, which FullProf uses to start its first run, and
   refuses a Pawley structure, since FullProf has no Pawley mode. cryspy (ADR-0099) refuses a Le Bail or Pawley
   structure as well as one without atoms, since it has neither mode. GSAS-II's `LeBail` and `doPawley` stay refused
   (ADR-0097).
10. **Labels** (ADR-0104). `structure.calc_method` "Calculation", short "Calc."; `structure.calc_method=rietveld`
    "Rietveld", `=le_bail` "Le Bail", `=pawley` "Pawley"; `extracted_intensity` "Extracted intensities";
    `refln.f_squared_meas` "F² extracted"; `refln.f_squared_meas_su` "s.u."; the Analysis row "Pawley intensities
    (%1)".
11. **Tests.** Core: the owner's workflow on an example project (atom categories identical after Le Bail and back,
    the scale start), undo of a switch, save and reopen under Le Bail, the fit write-back of rows, the fit marks, a
    structure without atoms under Le Bail, the single-crystal refusal, a FullProf `Jbt=2` import and export. Python and
    the command line on the same project. QML: the column, its disabled reason, the hidden groups and the Pawley row.
    The numerical references are crysta's (ADR-0138 §12). Two example projects, runnable with `edi fit`:
    `pd-neut-cwl_lbco-hrpt_le-bail` (Le Bail on LBCO HRPT, the owner's workflow from a structure with atoms) and
    `pd-xray-cwl_pbso4-lab_pawley` (Pawley on the PbSO4 lab X-ray pattern).

## Consequences

- A user can settle the cell and profile with Le Bail and return to Rietveld without losing the structure.
- Magnetic form factors and scattering lengths stay visible under Le Bail, unused by it.
- Fit starts and correlations in the analysis file hold no intensities, so undoing the fit of a reopened project
  restores the parameters but not the intensities.
- This needs crysta's SDK built with ADR-0138.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| The method on the Linked structures row | Overruled by the owner: it lives on the structure. |
| One switch for the whole project | Rejected: a Rietveld phase beside a Le Bail one needs a method per structure. |
| Clear the atoms when leaving Rietveld | Rejected by the owner: switching back restores every atom. |
| One Analysis row per intensity | Rejected by the owner: hundreds of rows; one row per structure and experiment. |
| A Reset intensities action | Deferred: switching to Rietveld and back starts them again, and undo brings them back. |
| The label "Fitting method" | Rejected: "Fitting methods" already names least squares, maximum likelihood and MCMC on the Features page. |
