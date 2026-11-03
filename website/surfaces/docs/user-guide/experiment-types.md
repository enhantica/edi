# Experiment types and labels

Use these labels to recognise the same measurement in the app, example catalogue and guides. Colour helps scanning; the text identifies the meaning.

An experiment has several independent attributes. For example, the first refinement is <a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../user-guide/experiment-types/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../user-guide/experiment-types/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a>.

Choose the measurement type before loading data. The app enables combinations it currently supports; a listed attribute does not imply every combination is available. [See the experiment controls](../application/experiments.md).

## Purpose

Choose whether to calculate a model alone or fit it to observations.

| Label | Meaning |
| --- | --- |
| <span id="fitting"></span><a class="ed-tag ed-tag--fitting" data-ed-tag="purpose" data-ed-token="refinement" href="../user-guide/experiment-types/#fitting" title="Fitting measured data"><span class="ed-reference-icon" aria-hidden="true"></span>Fitting</a> | Compare a calculated model with measured intensities and refine its parameters. |
| <span id="simulation"></span><a class="ed-tag ed-tag--simulation" data-ed-tag="purpose" data-ed-token="simulation" href="../user-guide/experiment-types/#simulation" title="Calculation without measured data"><span class="ed-reference-icon" aria-hidden="true"></span>Simulation</a> | Calculate the pattern from the current model without measured intensities. |

## Fitting mode

Choose how experiments contribute to a fit. This is separate from their measurement type.

| Label | Meaning |
| --- | --- |
| <span id="single-fit"></span><a class="ed-tag ed-tag--mode" data-ed-tag="fittingMode" data-ed-token="single" href="../user-guide/experiment-types/#single-fit" title="Fit one experiment"><span class="ed-reference-icon" aria-hidden="true"></span>Single</a> | Refine one experiment. |
| <span id="joint-fit"></span><a class="ed-tag ed-tag--mode" data-ed-tag="fittingMode" data-ed-token="joint" href="../user-guide/experiment-types/#joint-fit" title="Fit several experiments together"><span class="ed-reference-icon" aria-hidden="true"></span>Joint</a> | Refine several experiments together with shared model quantities. |
| <span id="sequential-fit"></span><a class="ed-tag ed-tag--mode" data-ed-tag="fittingMode" data-ed-token="sequential" href="../user-guide/experiment-types/#sequential-fit" title="Fit a scan using the preceding result"><span class="ed-reference-icon" aria-hidden="true"></span>Sequential</a> | Fit a scan in order, using the preceding result as the next starting point. |
| <span id="independent-fit"></span><a class="ed-tag ed-tag--mode" data-ed-tag="fittingMode" data-ed-token="independent" href="../user-guide/experiment-types/#independent-fit" title="Fit a scan from common starting values"><span class="ed-reference-icon" aria-hidden="true"></span>Independent</a> | Fit each dataset from the same starting model. |

## Sample form

Powder profiles contain overlapping reflections; single-crystal data identify individual reflections.

| Label | Meaning |
| --- | --- |
| <span id="powder-diffraction"></span><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../user-guide/experiment-types/#powder-diffraction" title="Powder diffraction">pd</a> | Diffraction from many crystallite orientations, usually measured as an intensity profile. |
| <span id="single-crystal-diffraction"></span><a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../user-guide/experiment-types/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> | Diffraction from an oriented crystal, measured as individual reflection intensities. |

## Probe

Neutrons and X-rays interact with the sample differently. Select the probe used for the measurement.

| Label | Meaning |
| --- | --- |
| <span id="neutron-diffraction"></span><a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../user-guide/experiment-types/#neutron-diffraction" title="Neutron diffraction">neut</a> | Diffraction using neutrons; nuclear scattering and, where modelled, magnetic scattering contribute. |
| <span id="x-ray-diffraction"></span><a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../user-guide/experiment-types/#x-ray-diffraction" title="X-ray diffraction">xray</a> | Diffraction using X-rays; the scattering model depends on the electron distribution. |

## Beam mode

Constant-wavelength powder data use scattering angle; time-of-flight data use arrival time and an instrument calibration.

| Label | Meaning |
| --- | --- |
| <span id="constant-wavelength"></span><a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> | A specified incident wavelength; powder patterns are commonly expressed against 2θ. |
| <span id="time-of-flight"></span><a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../user-guide/experiment-types/#time-of-flight" title="Time of flight">tof</a> | Neutron wavelengths are separated by arrival time. Calibration relates flight time to diffraction geometry. |

## Scattering type

Bragg diffraction describes the crystalline contribution from lattice reflections.

| Label | Meaning |
| --- | --- |
| <span id="bragg-diffraction"></span><a class="ed-tag ed-tag--technique" data-ed-tag="scatteringType" data-ed-token="bragg" href="../user-guide/experiment-types/#bragg-diffraction" title="Bragg diffraction">Bragg</a> | Model the crystalline contribution from lattice reflections. |
