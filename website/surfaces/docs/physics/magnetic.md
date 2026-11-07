---
icon: fa5/magnet
template: physics.html
---

# Magnetic structures

EasyDiffraction calculates and refines commensurate magnetic structures from unpolarised neutron powder data, at constant wavelength and in time of flight. One structure carries both the nuclear and the magnetic scattering: one set of atoms and one scale, not a separate magnetic phase.

!!! note "Current coverage"

    The calculation covers a commensurate structure with propagation vector $\mathbf k=0$, whose magnetic space group's spatial operations form a setting of the space-group table. Non-zero $\mathbf k$, grey groups, operators that form no table setting, magCIF import, single-crystal magnetic data and [polarized diffraction](diffraction.md#polarized-diffraction) are not available yet. A single-crystal experiment linked to a magnetic structure is refused.

## The magnetic cell {#magnetic-cell}

A magnetic structure is stored in its magnetic cell, as magCIF writes it. The cell, every atom, the operators and the centring vectors all belong to that cell, and reflections are integer $hkl$ of it. The parent space group and its propagation vectors are recorded with the structure; each vector must be one the magnetic cell can carry.

## Magnetic symmetry {#magnetic-symmetry}

Each operator of the magnetic space group is a spatial operation $\{R|\mathbf t\}$ with a time-reversal sign $\theta=\pm1$, written as, for example, `x,y,z,+1`.

Symmetry limits the moment a site can carry. Written in lattice-vector components $\mu_i=M_i/a_i$, a moment is allowed when every signed operation that fixes the site leaves it unchanged:

$$\theta\,\det(R)\,R\,\boldsymbol\mu=\boldsymbol\mu.$$

The components this leaves dependent or fixed are not fitted independently, as with symmetry-fixed coordinates. The derived form is shown as the site's symmetry form, for example `Mx,My,Mz` or `0,My,0`.

## Moment components {#moment-components}

A moment is stored and fitted in crystal-axis components, in Bohr magnetons along unit vectors parallel to $\mathbf a$, $\mathbf b$ and $\mathbf c$. It can also be shown in two other forms:

- **Cartesian**, in magCIF's frame: $x$ along $\mathbf a$, $z$ along $\mathbf c^*$, and $y$ completing a right-handed set.
- **Spherical**: the modulus, the polar angle from $+z$, and the azimuthal angle from $+x$ around $+z$.

After a fit, the uncertainties of the derived values come from the fit's covariance, including correlations. Before a fit they are propagated as if the crystal-axis components were uncorrelated. A value the moment does not determine, such as the angles of a zero moment, has no uncertainty.

## Magnetic form factor {#eq-magnetic-form-factor}

With $s=\sin\theta/\lambda$,

$$f(s)=\langle j_0\rangle(s)+C_2\langle j_2\rangle(s)+C_4\langle j_4\rangle(s)+C_6\langle j_6\rangle(s),$$

where each higher $\langle j_n\rangle$ carries its $s^2$ factor, using the coefficients of International Tables Vol. C §4.4.5. Each atom type chooses an approximation:

| Approximation | Terms used |
| --- | --- |
| `j0` | $\langle j_0\rangle$ alone |
| `dipole` | $\langle j_0\rangle+C_2\langle j_2\rangle$ |
| `beyond_dipole` | All four terms |

$C_2$, $C_4$ and $C_6$ are parameters that can be fitted. A coefficient the approximation does not use is ignored, and one whose term the ion's table lacks must stay 0. The model carries no convention for the Landé factor $g$: $C_2=2/g-1$ for a moment counted against $J$, and $1-2/g$ against $S$.

## Magnetic structure factor {#eq-magnetic-structure-factor}

Over the atoms of the magnetic cell, with the same phase sign and [displacement factor](displacement.md) as the [nuclear structure factor](diffraction.md#eq-nuclear-structure-factor),

$$\mathbf M(\mathbf h)=p\sum_j o_j f_j(s)\,T_j(\mathbf h)\,\theta_j\det(R_j)\,(A R_j A^{-1})\,\mathbf m_j\,\exp[2\pi i\,\mathbf h\cdot\mathbf r_j].$$

Here $p=2.695$ fm per Bohr magneton, $o_j$ is occupancy, $\mathbf m_j$ the site's moment, and $A$ takes lattice components to Cartesian ones. Only the component perpendicular to the scattering vector contributes:

$$\mathbf M_\perp=\mathbf M-(\hat{\mathbf e}\cdot\mathbf M)\,\hat{\mathbf e}.$$

## Intensity {#eq-magnetic-intensity}

For unpolarised neutrons, the nuclear and magnetic parts add without interference:

$$I\propto|F_N|^2+|\mathbf M_\perp|^2.$$

The magnetic intensity uses the same profile, scale and corrections as the nuclear one, so both share every instrument model. With every moment at zero, the pattern equals that of the same structure without magnetic categories. X-ray experiments use the nuclear rule only.

A reflection is generated when either its nuclear or its magnetic sum over the stabiliser of $\mathbf h$ is non-zero, so purely magnetic reflections are included.

## Nuclear and magnetic parts of a pattern {#nuclear-and-magnetic-parts}

Each structure's curve is also available in two parts. The magnetic part is the same profile drawn from $|\mathbf M_\perp|^2$ alone, and the nuclear part is the net curve less it, so the two add up to the net curve exactly. Each reflection records its nuclear $|F|^2$, its $|F_{M\perp}|^2$ and their total.

## Fitting moments {#fitting-moments}

Moment components and form-factor coefficients are refined with analytical derivatives, like other structural parameters. Freeing either on X-ray data is refused, because X-rays do not measure them here.

The magnetic intensity is quadratic in the moment, which makes $\mathbf M=0$ hard for an ordinary step to reach: near zero, the step grows as $1/M$ and overshoots. This matters above an ordering temperature. By default, once a fit is nearly finished, each iteration therefore also tries every free moment component at exactly zero together, and keeps that point when $\chi^2$ is lower. `_minimizer.moments_near_zero` chooses this behaviour (`try_exact_zero`) or leaves the moments free to move (`keep_free`).

See [minimization and uncertainty](minimization.md) for the fit itself and [Magnetic moments](../application/structure/magnetic-moments.md) for the application's controls.

## References

1. Blume, M. (1963). Polarization effects in the magnetic elastic scattering of slow neutrons. *Physical Review*, 130, 1670. [doi:10.1103/PhysRev.130.1670](https://doi.org/10.1103/PhysRev.130.1670).
2. Brown, P. J. (2006). Magnetic form factors. *International Tables for Crystallography*, Vol. C, §4.4.5.
3. Perez-Mato, J. M. et al. (2015). Symmetry-based computational tools for magnetic crystallography. *Annual Review of Materials Research*. [doi:10.1146/annurev-matsci-070214-021008](https://doi.org/10.1146/annurev-matsci-070214-021008).
