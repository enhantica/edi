---
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
