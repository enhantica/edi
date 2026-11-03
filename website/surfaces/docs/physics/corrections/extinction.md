---
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

`domain_radius` $r$ is in µm. `crystal_radius` $R_c$ is in mm and sets the spherical path $\ell=1000R_c$ in µm. It is a descriptor, not a refinable domain radius. `mosaic_spread` $g$ is an **inverse width** in rad⁻¹: larger values describe a narrower mosaic distribution. For the mixed Å/µm convention in the expressions below define $\tilde g=10^{-4}g$.

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
