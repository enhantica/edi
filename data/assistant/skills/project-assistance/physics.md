# Physics pages with equations

The website's physics pages that hold equations, as they were when this app was built.
Find the page in the table, then its section below, which starts with a line
`Page: <website address>`; cite that address.

| Title | Equations | Website |
| --- | --- | --- |
| Background models and estimation | eq-line-segment-background, eq-polynomial-background, eq-chebyshev-background, eq-arpls, eq-snip | https://easydiffraction.org/physics/background/ |
| Calibration and peak positions | eq-cwl-calibration, eq-line-shifts, eq-tof-calibration | https://easydiffraction.org/physics/calibration/ |
| Absorption | eq-hewat, eq-lobanov | https://easydiffraction.org/physics/corrections/absorption/ |
| Extinction | eq-primary-extinction, eq-secondary-extinction, eq-larson | https://easydiffraction.org/physics/corrections/extinction/ |
| Lorentz and polarization factors | eq-cwl-lorentz, eq-tof-lorentz, eq-xray-polarization | https://easydiffraction.org/physics/corrections/intensity/ |
| Preferred orientation | eq-march-dollase, eq-texture-angle | https://easydiffraction.org/physics/corrections/orientation/ |
| Crystallography | eq-cell-metric, eq-bragg | https://easydiffraction.org/physics/crystallography/ |
| Scattering and structure factors | eq-nuclear-structure-factor, eq-xray-structure-factor | https://easydiffraction.org/physics/diffraction/ |
| Atomic displacement parameters | eq-isotropic-adp, eq-anisotropic-adp | https://easydiffraction.org/physics/displacement/ |
| Magnetic structures | eq-magnetic-form-factor, eq-magnetic-structure-factor, eq-magnetic-intensity | https://easydiffraction.org/physics/magnetic/ |
| Minimization and uncertainty | eq-jacobian, eq-lm, eq-covariance | https://easydiffraction.org/physics/minimization/ |
| Constant-wavelength peak profiles | eq-cwl-pseudovoigt, eq-caglioti, eq-tch, eq-berar-baldinozzi, eq-fcj | https://easydiffraction.org/physics/profiles/cw/ |
| Time-of-flight peak profiles | eq-tof-widths, eq-jorgensen, eq-jorgensen-von-dreele | https://easydiffraction.org/physics/profiles/tof/ |
| Reliability factors | eq-profile-factors, eq-background-subtracted-factors, eq-bragg-factors | https://easydiffraction.org/physics/reliability/ |
| Rietveld method | eq-rietveld-pattern, eq-weighted-residual | https://easydiffraction.org/physics/rietveld/ |

---

Page: https://easydiffraction.org/physics/background/

---
icon: fa5/wave-square
template: physics.html
---

# Background models and estimation

A background contributes an additive baseline to a powder calculation. It is separate from excluded observations, peak-profile tails and the phase scale.

## Line-segment model {#eq-line-segment-background}

For anchors $(x_k,b_k)$ and $(x_{k+1},b_{k+1})$,

$$b(x)=b_k+(b_{k+1}-b_k)\frac{x-x_k}{x_{k+1}-x_k}.$$

Outside the anchor range the endpoint intensity is retained. Anchor positions are fixed nodes; the selected intensities can be fit parameters. This is not a linearly extrapolated edge.

## Polynomial model {#eq-polynomial-background}

$$b(x)=\sum_m c_m u^m,\qquad u=x/x_0-1.$$

`origin` is the nonzero normalisation coordinate $x_0$ in the pattern's axis units. It is not an intensity intercept. The currently admitted polynomial term orders are 0 through 5.

## Chebyshev model {#eq-chebyshev-background}

$$b(x)=\sum_m c_mT_m(u),\qquad u=\frac{2x-x_{\min}-x_{\max}}{x_{\max}-x_{\min}},$$

$$T_0=1,\quad T_1=u,\quad T_{m+1}=2uT_m-T_{m-1}.$$

`x_min` and `x_max` define the normalisation domain. The admitted Chebyshev term orders are 0 through 23. These are true Chebyshev coefficients, not powers of the unnormalised angle or time coordinate. Preserve the origin/domain when moving coefficients between projects.

## Automatic estimation {#background-estimation}

The estimator proposes a baseline and then editable anchors or series coefficients. The method is distinct from the final fitted background type. Supported method selectors are `auto`, `arpls`, `snip` and `fabc`; `auto` resolves to `arpls`.

### arPLS {#eq-arpls}

An iterated penalised smoothing solve uses

$$(W+\lambda D_2^{\mathsf T}D_2)\mathbf z=W\mathbf y,$$

$$w_i=\left[1+\exp\left(\frac{2}{s}[r_i-(2s-m)]\right)\right]^{-1},\qquad\mathbf r=\mathbf y-\mathbf z.$$

$m,s$ describe the negative residual subset; the reweighting suppresses peak contributions. Smoothness controls the penalty rather than a crystallographic parameter.

### SNIP {#eq-snip}

Peak clipping in log-log-square transformed intensity uses

$$v_i=\log[\log(\sqrt{y_i+1}+1)+1],\qquad v_i\leftarrow\min(v_i,(v_{i-w}+v_{i+w})/2).$$

The window and traversal settings determine the sequence of updates; the transform is inverted afterwards. This is an estimation algorithm, not an extra Bragg contribution.

### FABC and anchor reduction {#fabc}

FABC classifies baseline versus peak regions using a wavelet/noise criterion, then smooths through the baseline points. Anchor reduction converts the dense baseline to a smaller line-segment model using a noise-scaled vertical tolerance. `in_peaks` controls whether proposed anchors are moved out of or dropped from peak windows; `use_model` determines whether calculated peaks are subtracted before estimation.

Inspect the estimate. A missing phase or unsuitable calculated pattern can affect a model-assisted baseline proposal. Fitting the proposed background is a separate step.

## Excluded observations {#excluded-regions}

An excluded powder interval removes observations from the fitting objective and agreement-factor sums. It does not add a background component or change the definition of the calculated pattern. Retain excluded ranges with the experiment and justify them physically; masking a mismatch does not improve its model. Single-crystal reflection exclusion is a separate planned capability.

## References

1. Baek, S.-J., Park, A., Ahn, Y.-J. & Choo, J. (2015). *Baseline correction using asymmetrically reweighted penalized least squares smoothing*. **Analyst**, 140, 250–257. [DOI](https://doi.org/10.1039/C4AN01061B). arPLS baseline estimation.
2. Ryan, C. G., Clayton, E., Griffin, W. L., Sie, S. H. & Cousens, D. R. (1988). *SNIP, a statistics-sensitive background treatment for the quantitative analysis of PIXE spectra in geoscience applications*. **Nuclear Instruments and Methods in Physics Research B**, 34, 396–402. [DOI](https://doi.org/10.1016/0168-583X%2888%2990063-8). SNIP peak clipping.
3. Cobas, J. C., Bernstein, M. A., Martín-Pastor, M. & García Tahoces, P. (2006). *A new general-purpose fully automatic baseline-correction procedure for 1D and 2D NMR data*. **Journal of Magnetic Resonance**, 183, 145–151. [DOI](https://doi.org/10.1016/j.jmr.2006.07.013). FABC baseline classification.

---

Page: https://easydiffraction.org/physics/calibration/

---
icon: fa5/ruler-horizontal
template: physics.html
---

# Calibration and peak positions

Calibration determines where a reflection appears on the experimental axis. It can therefore correlate strongly with fitted cell dimensions.

## Constant-wavelength position {#eq-cwl-calibration}

$$2\theta_h=\frac{360}{\pi}\arcsin\left(\frac{\lambda}{2d_h}\right),\qquad x_{\rm corrected}=x_{\rm observed}-z.$$

The angle returned by the position equation is in degrees; $z$ is `calib_twotheta_offset`, also in degrees $2\theta$. The corrected coordinate must remain in the admitted open angular range for calculated points. Wavelength and cell changes both affect reflection positions; check their physical meaning before fitting both freely.

## Displacement and transparency shifts {#eq-line-shifts}

The implemented CW reflection-centre shift is

$$\Delta(2\theta_h)=D\cos(2\theta_h)+T\sin(2\theta_h),$$

where $D$ is `calib_sample_displacement` and $T$ is `calib_sample_transparency`, in degrees $2\theta$. It is applied to each reflection centre. The zero offset remains on the corrected observed axis. In particular, the displacement term here uses $\cos2\theta$, not an assumed Bragg–Brentano $\cos\theta$ formula.

## Time-of-flight position {#eq-tof-calibration}

$$t_h=z+D_1d_h+D_2d_h^2.$$

$z$ is in µs, $D_1$ in µs/Å and $D_2$ in µs/Å². The physical positive-spacing branch of the inverse quadratic is used; a negative quadratic coefficient does not by itself justify switching to the other mathematical root.

The reciprocal coefficient `calib_d_to_tof_reciprocal` ($D_{-1}/d$) is read and saved, but not used in the calculation.

## Fixed bank angle {#bank-angle}

A TOF bank uses its declared scattering angle to determine $\theta_{\rm bank}$ and $\lambda_h=2d_h\sin\theta_{\rm bank}$. Keep the bank geometry with calibration and absorption settings when moving or comparing a project.

See [instrument parameters](parameters.md#instrument), [Bragg's law](crystallography.md#eq-bragg) and [TOF profiles](profiles/tof.md).

---

Page: https://easydiffraction.org/physics/corrections/absorption/

---
icon: fa5/tint
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

FullProf's second absorption coefficient has no effect on this correction, so edi does not have it. An older project
file that sets it loads with a warning that the value is ignored.

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

---

Page: https://easydiffraction.org/physics/corrections/extinction/

---
icon: fa5/gem
template: physics.html
---

# Extinction

Extinction reduces strong single-crystal reflection intensities relative to the kinematic model. It is distinct from sample absorption. The correction below is a factor $y$ on **intensity** $F^2$, not a factor to apply unchanged to an amplitude.

## Single-crystal intensity {#single-crystal-intensity}

The scalar nuclear calculation compares each measured reflection with

$$F_{c,h}^2=s\,y_h\,|F_{N,h}|^2.$$

Here $s$ is the linked structure's scale and $y_h$ the selected extinction factor. A CW experiment supplies one wavelength; a TOF reflection list supplies a wavelength per reflection. This is a reflection model, with no powder-profile convolution or background term. Keep the [structure factor](../diffraction.md#eq-nuclear-structure-factor), scale and [reflection-statistics convention](../reliability.md#single-crystal-factors) consistent with the observed $F^2$ data.

## Supported types {#extinction-types}

| Type | Physical/empirical model | Active inputs |
| --- | --- | --- |
| `none` | Identity, $y=1$ | — |
| `becker-coppens-type-1` | Mosaic-spread-limited secondary extinction | Crystal radius, mosaic spread, mosaic distribution |
| `becker-coppens-type-2` | Domain-size-limited secondary extinction with primary extinction | Crystal radius, domain radius |
| `becker-coppens-mixed` | Primary and secondary extinction with both finite terms | Crystal radius, domain radius, mosaic spread, mosaic distribution |
| `larson-isotropic` | Empirical isotropic factor | `coefficient` |
| `larson-anisotropic` | Direction-dependent empirical coefficient | Six `coefficient_ij` terms |

Becker–Coppens mosaic distributions are `gaussian` and `lorentzian`. These are extinction distributions, not the powder peak-profile selector.

## Units and common factor {#extinction-units}

Use $c=\cos2\theta$, $q=\sin2\theta$, wavelength $\lambda$ in Å and cell volume $V$ in Å³. The extinction formula consumes $F^2$ in $(10^{-12}\,\mathrm{cm})^2$; a structure-factor value in fm must be converted before inserting it.

`domain_radius` $r$ is in µm. `crystal_radius` $R_c$ is in mm and sets the spherical path $\ell=1000R_c$ in µm. It is a descriptor, not a fitted domain radius. `mosaic_spread` $g$ is an **inverse width** in rad⁻¹: larger values describe a narrower mosaic distribution. For the mixed Å/µm convention in the expressions below define $\tilde g=10^{-4}g$.

Define

$$Y(x;a,b,k)=\left[1+kx+\frac{ax^2}{1+bx}\right]^{-1/2}.$$

Do not insert an arcminute mosaic width or a crystal diameter in place of these quantities.

## Primary Becker–Coppens factor {#eq-primary-extinction}

$$x_p=\tfrac32F^2(\lambda r/V)^2,\quad a_p=0.20+0.45c,\quad
b_p=0.22-0.12(0.5-c)^2,\quad y_p=Y(x_p;a_p,b_p,2).$$

## Secondary Becker–Coppens factor {#eq-secondary-extinction}

The effective domain $D$ is

$$D_G=\frac{r\tilde g}{\sqrt{\tilde g^2\lambda^2+\tfrac98r^2q^2}},\qquad
D_L=\frac{r\tilde g}{\tilde g\lambda+rq}.$$

Type I takes the unlimited-domain limit: $D_G=\tilde g/(\sqrt{9/8}\,q)$ and $D_L=\tilde g/q$. Type II takes the unlimited-mosaic-spread limit $D=r/\lambda$. The mixed model uses both finite inputs. Then

$$x_s=\tfrac32F^2\lambda(\lambda/V)^2\ell D.$$

For a Gaussian distribution,

$$a_s=0.58+0.48c+0.24c^2,\quad b_s=0.02-0.025c,\quad y_s=Y(x_s;a_s,b_s,2.12).$$

For a Lorentzian distribution,

$$a_s=0.025+0.285c,\qquad
b_s=\begin{cases}0.15-0.2(0.75-c)^2,&c>0,\\-0.45c,&c\le0,\end{cases}\qquad y_s=Y(x_s;a_s,b_s,2).$$

Type I uses $y=y_s$. Type II and mixed use $y=y_p y_s$. The implemented identity/degenerate limits must be retained when evaluating zero radii, zero spread or vanishing angle factors; do not manufacture infinities by cancelling terms outside their valid domain.

## Larson factors {#eq-larson}

For the isotropic coefficient $x$,

$$y=\left[1+0.001\,xF^2\lambda^3/\sin2\theta\right]^{-1/2}.$$

For the anisotropic form,

$$x_{\rm aniso}=x_{11}h^2+x_{22}k^2+x_{33}l^2+x_{12}hk+x_{13}hl+x_{23}kl,\qquad
x_{\rm eff}=\frac{x_{\rm aniso}}{4(\sin\theta/\lambda)^2},$$

and substitute $x_{\rm eff}$ for $x$ in the same intensity factor. The cross coefficients are entered in the polynomial as written, without an additional factor of two. The implementation returns the identity at vanishing $\sin2\theta$ or a nonpositive empirical radicand; such a result is not evidence for a physically justified coefficient choice.

## Applicability

These are spherical/isotropic Becker–Coppens approximations and the stated empirical Larson forms, not a general dynamical-diffraction solution. Parameter values can be correlated with scale and structure; inspect the strong-reflection residuals and the [reliability factors](../reliability.md).

## References

1. Becker, P. J. & Coppens, P. (1974). **Acta Crystallographica A**, 30, 129–147. [DOI](https://doi.org/10.1107/S0567739474000337). Extinction theory and spherical approximations.
2. Becker, P. J. & Coppens, P. (1974). **Acta Crystallographica A**, 30, 148–153. Application of the extinction treatment.
3. Larson extinction convention, as used in SHELXL and the Mag2Pol manual, §5.1.3. The operative intensity factor and units for this reference are stated above.

---

Page: https://easydiffraction.org/physics/corrections/intensity/

---
icon: fa5/adjust
template: physics.html
---

# Lorentz and polarization factors

These terms convert structure-factor contributions into the intensity convention of a measurement. They depend on geometry and radiation, not on a single universal powder formula.

## Constant-wavelength powder Lorentz factor {#eq-cwl-lorentz}

$$L_{\rm CW}(\theta)=\frac{1}{\sin\theta\sin2\theta}=\frac{1}{2\sin^2\theta\cos\theta}.$$

Evaluate it once at the reflection's Bragg angle. It does not contain the TOF $d^4$ factor. Reflection multiplicity and the experiment's intensity-unit convention enter the intensity assembly separately.

## Time-of-flight powder factor {#eq-tof-lorentz}

The fixed-bank spacing dependence is

$$L_{\rm TOF}(d)\propto d^4\sin\theta_{\rm bank}.$$

$\theta_{\rm bank}$ is half the bank's scattering angle. Wavelength-dependent absorption uses $\lambda=2d\sin\theta_{\rm bank}$. The full calculation retains its scattering-length/intensity unit conversion and scale; the proportionality above isolates the Lorentz dependence rather than specifying an arbitrary absolute normalisation.

## X-ray polarization {#eq-xray-polarization}

$$P=1-K+K\cos^2(2\theta_m)\cos^2(2\theta).$$

$K$ is `setup_polarization_coefficient`, and the entered monochromator take-off angle `setup_monochromator_twotheta` is $2\theta_m$ in degrees. At $K=0$ the factor is unity. Apply the angle conversion before evaluating the cosines; a stored monochromator angle is not a precomputed squared cosine.

## Wavelength doublet {#wavelength-doublet}

A CW X-ray experiment may declare a second wavelength and its intensity ratio. The calculated pattern combines the two line systems with the declared weights, placing each at its own Bragg positions. It is distinct from increasing the peak width or changing the atomic displacement parameter. See [calibration](../calibration.md) and the [instrument parameters](../parameters.md#instrument).

## Scope

The factors here are for the stated powder geometries. They should not be copied onto a single-crystal reflection list that is already reduced to its own integrated-intensity convention. The [Rietveld model](../rietveld.md#eq-rietveld-pattern) shows where they enter a powder calculation.

---

Page: https://easydiffraction.org/physics/corrections/orientation/

---
icon: fa5/compass
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

---

Page: https://easydiffraction.org/physics/crystallography/

---
icon: fa5/cube
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

---

Page: https://easydiffraction.org/physics/diffraction/

---
icon: fa5/atom
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

Commensurate magnetic structures are available for unpolarised neutron powder data. Magnetic scattering involves vector contributions beyond the scalar nuclear and X-ray models above; see [Magnetic structures](magnetic.md).

## Polarised diffraction {#polarised-diffraction}

**Planned.** Polarised diffraction is planned. Polarization changes the scattering cross-section; the scalar model above does not provide this capability.

## Total scattering and PDF {#total-scattering-and-pdf}

**Planned.** Total scattering and pair distribution function (PDF) analysis are planned. PDF uses a total-scattering transform rather than the Bragg-profile model.

See [Scattering models](../user-guide/features.md#scattering-models) for the status of these and the implemented models.

## References

1. International Union of Crystallography. [Structure factor](https://dictionary.iucr.org/Structure_factor).

---

Page: https://easydiffraction.org/physics/displacement/

---
icon: fa5/arrows-alt
template: physics.html
---

# Atomic displacement parameters

Displacement parameters describe the attenuation of coherent scattering by the distribution of positions around each site's average position. Their conventions and coordinate basis matter.

## Isotropic forms {#eq-isotropic-adp}

$$T_{\rm iso}(s)=\exp(-B_{\rm iso}s^2)=\exp(-8\pi^2U_{\rm iso}s^2),\qquad B_{\rm iso}=8\pi^2U_{\rm iso}.$$

Both Biso and Uiso have units Å². An equal numerical value in the two forms does not represent equal displacement. `adp_type` chooses `Biso` or `Uiso`; `adp_iso` carries the corresponding value.

## Anisotropic forms {#eq-anisotropic-adp}

With fractional reflection indices and reciprocal-cell lengths,

$$T_{\rm aniso}=\exp\left[-2\pi^2\sum_{i,j}U_{ij}h_i h_j a_i^*a_j^*\right]
=\exp\left[-\tfrac14\sum_{i,j}B_{ij}h_i h_j a_i^*a_j^*\right].$$

The `beta` convention absorbs the reciprocal-length and $2\pi^2$ factors:

$$T_{\rm aniso}=\exp[-\mathbf h^{\mathsf T}\boldsymbol\beta\mathbf h].$$

`Bani`, `Uani` and `beta` are distinct supported representations. The six independent symmetric components include cross terms: a full $\sum_{i,j}$ counts $ij$ and $ji$, so an off-diagonal entry must not be added as if it were already doubled. Space-group symmetry can constrain the components.

## Interpretation

Check physical plausibility and positive-definiteness where appropriate. A large displacement can compensate for another model error; its fitted uncertainty does not resolve that ambiguity. Link the value to the [parameter index](parameters.md) and the selected convention before discussing it with the assistant.

## References

1. International Union of Crystallography. [Atomic displacement parameter nomenclature](https://www.iucr.org/who-we-are/commissions/commission-on-crystallographic-nomenclature/published-reports/adp). Definitions and coordinate conventions.
2. International Union of Crystallography. [coreCIF definition of isotropic B](https://www.iucr.org/__data/iucr/cifdic_html/1/cif_core.dic/Iatom_site_B_iso_or_equiv.html).

---

Page: https://easydiffraction.org/physics/magnetic/

---
icon: fa5/magnet
template: physics.html
---

# Magnetic structures

EasyDiffraction calculates and fits commensurate magnetic structures from unpolarised neutron powder data, at constant wavelength and in time of flight. One structure carries both the nuclear and the magnetic scattering: one set of atoms and one scale, not a separate magnetic phase.

!!! note "Current coverage"

    The calculation covers a commensurate structure with propagation vector $\mathbf k=0$, whose magnetic space group's spatial operations form a setting of the space-group table. Non-zero $\mathbf k$, grey groups, operators that form no table setting, magCIF import and [polarised diffraction](diffraction.md#polarised-diffraction) are not available yet. A neutron single-crystal experiment linked to a magnetic structure adds the magnetic intensity $|\mathbf M_\perp|^2$ to each reflection, and its fit can free the moments.

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

Moment components and form-factor coefficients are fitted with analytical derivatives, like other structural parameters. Freeing either on X-ray data is refused, because X-rays do not measure them here.

The magnetic intensity is quadratic in the moment, which makes $\mathbf M=0$ hard for an ordinary step to reach: near zero, the step grows as $1/M$ and overshoots. This matters above an ordering temperature. By default, once a fit is nearly finished, each iteration therefore also tries every free moment component at exactly zero together, and keeps that point when $\chi^2$ is lower. `_minimizer.moments_near_zero` chooses this behaviour (`try_exact_zero`) or leaves the moments free to move (`keep_free`).

See [minimization and uncertainty](minimization.md) for the fit itself and [Magnetic moments](../application/structure/magnetic-moments.md) for the application's controls.

## References

1. Blume, M. (1963). Polarization effects in the magnetic elastic scattering of slow neutrons. *Physical Review*, 130, 1670. [doi:10.1103/PhysRev.130.1670](https://doi.org/10.1103/PhysRev.130.1670).
2. Brown, P. J. (2006). Magnetic form factors. *International Tables for Crystallography*, Vol. C, §4.4.5.
3. Perez-Mato, J. M. et al. (2015). Symmetry-based computational tools for magnetic crystallography. *Annual Review of Materials Research*. [doi:10.1146/annurev-matsci-070214-021008](https://doi.org/10.1146/annurev-matsci-070214-021008).

---

Page: https://easydiffraction.org/physics/minimization/

---
icon: fa5/level-down-alt
template: physics.html
---

# Minimization and uncertainty

## Independent parameters and Jacobian {#eq-jacobian}

For the weighted residual vector $\mathbf r$ defined in [Rietveld method](rietveld.md#eq-weighted-residual), let $J_{ij}=\partial r_i/\partial p_j$. The Jacobian columns correspond to independent free parameters; fixed, symmetry-related and constrained dependent values are not extra columns.

The scientific models and their derivatives share their declared parameter conventions. A parameter that is only stored has no nonzero model derivative merely because a numerical value is present in the file.

## Levenberg–Marquardt step {#eq-lm}

A scaled damped least-squares step has the form

$$(J^{\mathsf T}J+\lambda D)\Delta\mathbf p=-J^{\mathsf T}\mathbf r.$$

$D$ supplies the diagonal scaling/damping convention; $\lambda$ controls damping. The implemented strategy controls the acceptance and damping search, while the scientific objective remains the weighted residual sum.

| Descent selector | Meaning |
| --- | --- |
| `auto` | The default: `fast_descent_and_ladder` for a single or joint fit, `fast_descent` for each point of a sequential fit |
| `ladder` | Damping-ladder LM search |
| `fast_descent` | Gain-ratio damping within each step |
| `fast_descent_and_ladder` | Fast descent and the ladder run briefly from the start; the lower continues |

The project records its descent, positive relative objective tolerance and positive iteration budget. A budget stop is not the same as convergence. Some strategies have restrictions when bounds are declared; inspect the reported diagnostic rather than assuming every combination is supported.

## Covariance and standard uncertainties {#eq-covariance}

At the final state, the current covariance convention is the scaled inverse curvature

$$C=\chi^2_{\rm red}(J^{\mathsf T}J)^+,\qquad u(p_j)=\sqrt{\max(C_{jj},0)},\qquad
\rho_{jk}=C_{jk}/\sqrt{C_{jj}C_{kk}}.$$

The Jacobian here is already weighted. The implementation computes a column-scaled pseudoinverse and transforms back to physical parameter units, using the undamped final curvature. The `+` denotes that numerical pseudoinverse; it is not an inverse of the damped LM step matrix.

The reduced-χ² scaling is an explicit convention. Do not silently substitute an unscaled covariance from another program. A zero-sensitivity direction or numerical degeneracy requires inspecting the associated diagnostics; a zero reported uncertainty does not make an unmeasured parameter exact.

## Constraints and bounds {#constraints-and-bounds}

A constraint relates quantities and reduces independent freedom. Physical admissibility limits, editable optimizer bounds and symmetry restrictions serve different purposes. The application's displayed minimum and maximum are model-admissibility information; they are not a promise of controls for setting optimizer search bounds.

Use [Parameters](../user-guide/parameters.md) for practical interpretation. The fit's observation set and parameter count also determine the [reliability factors](reliability.md).

## Global minimization (planned) {#global-minimization}

Least squares improves a fit from its starting values, so a poor start can leave it in a local minimum. A global
search, such as simulated annealing or several fits from different starting points, is planned to find a better start
before the least-squares fit.

---

Page: https://easydiffraction.org/physics/profiles/cw/

---
icon: fa5/long-arrow-alt-right
template: physics.html
---

# Constant-wavelength peak profiles

Use $\Delta=2\theta-2\theta_h$ and FWHM $H$ in degrees. Widths, mixing and the production asymmetry coefficients are evaluated at the reflection's Bragg angle, not independently at every sampled pattern point.

## Symmetric primitives {#eq-cwl-pseudovoigt}

$$G(\Delta;H)=\frac{2}{H}\sqrt{\frac{\ln2}{\pi}}\exp[-4\ln2(\Delta/H)^2],\qquad
L(\Delta;H)=\frac{2}{\pi H}\frac{1}{1+4(\Delta/H)^2}.$$

$$pV(\Delta;H,\eta)=(1-\eta)G(\Delta;H)+\eta L(\Delta;H).$$

Both components use the same $H$. `cwl-gaussian` uses $\eta=0$ and `cwl-lorentzian` uses $\eta=1$.

## Direct width and mixing {#eq-caglioti}

For Gaussian, Lorentzian and direct pseudo-Voigt types,

$$H^2=U\tan^2\theta+V\tan\theta+W.$$

`cwl-pseudo-voigt` additionally uses $\eta=\eta_0+\eta_1(2\theta)$ with $2\theta$ in degrees. `mixing_eta_1` is therefore per degree. An unphysical width or mixing choice is not repaired by interpreting the parameters as a different profile type.

## Thompson–Cox–Hastings {#eq-tch}

`cwl-tch-pseudo-voigt` derives a combined width and mixing from

$$H_G^2=U\tan^2\theta+V\tan\theta+W,\qquad H_L=X\tan\theta+Y/\cos\theta.$$

$$\begin{aligned}
H^5={}&H_G^5+2.69269H_G^4H_L+2.42843H_G^3H_L^2\\
&+4.47163H_G^2H_L^3+0.07842H_GH_L^4+H_L^5,\\
\eta={}&1.36603r-0.47719r^2+0.11116r^3,\qquad r=H_L/H.
\end{aligned}$$

$U,V,W$ have degree-squared units; $X,Y$ have degree units. Here X multiplies $\tan\theta$ and Y multiplies $1/\cos\theta$. The implementation's nonnegative TCH mixing floor is zero, preserving the Gaussian endpoint. The combined $H$ is used by both Gaussian and Lorentzian components.

## Bérar–Baldinozzi asymmetry {#eq-berar-baldinozzi}

`cwl-pseudo-voigt-berar-baldinozzi` applies the direct pseudo-Voigt width/mixing with an empirical multiplicative factor. Let $z=\Delta/H$:

$$F_a(z)=2ze^{-z^2},\qquad F_b(z)=2(2z^2-3)F_a(z),$$

$$A(\theta)=A_0/\tan\theta+A_1/\tan2\theta,\qquad B(\theta)=B_0/\tan\theta+B_1/\tan2\theta,$$

$$\Omega(\Delta)=pV(\Delta)[1+A(\theta)F_a(z)+B(\theta)F_b(z)].$$

Parameters are `asym_beba_a0`, `asym_beba_b0`, `asym_beba_a1`, `asym_beba_b1` and the limit angle `asym_beba_limit`. At or above that limit in degrees $2\theta$, the asymmetry correction is omitted. It is a descriptor, not an independent free fit parameter. The production per-reflection evaluation keeps the odd factor centred on each reflection.

## Finger–Cox–Jephcoat asymmetry {#eq-fcj}

`cwl-tch-pseudo-voigt-fcj` convolves the TCH core with an axial-divergence weight. Put $S_L=S/L$ and $D_L=D/L$, half the sample and detector heights divided by the diffractometer radius:

$$\cos2\phi_{\min}=\cos2\theta_h\sqrt{1+(S_L+D_L)^2},\qquad
\cos2\phi_{\rm infl}=\cos2\theta_h\sqrt{1+(S_L-D_L)^2}.$$

With $q(\delta)=|\cos2\theta_h|/\sqrt{\cos^2\delta-\cos^22\theta_h}$, the two geometric regions use

$$G(\delta)=\begin{cases}\left|[(S_L+D_L)q(\delta)-1]/\cos\delta\right|,&\text{inner region},\\
2\min(S_L,D_L)q(\delta)/\cos\delta,&\text{outer region}.
\end{cases}$$

Integrate between $2\phi_{\min}$ and $2\theta_h$. The inner branch applies when $|\delta-2\phi_{\min}|\le|2\phi_{\rm infl}-2\phi_{\min}|$; the outer branch applies beyond that boundary. The normalised quadrature is

$$\Omega(x)=\frac{\sum_k w_kG(\delta_k)\,pV(x-\delta_k+2\theta_h)}{\sum_k w_kG(\delta_k)}.$$

`asym_fcj_1` is $S_L$ and `asym_fcj_2` is $D_L$. The implementation handles zero/equal-height limits and uses the symmetric profile within 0.4° of $2\theta_h=90°$; these evaluation conventions are part of the model, not new free parameters.

## References

1. Caglioti, G., Paoletti, A. & Ricci, F. P. (1958). **Nuclear Instruments**, 3, 223–228. Angular dependence of peak widths.
2. Thompson, P., Cox, D. E. & Hastings, J. B. (1987). **Journal of Applied Crystallography**, 20, 79–83. [DOI](https://doi.org/10.1107/S0021889887087090). TCH width and mixing.
3. Bérar, J.-F. & Baldinozzi, G. (1993). **Journal of Applied Crystallography**, 26, 128–129. Empirical profile asymmetry.
4. Finger, L. W., Cox, D. E. & Jephcoat, A. P. (1994). **Journal of Applied Crystallography**, 27, 892–900. Axial-divergence asymmetry.

---

Page: https://easydiffraction.org/physics/profiles/tof/

---
icon: fa5/stopwatch
template: physics.html
---

# Time-of-flight peak profiles

Let $\delta=t-t_h$ in microseconds. The bank geometry supplies the wavelength of each reflection; [calibration](../calibration.md#eq-tof-calibration) maps spacing to the peak centre.

## Gaussian and Lorentzian width terms {#eq-tof-widths}

$$\sigma_G^2(d)=v_0+(v_1+\mathrm{strain}_G)d^2+(v_2+\mathrm{size}_G)d^4,$$

$$H_G=\sqrt{8\ln2}\,\sigma_G,\qquad
H_L(d)=\gamma_0+(\gamma_1+\mathrm{strain}_L)d+(\gamma_2+\mathrm{size}_L)d^2.$$

Here $v_0,v_1,v_2$ denote the stored variance coefficients labelled σ₀², σ₁² and σ₂²; the superscript is part of the variance notation, not an instruction to square their stored values again. The `broad_gauss_sigma_*` coefficients are variance coefficients, not standard deviations or FWHMs. `broad_lorentz_gamma_*` coefficients define Lorentzian FWHM. Keep their respective time/spacing units; see the [parameter index](../parameters.md#peak).

## Symmetric pseudo-Voigt {#tof-pseudo-voigt}

`tof-pseudo-voigt` uses the [TCH width/mixing](cw.md#eq-tch), with $H_G,H_L$ in microseconds, and the symmetric unit-area pseudo-Voigt. It does not add the back-to-back exponential pulse.

## Jorgensen pulse and profile {#eq-jorgensen}

`tof-jorgensen` convolves a two-sided exponential pulse with a Gaussian. The rates are

$$\alpha(d)=\alpha_0+\alpha_1/d,\qquad \beta(d)=\beta_0+\beta_1/d^4,$$

with positive evaluated rates in inverse microseconds. Let $N=\alpha\beta/[2(\alpha+\beta)]$ and $\sigma$ be the Gaussian standard deviation:

$$\Omega_G(\delta)=N[e^u\operatorname{erfc}(y)+e^v\operatorname{erfc}(z)],$$

$$\begin{aligned}
u&=\tfrac12\alpha(\alpha\sigma^2+2\delta),&
y&=(\alpha\sigma^2+\delta)/(\sqrt2\sigma),\\
v&=\tfrac12\beta(\beta\sigma^2-2\delta),&
z&=(\beta\sigma^2-\delta)/(\sqrt2\sigma).
\end{aligned}$$

The normalisation already includes the Gaussian-convolution factors; do not reuse $N$ as if it alone normalised a bare piecewise exponential. The numerical evaluation uses stable exponential/error-function combinations to avoid overflow without changing this equation.

## Jorgensen–Von Dreele {#eq-jorgensen-von-dreele}

`tof-jorgensen-von-dreele` adds the Lorentzian contribution through a common TCH width $H$ and mixing $\eta$:

$$\Omega=(1-\eta)\Omega_G+\eta\Omega_L.$$

Both terms use that combined width: $\sigma=H/\sqrt{8\ln2}$ in $\Omega_G$ and FWHM $H$ in $\Omega_L$.

$$\Omega_L=-\frac{2N}{\pi}\left(\operatorname{Im}[e^pE_1(p)]+\operatorname{Im}[e^qE_1(q)]\right),$$

$$p=\alpha\delta+i\alpha H/2,\qquad q=-\beta\delta+i\beta H/2.$$

$E_1$ is the exponential integral. At zero Lorentzian width the profile reduces to its Gaussian Jorgensen limit; assigning a different width to each mixed kernel would define a different model.

## Ikeda–Carpenter {#ikeda-carpenter}

**Planned.** Ikeda–Carpenter is planned for TOF pulse modelling. It is not a selectable profile in this reference snapshot. See [Time-of-flight peak profiles](../../user-guide/features.md#time-of-flight-peak-profiles) for the availability of this and the implemented profiles.

## References

1. Von Dreele, R. B., Jorgensen, J. D. & Windsor, C. G. (1982). **Journal of Applied Crystallography**, 15, 581–589. Time-of-flight profile modelling.
2. Thompson, P., Cox, D. E. & Hastings, J. B. (1987). **Journal of Applied Crystallography**, 20, 79–83. [DOI](https://doi.org/10.1107/S0021889887087090). Width and mixing convention.

---

Page: https://easydiffraction.org/physics/reliability/

---
icon: fa5/check-circle
template: physics.html
---

# Reliability factors

Reliability factors summarise agreement under a defined observation model. They supplement the pattern, residual, physical model and parameter uncertainties.

## Included observations and weights {#factor-observations}

For powder factors, sums run over included points outside excluded intervals with positive standard uncertainty and available finite calculated intensity. Let $w_i=1/\sigma_i^2$, $b_i$ be background, $N$ the included point count and $P$ the independent free-parameter count.

## Powder profile factors {#eq-profile-factors}

$$R_p=\frac{\sum_i|y_{o,i}-y_{c,i}|}{\sum_i|y_{o,i}|},\qquad
R_{wp}=\sqrt{\frac{\sum_iw_i(y_{o,i}-y_{c,i})^2}{\sum_iw_i y_{o,i}^2}},$$

$$R_{\exp}=\sqrt{\frac{N-P}{\sum_iw_i y_{o,i}^2}},\qquad
\chi^2_{\rm red}=\frac{\sum_iw_i(y_{o,i}-y_{c,i})^2}{N-P}.$$

The engine's factor values are fractions; a displayed percentage is 100 times that fraction. $R_{wp}/R_{\exp}$ is the square root of reduced χ² under matching sums and degrees of freedom. The name “goodness of fit” is used for both conventions in the literature, so state which is meant.

A fit needs positive degrees of freedom to interpret reduced χ². Nonpositive degrees of freedom or a zero denominator are degenerate cases; the report's numerical guard result is not a statistically meaningful factor.

## Background-subtracted factors {#eq-background-subtracted-factors}

The conventional background-subtracted factors retain the same residual numerator but replace the normalising observations by net intensity:

$$cR_p=\frac{\sum_i|y_{o,i}-y_{c,i}|}{\sum_i|y_{o,i}-b_i|},\qquad
cR_{wp}=\sqrt{\frac{\sum_iw_i(y_{o,i}-y_{c,i})^2}{\sum_iw_i(y_{o,i}-b_i)^2}},$$

$$cR_{\exp}=\sqrt{\frac{N-P}{\sum_iw_i(y_{o,i}-b_i)^2}}.$$

Removing background from the denominator can change the apparent factor substantially. Do not compare a conventional profile Rwp directly with a background-subtracted value while calling them the same definition.

## Bragg and F factors {#eq-bragg-factors}

Powder phase factors use reflection intensities apportioned from the observed profile according to the calculated contributions:

$$I_{o,h}=\sum_i I_{c,h}(i)\frac{y_{o,i}-b_i}{y_{c,i}-b_i},\qquad
R_B=\frac{\sum_h|I_{o,h}-I_{c,h}|}{\sum_h|I_{o,h}|}.$$

$$|F_{c,h}|=\sqrt{m_h|F_h|^2},\qquad |F_{o,h}|=|F_{c,h}|\sqrt{\max(I_{o,h},0)/I_{c,h}},\qquad
R_F=\frac{\sum_h\big||F_{o,h}|-|F_{c,h}|\big|}{\sum_h|F_{o,h}|}.$$

The reflection partition is model-dependent, particularly where peaks overlap. These phase factors are not independent directly measured integrated intensities for every powder reflection.

## Single-crystal reflection factors {#single-crystal-factors}

The reflection-statistics view also reports amplitude-based and intensity-weighted factors over a declared set $\mathcal H$:

$$R(F)=\frac{\sum_{h\in\mathcal H}\left|\sqrt{\max(F_{o,h}^2,0)}-\sqrt{\max(F_{c,h}^2,0)}\right|}{\sum_{h\in\mathcal H}\sqrt{\max(F_{o,h}^2,0)}},$$

$$wR(F^2)=\sqrt{\frac{\sum_{h\in\mathcal H}w_h(F_{o,h}^2-F_{c,h}^2)^2}{\sum_{h\in\mathcal H}w_h(F_{o,h}^2)^2}},\qquad w_h=1/u(F_{o,h}^2)^2.$$

`r_factor_all` and `wr_factor_all` use all reflections; `_gt` uses those passing the experiment's observed-reflection threshold; `wr_factor_ref` uses those selected for fitting. An absent observed threshold means $I>2u(I)$. An amplitude threshold $F>n u(F)$ is implemented as $F_o^2>(n/2)u(F_o^2)$; an intensity threshold uses $F_o^2>n u(F_o^2)$. The project's optional fit threshold is separate and uses the intensity rule. A reporting threshold does not itself discard weak data from fitting.

### Single-crystal reflection exclusions {#single-crystal-reflection-exclusions}

**Planned.** Single-crystal reflection exclusions are planned. The reporting and fit-threshold rules above describe the current behaviour. See [Background and excluded observations](../user-guide/features.md#observation-exclusions) for the status alongside powder exclusions.

## Per-experiment and pooled summaries {#pooled-factors}

For a single-crystal reflection list, the same absolute and weighted formulas operate on observed and calculated $F^2$ values, giving $R(F^2)$ and $wR(F^2)$. There is no powder background partition; the background-subtracted denominators equal the un-subtracted ones. Do not label this intensity-based factor as the amplitude-based $R(F)$.

Per-experiment factors use that experiment's included observations. Pooled factors combine the underlying sums across experiments; they are not an arithmetic average of each experiment's R factor. Keep the objective weighting and factor definition explicit when interpreting joint fits.

## Interpretation

There is no universal threshold that proves structural correctness. Changing the data range, uncertainty estimates, background, excluded observations or free set changes the statistic. See [assessing a fit](../user-guide/analysis-workflow/analysis.md#fit-quality).

## References

1. McCusker, L. B., Von Dreele, R. B., Cox, D. E., Louër, D. & Scardi, P. (1999). *Rietveld refinement guidelines*. **Journal of Applied Crystallography**, 32, 36–50.
2. Toby, B. H. (2006). *R factors in Rietveld analysis: How good is good enough?* **Powder Diffraction**, 21, 67–70.

---

Page: https://easydiffraction.org/physics/rietveld/

---
icon: fa5/chart-area
template: physics.html
---

# Rietveld method

The Rietveld method compares a calculated powder pattern with measured intensities over the included observations. It fits a crystallographic model together with the relevant experiment parameters.

## Calculated powder pattern {#eq-rietveld-pattern}

A useful decomposition is

$$
y_i^{\rm calc}=b(x_i)+\sum_p s_p\sum_{h\in p}m_h\,L_h\,P_h\,A_h\,O_h\,|F_h|^2\,\Omega_p(x_i-x_h).
$$

Here $p$ labels a linked phase, $s_p$ its scale, $h$ a reflection, $m_h$ multiplicity, $L_h$ the geometry-dependent Lorentz factor, $P_h$ polarization where applicable, $A_h$ absorption, $O_h$ preferred orientation, $F_h$ the structure factor, $\Omega$ the selected peak profile and $b$ the background. This is a model decomposition: factors that do not apply to the selected experiment are unity, and instrument-specific intensity-unit conventions are carried with its scale.

Follow the terms to [crystallography](crystallography.md), [scattering](diffraction.md), [profiles](profiles/index.md), [absorption](corrections/absorption.md), [orientation](corrections/orientation.md), [Lorentz/polarization](corrections/intensity.md) and [background](background.md). Single-crystal reflection calculations use the corresponding integrated-intensity model, not a powder-profile sum.

## Least-squares objective {#eq-weighted-residual}

$$
r_i(\mathbf p)=\frac{y_i^{\rm calc}(\mathbf p)-y_i^{\rm obs}}{\sigma_i},\qquad
S(\mathbf p)=\sum_{i\in\mathcal I}r_i^2.
$$

$\mathcal I$ is the included observation set and $\sigma_i>0$ its standard uncertainty. Reversing every residual's sign leaves $S$ unchanged. The displayed observed-minus-calculated difference curve can therefore have the opposite sign to the solver residual.

Only independent free parameters are optimisation variables. Symmetry, constraints, the selected experiment and model type determine which quantities are independent and affect the observations. See [minimization](minimization.md).

## Single and joint fitting {#joint-fitting}

A single fit uses one experiment. A joint fit combines the residuals of several experiments, sharing their common structural quantities while retaining experiment-specific terms. If experiment weights $v_e$ are applied, its residual block is multiplied by $\sqrt{v_e}$ and its objective contribution by $v_e$.

Inspect each experiment after a joint fit. Combined agreement can hide a systematic mismatch in one dataset. [Reliability factors](reliability.md) distinguish per-experiment and pooled summaries.

## Sequential and independent scans {#scan-fitting}

Both scan modes run a sequence of fits against a template experiment. Their distinction is the starting model, not parallel execution. See the [fitting-mode guide](../user-guide/analysis-workflow/analysis.md#fitting-modes).

### Sequential scans {#sequential-scans}

Each dataset starts from the preceding fitted result. This carries the evolving model forward through the series.

### Independent scans {#independent-scans}

Every dataset starts from the same template values, so the starting model does not depend on the preceding fit.

## Intensity extraction {#intensity-extraction}

**Proposed.** These methods are not available fitting modes in this reference snapshot. See [Pattern fitting](../user-guide/features.md#pattern-fitting) for current alternatives.

### Le Bail intensity extraction {#le-bail-intensity-extraction}

Reflection intensities are updated by iterative decomposition of the measured powder pattern, alongside profile fitting.

### Pawley intensity extraction {#pawley-intensity-extraction}

Reflection intensities are adjustable variables in a least-squares fit of the powder pattern.

The distinction is described in the [IUCr intensity-extraction overview](https://onlinelibrary.wiley.com/iucr/itc/Ha/ch4o2v0001/sec4o2o2/).

## Interpretation

Fitting improves agreement under the model and its uncertainties. Convergence does not establish that the phase model, background, calibration or uncertainty estimates are correct. Use the [practical fit assessment](../user-guide/analysis-workflow/analysis.md#fit-quality) and retain the starting project.

## References

1. McCusker, L. B., Von Dreele, R. B., Cox, D. E., Louër, D. & Scardi, P. (1999). *Rietveld refinement guidelines*. **Journal of Applied Crystallography**, 32, 36–50.
