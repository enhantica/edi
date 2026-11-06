# :fa5-microscope: Experiment

An experiment describes an observation of the sample or a simulation of that observation. It combines measured data or a calculation range with an instrument model, peak profile, background and links to the contributing structures.

## Identify the measurement

Choose the sample form, radiation probe and beam mode that match the experiment. Constant-wavelength powder data use scattering angle; time-of-flight data use the calibrated time axis. Single-crystal observations describe reflections rather than a continuous powder profile.

The [glossary](../glossary.md) explains the experiment labels. Use the checked [example catalogue](../examples/index.md#catalogue) to find an appropriate starting model and its stated scope.

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

## An experiment file

An experiment is saved as one `.edi` data block. The example below is `experiments/cu_ka.edi` from the LiF project — a constant-wavelength X-ray simulation, so it declares a calculation range (`_data_range`) rather than measured points:

```text
data_cu_ka

_edi.schema_version 3

_experiment_type.sample_form powder
_experiment_type.beam_mode "constant wavelength"
_experiment_type.radiation_probe xray
_experiment_type.scattering_type bragg

_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion sasaki1989

_instrument.setup_wavelength 1.54056
_instrument.calib_twotheta_offset 0.

_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0.048457
_peak.broad_gauss_v -0.083053
_peak.broad_gauss_w 0.04
_peak.broad_lorentz_x 0.
_peak.broad_lorentz_y 0.049268

_data_range.two_theta_min 10.
_data_range.two_theta_max 150.
_data_range.two_theta_step 0.02

loop_
_linked_structure.structure_id
_linked_structure.scale
lif 0.01
```

A measured experiment instead carries a background definition and a `loop_` of measured points with their uncertainties. See [data formats](../data-formats.md).

Configure experiments in the [<span class="ed-interface-icons" aria-hidden="true">:fa5-desktop:</span> <span class="ed-icon-text">Application</span>](../../application/experiment/experiments.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../../python/experiments.md){ .ed-interface-link .ed-icon-label }, then [use the saved experiments from Command Line](../../cli/experiments.md).
