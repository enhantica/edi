---
template: physics.html
---

# Absorption

Absorption reduces the intensity leaving the sample. The cylinder models below apply a multiplicative transmission $A$ to each reflection's intensity; they do not move the reflection or define a single-crystal extinction correction.

## Types and active fields {#absorption-types}

| Beam mode | Saved type | Active field | Meaning |
| --- | --- | --- | --- |
| CW | `none` | — | $A=1$ |
| CW | `cylinder-hewat` | `mu_r` | Hewat cylinder expansion |
| CW | `cylinder-lobanov` | `mu_r` | Two-branch Lobanov cylinder fit |
| TOF | `none` | — | $A=1$ |
| TOF | `cylinder` | `abscor1` | Wavelength-dependent Hewat cylinder; canonical model token `cylinder-hewat` |

For a cylinder, $\mu R$ uses the **radius**, not the diameter. It is dimensionless when $\mu$ and $R$ use reciprocal length units consistently.

## Hewat cylinder {#eq-hewat}

Let $u=\mu R$ and $s=\sin\theta$:

$$A(u,\theta)=\exp[-(1.7133-0.0368s^2)u+(0.0927+0.375s^2)u^2].$$

In CW the angle is each reflection's Bragg angle and $u$ is the `mu_r` parameter. The polynomial is a small-to-moderate-absorption approximation. At large $u$ its quadratic exponent is not a general physical transmission law; use an appropriate model and inspect the resulting transmission rather than treating extrapolation as validated physics.

For TOF at a fixed bank angle,

$$\lambda_h=2d_h\sin\theta_{\rm bank},\qquad u_h=\text{ABSCOR1}\,\lambda_h.$$

The same Hewat expression uses that bank angle and reflection-specific wavelength. ABSCOR1 therefore carries the inverse-wavelength scale needed to produce $u_h$.

**ABSCOR2 is retained in saved input but is held fixed and does not enter this calculation.** It must not be described as an active second wavelength term or as a free fitting direction.

## Lobanov cylinder {#eq-lobanov}

For CW `cylinder-lobanov`, put $s=\sin\theta$ and $u=\mu R$. For $u\le3$:

$$A=\exp[-t_0u-t_1u^2-t_2u^3-t_3u^4],\qquad t_0=16/(3\pi),$$

$$\begin{aligned}
t_1={}&(25.99978-0.01911\sqrt{s})e^{-0.024551s^2}+0.109561s-26.04556,\\
t_2={}&-0.02489-0.39499s^2+1.219077s^3-1.31268s^4+0.871081s^5-0.2327s^6,\\
t_3={}&0.003045+0.018167s^2-0.03305s^4.
\end{aligned}$$

For $u>3$:

$$A=0.01\left[\frac{t_1-t_4}{(1+t_2(u-3))^{t_3}}+t_4\right],$$

$$\begin{aligned}
t_1={}&1.433902+11.07504s^2-8.77629s^4+10.02088s^6-3.36778s^8,\\
t_2={}&(0.013869-0.01249s^2)e^{3.27094s^2}+\frac{0.337894+13.77317s^2}{(1+11.53544s^2)^{1.555039}},\\
t_3={}&\frac{1.933433}{(1+23.12967s^2)^{1.686715}}-0.13576s+1.163198,\\
t_4={}&0.044365-\frac{0.04259}{(1+0.41051s^2)^{148.4202}}.
\end{aligned}$$

The high-$u$ expression is tabulated as a percentage before the $0.01$ conversion to a transmission fraction. The two empirical branches have a small seam mismatch; do not impose an invented continuity correction when reproducing this model.

## References

1. Hewat, A. W. (1979). **Acta Crystallographica A**, 35, 248. Cylinder absorption approximation.
2. Lobanov, N. N. & Alte da Veiga, L. (1998). Cylinder-transmission parameterisation, as used by the GSAS-II absorption implementation. The coefficients and branch conventions reproduced above identify the implemented approximation.
