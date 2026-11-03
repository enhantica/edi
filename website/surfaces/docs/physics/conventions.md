---
template: physics.html
---

# Conventions

A physical model is reproducible only when its quantities, units and conventions are identified. Keep them with the structure, experiment and analysis settings.

## Axes and units

| Quantity | Convention to check |
| --- | --- |
| Constant-wavelength powder axis | The measured scattering angle is 2θ, in degrees for the powder text input |
| Time-of-flight powder axis | Time of flight in microseconds for the powder text input |
| Unit cell | Length and angle units, space-group setting and coordinate system |
| Atom positions | Fractional coordinates in the selected cell and setting |
| Peak width | Whether the quantity is a full width, half width, standard deviation or model-specific coefficient |
| Observation uncertainty | A standard uncertainty, rather than a variance or an intensity weight |

Use [data formats](../user-guide/data-formats.md) and the relevant import instructions to prepare observations. Changing a filename extension does not convert an axis or unit.

## Atomic displacement parameters

Isotropic displacement can be expressed with `Uiso` or `Biso`, related by **Biso = 8π² Uiso**. Both have dimensions of length squared, but their numerical values differ.

Anisotropic displacement uses components in a specified basis. Keep the source convention and coordinate system when importing, exporting or comparing values. See the [IUCr displacement-parameter nomenclature](https://www.iucr.org/who-we-are/commissions/commission-on-crystallographic-nomenclature/published-reports/adp) and [coreCIF B-parameter definition](https://www.iucr.org/__data/iucr/cifdic_html/1/cif_core.dic/Iatom_site_B_iso_or_equiv.html).

## Parameter and file names

Python access paths, Edi project keys and scientific CIF names have different roles. Use the [Python reference](../python/reference.md) for code and [data formats](../user-guide/data-formats.md) for persistence; identify the actual scientific quantity before comparing a similarly named value.

## Comparing calculations

Match the structure setting, radiation and scattering sources, instrument calibration, profile definition, background, exclusions, observations and free parameters. Record the software version and minimizer conditions as well.

A comparison is meaningful only for the models and conditions it covers. Retain the [complete project](../user-guide/analysis-workflow/project.md) and its [report](../user-guide/analysis-workflow/report.md) with the result.
