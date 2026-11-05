# :material-microscope: Experiment

An experiment describes an observation of the sample or a simulation of that observation. It combines measured data or a calculation range with an instrument model, peak profile, background and links to the contributing structures.

## Identify the measurement

Choose the sample form, radiation probe and beam mode that match the experiment. Constant-wavelength powder data use scattering angle; time-of-flight data use the calibrated time axis. Single-crystal observations describe reflections rather than a continuous powder profile.

The [glossary](../glossary.md) explains the experiment labels. Use the checked [example catalogue](../examples.md) to find an appropriate starting model and its stated scope.

## Observations or a simulation range

Measured observations supply the intensities and uncertainties used by a refinement. A simulation supplies the range over which the current model is calculated, without requiring measured intensities.

A saved experiment declares one of these forms. A complete project can contain both simulation and measured-data experiments; fitting uses the experiments with observations.

For powder text input, verify the independent variable, its units, intensity and optional uncertainty column. Check the imported range and any import diagnostics. See [data formats](../data-formats.md) before preparing a file.

## Instrument and peak profile

[Instrument settings](../../physics/calibration.md) describe the measurement geometry and calibration, such as wavelength or the relationship between time of flight and diffraction spacing. The [peak profile](../../physics/profiles.md) describes reflection shapes and broadening.

Check peak positions and widths before changing structural parameters to compensate for disagreement. A profile appropriate to one instrument or measurement need not describe another.

## Background and excluded regions

The [background](../../physics/background.md) accounts for the contribution beneath the diffraction peaks. Select a representation appropriate to the measurement and inspect its behaviour between and under peaks. An automatic estimate is a starting model that still needs inspection.

Excluded intervals remove observations from the fitting objective. Record why a region is excluded; an exclusion changes the evidence used to assess the model and its agreement factors.

## Contributing structures and scales

Link each contributing structure and review its scale. One experiment can sum contributions from several phases. Several experiments can observe the same structure under different measurement conditions.

Scales connect phase contributions to the experiment. Interpret any derived composition or phase fraction in the context of the model and its conventions.

Configure experiments in the [<span class="ed-interface-icons" aria-hidden="true">:lucide-globe: :lucide-monitor:</span> <span class="ed-icon-text">Application</span>](../../application/experiments.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:simple-python: :simple-jupyter:</span> <span class="ed-icon-text">Python</span>](../../python/experiments.md){ .ed-interface-link .ed-icon-label }, then [use the saved experiments from Command Line](../../cli/experiments.md).
