---
template: physics.html
---

# Preferred orientation

A powder with preferred crystallite orientations does not produce the same relative reflection intensities as an ideally random powder. The supported CW model is the March–Dollase correction, with an optional random fraction.

## March–Dollase factor {#eq-march-dollase}

$$O(h)=f+(1-f)\left\langle\left[r^2\cos^2\alpha+\frac{\sin^2\alpha}{r}\right]^{-3/2}\right\rangle.$$

$r>0$ is `march_r`; $f$ is `march_random_fract`. $r=1$ or $f=1$ gives the untextured factor. The angle $\alpha$ is between the reflection and the declared texture axis, both treated as reciprocal-lattice vectors. The average is over the space group's point-group images of the reflection.

## Axis and metric {#eq-texture-angle}

For reciprocal vectors $\mathbf h$ and $\mathbf a$,

$$\cos^2\alpha=\frac{(\mathbf h^{\mathsf T}G^*\mathbf a)^2}{(\mathbf h^{\mathsf T}G^*\mathbf h)(\mathbf a^{\mathsf T}G^*\mathbf a)}.$$

The reciprocal metric matters for non-orthogonal cells. A bare Cartesian dot product of the Miller-index triplets is not the general expression.

## Scope and interpretation

A preferred-orientation row belongs to a linked structure in a CW experiment. It changes reflection intensities rather than peak positions. The implementation applies no extra volume normalisation to this factor. This model is not an arbitrary orientation-distribution function or a model for every texture geometry.

## References

1. Dollase, W. A. (1986). *Correction of intensities for preferred orientation in powder diffractometry: application of the March model*. **Journal of Applied Crystallography**, 19, 267–272.
