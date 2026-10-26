# 0053. What a fit can free comes from crysta's one rule

- **Status:** Accepted
- **Date:** 2026-10-26
- **Implementation:** ✅ Implemented
- **Priority:** High
- **Forward constraint (binding on new features):** a surface that offers or refuses a free flag reads the parameter's
  fit mark (`Parameter::fit_blocker`, `fit_reason`), set by `refresh_fittability` from crysta's rule. No surface keeps
  its own list of values that cannot be fitted.

## Context

Whether a value could be fitted was decided in three places that disagreed. edi kept a list of two fixed settings
(the Berar-Baldinozzi limit angle and the crystal radius), crysta's fit refused a single crystal's cell and wavelength,
and the loader cleared those two with notes of its own. The Analysis table hid every value it could not fit, so a user
could not see why one was missing, and a checkbox could be enabled for a value the fit then refused.

crysta now decides it once, in one rule its public API exposes:
for each parameter of a fit, the first of five reasons that applies, each with one text. A descriptor is never fitted.
Symmetry or a declared constraint may set the value. No experiment in the fit that uses the value may measure what it
needs: integrated single-crystal intensities measure no reflection positions, so they cannot determine the cell. Or
crysta may have no derivative for it yet, such as the wavelength of an X-ray experiment with a dispersion source.

## Decision

1. **One mark per parameter.** `refresh_fittability` (`core/include/edi/fittability.hpp`) converts the project, asks
   crysta's rule for the experiments the project's fitting mode fits, and marks each parameter with its blocker and
   crysta's reason. In the single and joint modes the fit uses the experiments with measured data when the project
   mixes them with data-free ones, else all of them; a scan uses its one experiment. A parameter crysta's model does
   not hold, such as a slot of the other beam mode, counts as one no fitted experiment uses.
2. **When the marks are read.** The loader, a fit's entry, the Python `free` setter and the app after a load or an
   edit refresh the marks first. A value change never changes them, so a fit's iterations and frames do not.
3. **Python.** `free = True` on a descriptor, a value this fit's data cannot determine or one crysta cannot vary
   raises `ValueError` naming the parameter and the reason. On a value symmetry or a constraint sets, the flag is
   ignored with the `crysta.domain.dependent_free_ignored` warning, as before
   ([ADR-0024](0024-parameter-aliases-and-constraints.md)), which now also names the reason.
4. **Loading.** A file that marks such a value free loads it fixed, value and uncertainty kept, with one
   `crysta.domain.unfittable_free_ignored` note each on the loader's warning route.
5. **The fit.** `Project.fit`, `fit_joint` and the scan entries refuse a free flag the rule blocks, naming the
   parameter and the reason. Such a flag can survive a change to the project, for example removing the powder pattern
   that let a single crystal's cell be fitted; only a load clears it.
6. **The Analysis table** can list every numerical input of the structures and experiments, fittable or not: each
   parameter, and each value that is no parameter (a background point's position, a polynomial term's order, the peak
   cutoff, a texture direction's indices, a scattering length), which is shown read-only and edited on its page.
   Measured data, computed values and fit results stay out. The Free checkbox is enabled where a fit can vary the
   value, or while it is free so the flag can be cleared; otherwise its tooltip says "Cannot be fitted: " and the
   reason. The variability filter splits the rows into free, fixed and not fittable, and the status bar counts what a
   fit can vary.
7. **Show-filters.** Which of the values a fit cannot free the table lists is chosen on the Analysis page's Settings
   tab, with four boxes, two to a row, one per group of crysta's reasons: not measured in this fit (this fit's data
   cannot determine it, or crysta cannot vary it yet), fixed by symmetry, set by a constraint, and fixed settings (the
   descriptors). Each box adds its group's rows to those a fit can free, and its label counts them. A value marked free
   is always listed, so its flag can be cleared. By default the values not measured in this fit and the fixed settings
   are listed, the other two groups are not. The choice is remembered per user by the app and never saved in the
   project; Python and the command line are not filtered. The variability filter's counts are of the rows the
   show-filters leave.

## Consequences

- `is_fixed_setting`, the adapter's silent clearing of those two flags and the loader's single-crystal notes are gone.
- The Analysis table is longer. It stays fast because its list view creates rows only as they are shown
  ([ADR-0029](0029-listview-tables.md)).
- A project that mixes a single crystal and a powder pattern makes the cell fittable here, while crysta still refuses
  to fit such a project as a whole, with its own reason.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep edi's list and add the single-crystal cell to it | Rejected: a list per surface is what disagreed |
| Hide the rows a fit cannot vary, as before | Rejected: the owner asked to see every value with the reason it cannot be fitted |
| Clear a blocked flag whenever the project changes | Rejected: it discards a choice made for another fit; a load clears it, a fit refuses it |
| Edit every descriptor in the Analysis table | Deferred: values that are no parameter are edited where their rows are added and removed |
| Save the show-filters in the project | Rejected: they choose what this user sees, not what the project holds |
