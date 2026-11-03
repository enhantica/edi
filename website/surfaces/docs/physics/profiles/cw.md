---
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
