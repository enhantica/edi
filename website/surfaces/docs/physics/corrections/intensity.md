---
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
