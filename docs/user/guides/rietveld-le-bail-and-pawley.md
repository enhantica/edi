# Rietveld, Le Bail and Pawley

Each structure has a calculation method. It says where the intensity of each reflection comes from: from the atoms
(Rietveld) or from the measured pattern (Le Bail and Pawley). The method belongs to the structure, so one pattern can
mix them: a Rietveld main phase beside a Le Bail impurity, for example.

## What each method needs and gives

| Method | Needs | Gives | Use it to |
|---|---|---|---|
| **Rietveld**, the default | Cell, space group, atom sites with displacements (and moments), peak profile, background | The structure, phase scales, weight fractions and R Bragg | Fit the structure |
| **Le Bail** | Cell, space group, peak profile, background | The cell, profile and background, and one intensity per reflection, without an s.u. | Settle the cell and profile before Rietveld; test a space group or a propagation vector |
| **Pawley** | The same as Le Bail | The same, with an s.u. for every intensity | Extract intensities with their uncertainties, for example for structure solution |

- **Le Bail** shares the measured counts out between the reflections after each fit step. It is fast and stable.
  Its intensities have no uncertainties and do not count as fitted parameters.
- **Pawley** fits every intensity as a parameter. It gives uncertainties, but it is slower and less stable where
  peaks overlap. No intensity goes below zero. Reflections that always sit at the same position share one value.
- **Neither** gives a phase scale, weight fractions, R Bragg or R F. The scale of a Le Bail or Pawley structure
  cannot be fitted.

## Le Bail first, then Rietveld

A good way to start on a new pattern:

1. Load the structure, for example from a CIF with its atoms.
2. Switch it to **Le Bail** and fit the cell, peak profile, background and zero.
3. Switch back to **Rietveld**. Every atom, displacement and moment from the CIF is still there. The phase scale gets
   a new start from the pattern, so the fit does not start from a meaningless scale.
4. Free the atoms you want and continue the fit from the Le Bail cell and profile.

Switching never changes the atoms. Under Le Bail or Pawley they stay saved with the structure, free marks included,
and the fit leaves them out; save, reopen and switch back, and they are all there. A structure without atoms can be
fitted with Le Bail or Pawley too, but an export that needs atoms still refuses it.

## Where to set it

- **App:** on **Structure → Main**, the **Calculation** column of the **Structures** table. **Undo** reverses a
  switch. The column is disabled, with the reason in its tooltip, for a structure linked to a single-crystal or
  total-scattering experiment: Le Bail and Pawley are for powder diffraction.
- **Python:** `structure.calc_method = 'le_bail'` (or `'pawley'`, `'rietveld'`). A method the structure cannot take
  raises a `ValueError` with the reason. `experiment.extracted_intensities` lists the extracted values, read-only.
- **Command line:** no option. `edi fit` reads the method from the project and saves the extracted intensities with
  it.

## What changes on the pages

For a Le Bail or Pawley structure:

- The **Atom sites**, **Atomic displacement** and **Magnetic moments** groups on the Structure page are hidden. Their
  values are kept.
- In **Linked structures**, the scale's free box is disabled with the reason, and the experiment shows every weight
  fraction as "—".
- In **Reflections**, the rows show **F² extracted**, and for Pawley its **s.u.**, in place of the calculated F, F²
  and |F_M⊥|². The values are in the units of F² calc, so they compare directly with a Rietveld F².
- R Bragg, R F and the magnetic R show "—" in the **Least-squares fit results** window.
- Once a fit has extracted them, the Experiment page's **Extra** tab has an **Extracted intensities** group with
  the saved values.
- On the Analysis page, a Pawley structure's intensities are one row per experiment, **Pawley intensities (N)**,
  with one free box for all of them. Le Bail intensities are not listed.

## Fits and files

- **Joint fits** share the cell; each experiment keeps its own intensities.
- **Sequential scans** carry the intensities from one dataset to the next. Each dataset's values are saved in
  `analysis/results_intensities.csv`, so a resumed scan continues where it stopped.
- **Magnetic structures** use the reflections of their magnetic group, whatever the moments are. Where a magnetic
  reflection falls on a nuclear one, as for a zero propagation vector, the two cannot be told apart.
- **Files:** the structure block holds `_structure.calc_method le_bail` (or `pawley`); it is left out for Rietveld.
  The experiment file holds the extracted intensities in an `_extracted_intensity` loop, one row per structure and
  reflection, and the next fit starts from them. The report writes the standard `_pd_calc.method` and
  `_refln.F_squared_meas`.
- **FullProf:** a phase with `Jbt=2` imports as Le Bail, and a Le Bail structure exports as `Jbt=2`. FullProf has no
  Pawley mode, so a Pawley structure does not export.

Two example projects show the methods: `docs/user/cli/pd-neut-cwl_lbco-hrpt_le-bail` (Le Bail, with the atoms kept for
the switch back) and `docs/user/cli/pd-xray-cwl_pbso4-lab_pawley` (Pawley, without atoms).
