---
template: physics.html
---

# Physics

This reference explains the models and numerical conventions used to calculate and refine EasyDiffraction projects. The equations apply across the application, Python and the command line; the [feature matrix](../user-guide/features.md) distinguishes what each interface can do.

## Find a physical model

| Topic | Questions answered |
| --- | --- |
| [Rietveld refinement](rietveld.md) | How do structures, profiles and corrections form a powder pattern? What does the fit minimise? |
| [Crystallography](crystallography.md) | How do the cell, symmetry, reflection indices and multiplicities determine the diffraction geometry? |
| [Scattering and structure factors](diffraction.md) | How do radiation, atomic positions, occupancy and scattering-data sources affect intensity? |
| [Atomic displacement parameters](displacement.md) | What do Biso, Uiso, Bani, Uani and beta mean? |
| [Constant-wavelength profiles](profiles/cw.md) | Gaussian, Lorentzian, pseudo-Voigt, TCH and the two asymmetry models |
| [Time-of-flight profiles](profiles/tof.md) | Symmetric pseudo-Voigt, Jorgensen and Jorgensen–Von Dreele |
| [Absorption](corrections/absorption.md) | Cylinder Hewat and Lobanov transmission, beam-mode differences and active parameters |
| [Extinction](corrections/extinction.md) | Becker–Coppens type I/type II/mixed and isotropic/anisotropic Larson |
| [Preferred orientation](corrections/orientation.md) | March–Dollase texture and random fraction |
| [Lorentz and polarization](corrections/intensity.md) | Which intensity factors apply to each geometry and radiation probe? |
| [Calibration and peak positions](calibration.md) | Wavelength, TOF mapping, zero offset, displacement and transparency |
| [Background](background.md) | Line-segment, polynomial, Chebyshev and automatic estimation |
| [Minimization and uncertainty](minimization.md) | The solver, free parameters, constraints, covariance and correlations |
| [Reliability factors](reliability.md) | Rp, Rwp, Rexp, reduced χ², background-subtracted, Bragg and F factors |

## Look up a type or parameter

The [model catalogue](models.md) lists supported model tokens and their explanations. The [parameter index](parameters.md) links each scientific parameter to its equation, units and applicable model. [Conventions](conventions.md) fixes the notation used throughout the reference.

## Use the reference with the assistant

Use a model's exact name and the parameter or equation link when asking a question. The assistant should identify the experiment type and units before applying an equation, distinguish an active parameter from a stored field, and cite the relevant section. Model availability is scoped to the [reference snapshot](models.md#reference-snapshot).

The [assistant index](../llms.txt) provides a machine-friendly entry point; the [machine-readable catalogue](catalogue.json) identifies model and parameter pages. These are a retrieval source for the assistant, not a claim that chat integration has already been implemented.
