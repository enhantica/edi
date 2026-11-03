---
template: physics.html
---

# Crystallography

## Cell metric and spacing {#eq-cell-metric}

Cell lengths $a,b,c$ and angles $\alpha,\beta,\gamma$ define the direct metric

$$
G=\begin{pmatrix}a^2&ab\cos\gamma&ac\cos\beta\\ab\cos\gamma&b^2&bc\cos\alpha\\ac\cos\beta&bc\cos\alpha&c^2\end{pmatrix},\qquad
V=\sqrt{\det G},\qquad G^*=G^{-1}.
$$

For reflection indices $\mathbf h=(h,k,l)^{\mathsf T}$,

$$d_{hkl}^{-2}=\mathbf h^{\mathsf T}G^*\mathbf h.$$

Lengths are in Å, angles are entered in degrees, and the trigonometric functions use the corresponding angles. The reciprocal metric above excludes a $2\pi$ factor. The scattering-vector magnitude is $Q=2\pi/d$.

## Bragg condition {#eq-bragg}

$$2d\sin\theta=n\lambda,\qquad s=\sin\theta/\lambda=1/(2d).$$

For an indexed reflection the order can be incorporated in its Miller indices. The measured powder angle is $2\theta$, not $\theta$. A CW reflection is reachable only when $\lambda/(2d)<1$ in the implemented open-angle domain. See [calibration](calibration.md) for how this becomes an experimental coordinate.

## Symmetry and atom positions {#symmetry}

Space-group operations map fractional positions as $\mathbf r'=R\mathbf r+\mathbf t$ modulo lattice translations. The selected setting fixes the coordinate convention. Symmetry may relate cell parameters or fix atom coordinates; such values are not additional independent fitting directions.

The asymmetric unit and its symmetry-generated images define the unit cell. Wyckoff positions describe site symmetry and multiplicity. Do not count identical special-position images twice or confuse a site's multiplicity with the multiplicity of a reflection.

## Reflection multiplicity and absences {#reflection-multiplicity}

Equivalent reciprocal-lattice vectors contribute a reflection multiplicity to a powder intensity. Centering, glide and screw translations can cause systematic absences through phase cancellation in the structure factor. A reflection's symmetry equivalence is a property of its space-group setting and radiation model; a count of atom sites is not its multiplicity.

For practical input, see [Structure](../user-guide/analysis-workflow/structure.md). [Scattering](diffraction.md) connects the positions to intensities.

## References

1. International Union of Crystallography. [Bragg's law](https://dictionary.iucr.org/Bragg%27s_law).
