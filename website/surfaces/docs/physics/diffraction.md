---
template: physics.html
---

# Scattering and structure factors

## Nuclear structure factor {#eq-nuclear-structure-factor}

$$F_N(\mathbf h)=\sum_j o_j b_j T_j(\mathbf h)\exp[2\pi i\,\mathbf h\cdot\mathbf r_j].$$

The sum is over the symmetry-generated cell: $o_j$ is occupancy, $b_j$ coherent neutron scattering length, $T_j$ the [displacement factor](displacement.md), and $\mathbf r_j$ the fractional position. The measured nuclear intensity uses $|F_N|^2$ with the applicable scale and measurement factors. The sign of the exponential is a phase convention; it must be kept consistent with any complex scattering contribution.

Neutron scattering lengths depend on species/isotope, not on the X-ray atomic form-factor equation. The supported source selectors are `rauch2003ext` and `sears1992`; preserve the selected source or explicitly supplied scattering lengths when reproducing a calculation. Model admission rules prevent conflicting source declarations.

## X-ray form factors and dispersion {#eq-xray-structure-factor}

For the scalar X-ray model, replace $b_j$ by

$$f_j(s,\lambda)=f_{0,j}(s)+f'_j(\lambda)+i f''_j(\lambda),\qquad s=\sin\theta/\lambda.$$

Tabulated Gaussian parameterisations have the form

$$f_0(s)=c+\sum_{n=1}^{M}a_n\exp(-b_n s^2).$$

`wk1995` and `it1992` select the supported form-factor tables, with their own coefficient sets. Dispersion selectors are `cromer-liberman`, `sasaki1989`, `it1992` and `none`. `none` omits the anomalous-dispersion term; it does not replace the atom's normal form factor by zero.

These selectors identify data sources, not alternative calculation engines. Keep the source and wavelength with the project, especially near an absorption edge. See [model coverage](models.md).

## Occupancy and scale {#occupancy-and-scale}

Occupancy weights an atom's contribution to the structure factor. A phase scale weights the phase's intensity contribution to an experiment. Changing one is not generally equivalent to changing the other, and they can be strongly correlated with displacement and composition choices.

## Multiple phases and mass fractions {#phase-fractions}

An experiment sums the contributions of its enabled structure links. In the conventional scale-to-weight relation,

$$w_p=\frac{s_p Z_p M_p V_p}{\sum_q s_q Z_q M_q V_q}.$$

Here $Z_pM_p$ is the cell formula mass and $V_p$ its volume; a cell-mass representation uses the same product without separately spelling $Z$ and formula mass. Interpret reported fractions with the project's scale convention, composition and links. A disconnected structure contributes no intensity.

## Magnetic diffraction {#magnetic-diffraction}

**Planned.** Magnetic diffraction is planned. Magnetic scattering involves vector contributions beyond the scalar nuclear/X-ray model above.

## Polarized diffraction {#polarized-diffraction}

**Planned.** Polarized diffraction is planned. Polarization changes the scattering cross-section; the scalar model above does not provide this capability.

## Total scattering and PDF {#total-scattering-and-pdf}

**Planned.** Total scattering and pair distribution function (PDF) analysis are planned. PDF uses a total-scattering transform rather than the Bragg-profile model.

See [Scattering models](../user-guide/features.md#scattering-models) for the status of these and the implemented models.

## References

1. International Union of Crystallography. [Structure factor](https://dictionary.iucr.org/Structure_factor).
