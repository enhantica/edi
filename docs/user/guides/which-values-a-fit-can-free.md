# Which values a fit can free

The Analysis page's parameter table lists every numerical input of your structures and experiments. You can free a
value for the next fit with its **free** checkbox. When a fit cannot vary a value, its checkbox is disabled, and
hovering over it shows the reason.

## The reasons

- **A descriptor, never fitted.** The value describes the setup and is never varied, for example the crystal radius,
  the Berar-Baldinozzi limit angle, a background point's position or a texture direction. Values that are not
  parameters (a background point's position, a polynomial term's order, the peak cutoff, a texture direction's
  indices, a scattering length) are shown read-only here; change them on their page.
- **Set by symmetry.** The space group fixes the value or ties it to another one, for example the b length of a cubic
  cell. Free the value it follows instead.
- **Set by a constraint.** One of your constraints computes the value from others.
- **This fit's data cannot determine it.** No experiment in the fit that uses the value measures what it depends on.
  Single-crystal reflections give intensities but not positions, so they cannot determine the cell; add a powder
  pattern of the same structure to fit it. A structure that no experiment links, a disabled link and an experiment
  without measured data beside measured ones also leave their values undetermined.
- **The fit cannot vary it yet.** The calculation has no derivative for it. The wavelength of an X-ray experiment is
  one when its anomalous dispersion comes from a table: set the dispersion source to `none` to fit it.

## What happens to a free mark that cannot be fitted

- **When a project opens,** a value marked free that cannot be fitted is loaded fixed, keeping its value, and the
  Messages panel says so.
- **When the project changes,** for example when you remove the powder pattern that let a single crystal's cell be
  fitted, a value you freed stays free. Its checkbox stays enabled so you can clear it, and starting a fit says which
  value cannot be fitted and why.
- **When you disable a link,** its scale and texture, and a structure that no enabled link uses, keep their free
  marks. The fit leaves them out until a link uses them again, and opening the project keeps them free.
- **In Python,** setting `free = True` on such a value raises an error with the reason. On a value that symmetry or a
  constraint sets, it is ignored with a warning.

## Filters and counts

The table always lists the values a fit can vary and every value marked free. Four boxes in the **Parameters shown**
group on the Analysis page's **Settings** tab add the values that cannot be fitted, one group each, and count them:

- **Not measured in this fit:** this fit's data cannot determine the value, or the fit cannot vary it yet. Shown by
  default.
- **Fixed by symmetry:** the space group sets the value. Hidden by default.
- **Set by a constraint:** one of your constraints computes the value. Hidden by default.
- **Setup values:** values that describe the setup, which no fit ever varies, and the values that are not
  parameters. Shown by default.

The app remembers your choice. It is not saved in the project, and Python and the command line are not filtered.

The variability filter above the table shows all listed rows, the free ones, the fixed ones a fit could vary, or the
ones that cannot be fitted. The Parameters entry in the status bar counts the values a fit can vary.
