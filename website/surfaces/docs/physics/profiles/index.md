---
template: physics.html
---

# Peak profiles

A profile turns an integrated reflection contribution into intensity over a powder-pattern axis. Its width and asymmetry are part of the experiment model.

- [Constant wavelength](profiles/cw.md): Gaussian, Lorentzian, direct pseudo-Voigt, TCH, Bérar–Baldinozzi and Finger–Cox–Jephcoat.
- [Time of flight](profiles/tof.md): symmetric pseudo-Voigt, Jorgensen and Jorgensen–Von Dreele.

The [catalogue](models.md#peak-profiles) lists the exact supported type tokens. A similarly named type from another program is not sufficient to establish matching width, mixing or asymmetry conventions.

## Width and normalisation {#profile-normalisation}

A unit-area profile integrates to one over its complete mathematical domain. Peak height therefore changes as width changes, even when integrated intensity remains fixed. FWHM $H$ and Gaussian standard deviation $\sigma$ satisfy $H=\sqrt{8\ln2}\,\sigma$.

## Finite peak windows {#peak-cutoff}

The evaluated pattern can use a finite window set by a cutoff in FWHM units. Tails outside that window are omitted; a finite window is a calculation choice rather than a new physical profile. The current window extent is `cutoff_fwhm * H`; a nonpositive cutoff selects the full-range path. Keep the cutoff when comparing calculations, particularly for Lorentzian tails.
