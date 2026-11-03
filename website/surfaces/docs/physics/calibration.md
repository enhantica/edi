---
template: physics.html
---

# Calibration and peak positions

Calibration determines where a reflection appears on the experimental axis. It can therefore correlate strongly with refined cell dimensions.

## Constant-wavelength position {#eq-cwl-calibration}

$$2\theta_h=\frac{360}{\pi}\arcsin\left(\frac{\lambda}{2d_h}\right),\qquad x_{\rm corrected}=x_{\rm observed}-z.$$

The angle returned by the position equation is in degrees; $z$ is `calib_twotheta_offset`, also in degrees $2\theta$. The corrected coordinate must remain in the admitted open angular range for calculated points. Wavelength and cell changes both affect reflection positions; check their physical meaning before refining both freely.

## Displacement and transparency shifts {#eq-line-shifts}

The implemented CW reflection-centre shift is

$$\Delta(2\theta_h)=D\cos(2\theta_h)+T\sin(2\theta_h),$$

where $D$ is `calib_sample_displacement` and $T$ is `calib_sample_transparency`, in degrees $2\theta$. It is applied to each reflection centre. The zero offset remains on the corrected observed axis. In particular, the displacement term here uses $\cos2\theta$, not an assumed Bragg–Brentano $\cos\theta$ formula.

## Time-of-flight position {#eq-tof-calibration}

$$t_h=z+D_1d_h+D_2d_h^2.$$

$z$ is in µs, $D_1$ in µs/Å and $D_2$ in µs/Å². The physical positive-spacing branch of the inverse quadratic is used; a negative quadratic coefficient does not by itself justify switching to the other mathematical root.

`calib_d_to_tof_reciprocal` is retained in input but is held fixed and **does not contribute a $D_{-1}/d$ term in this reference's calculation**. The four-term equation used by some other programs must not be substituted for the equation above.

## Fixed bank angle {#bank-angle}

A TOF bank uses its declared scattering angle to determine $\theta_{\rm bank}$ and $\lambda_h=2d_h\sin\theta_{\rm bank}$. Keep the bank geometry with calibration and absorption settings when moving or comparing a project.

See [instrument parameters](parameters.md#instrument), [Bragg's law](crystallography.md#eq-bragg) and [TOF profiles](profiles/tof.md).
