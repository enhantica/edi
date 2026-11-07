---
icon: fa5/book
---

# Glossary

These terms are shared by the application, Python library and command line. The interface changes how you work with them, rather than changing their scientific meaning.

## Project and model

| Term | Meaning |
| --- | --- |
| Project | The complete analysis: structures, experiments, data, analysis settings and saved results. A project can be kept as a folder or a `.zip` archive. |
| Structure | A crystallographic model of a phase, including its space group, unit cell and atom sites. |
| Experiment | The observation or simulation associated with an instrument model, profile, background and contributing structures. |
| Parameter | A model quantity such as a cell length, atom coordinate, scale or profile coefficient. A refinable parameter may be free or fixed. |
| Constraint | A declared relationship that reduces independent freedom between model quantities. A tied value is not another independently refined parameter. |

## Experiment types and labels

These coloured labels mark the attributes of a measurement. They are generated from the experiment registry and shared by the app, the example catalogue and the guides.

<!-- experiment-type-tables -->
An experiment combines one label from each family below. For example, the first refinement is <a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a>. Choose the measurement type before loading data; a listed attribute does not imply every combination is available.

### Purpose

| Label | Meaning |
| --- | --- |
| <span id="fitting"></span><a class="ed-tag ed-tag--fitting" data-ed-tag="purpose" data-ed-token="refinement" href="../user-guide/glossary/#fitting" title="Fitting measured data"><span class="ed-reference-icon" aria-hidden="true"></span>Fitting</a> | Compare a calculated model with measured intensities and refine its parameters. |
| <span id="simulation"></span><a class="ed-tag ed-tag--simulation" data-ed-tag="purpose" data-ed-token="simulation" href="../user-guide/glossary/#simulation" title="Calculation without measured data"><span class="ed-reference-icon" aria-hidden="true"></span>Simulation</a> | Calculate the pattern from the current model without measured intensities. |

### Fitting mode

| Label | Meaning |
| --- | --- |
| <span id="single-fit"></span><a class="ed-tag ed-tag--mode" data-ed-tag="fittingMode" data-ed-token="single" href="../user-guide/glossary/#single-fit" title="Fit one experiment"><span class="ed-reference-icon" aria-hidden="true"></span>Single</a> | Refine one experiment. |
| <span id="joint-fit"></span><a class="ed-tag ed-tag--mode" data-ed-tag="fittingMode" data-ed-token="joint" href="../user-guide/glossary/#joint-fit" title="Fit several experiments together"><span class="ed-reference-icon" aria-hidden="true"></span>Joint</a> | Refine several experiments together with shared model quantities. |
| <span id="sequential-fit"></span><a class="ed-tag ed-tag--mode" data-ed-tag="fittingMode" data-ed-token="sequential" href="../user-guide/glossary/#sequential-fit" title="Fit a scan using the preceding result"><span class="ed-reference-icon" aria-hidden="true"></span>Sequential</a> | Fit a scan in order, using the preceding result as the next starting point. |
| <span id="independent-fit"></span><a class="ed-tag ed-tag--mode" data-ed-tag="fittingMode" data-ed-token="independent" href="../user-guide/glossary/#independent-fit" title="Fit a scan from common starting values"><span class="ed-reference-icon" aria-hidden="true"></span>Independent</a> | Fit each dataset from the same starting model. |

### Sample form

| Label | Meaning |
| --- | --- |
| <span id="powder-diffraction"></span><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> | Diffraction from many crystallite orientations, usually measured as an intensity profile. |
| <span id="single-crystal-diffraction"></span><a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> | Diffraction from an oriented crystal, measured as individual reflection intensities. |

### Probe

| Label | Meaning |
| --- | --- |
| <span id="neutron-diffraction"></span><a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> | Diffraction using neutrons; nuclear scattering and, where modelled, magnetic scattering contribute. |
| <span id="x-ray-diffraction"></span><a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> | Diffraction using X-rays; the scattering model depends on the electron distribution. |

### Beam mode

| Label | Meaning |
| --- | --- |
| <span id="constant-wavelength"></span><a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> | A specified incident wavelength; powder patterns are commonly expressed against 2θ. |
| <span id="time-of-flight"></span><a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> | Neutron wavelengths are separated by arrival time. Calibration relates flight time to diffraction geometry. |

### Scattering type

| Label | Meaning |
| --- | --- |
| <span id="bragg-diffraction"></span><a class="ed-tag ed-tag--technique" data-ed-tag="scatteringType" data-ed-token="bragg" href="../user-guide/glossary/#bragg-diffraction" title="Bragg diffraction">Bragg</a> | Model the crystalline contribution from lattice reflections. |
<!-- /experiment-type-tables -->

## Analysis

| Term | Meaning |
| --- | --- |
| Calculation or simulation | Evaluation of the model with its present parameter values. A simulation may use a calculation range without measured observations. |
| Refinement or fit | Optimisation of the chosen free parameters against measured observations. |
| Residual | The difference between observed and calculated signal. Its pattern can reveal systematic disagreement that a single agreement factor hides. |
| Standard uncertainty | The uncertainty reported with an estimated parameter or observation. A fitted uncertainty reflects the assumptions of the fit, rather than every possible systematic error. |

## Patterns and crystallographic quantities

| Term | Meaning |
| --- | --- |
| Reflection | Diffraction associated with a set of lattice planes. A Bragg-position mark indicates where that reflection is expected in the pattern. |
| Background | The slowly varying contribution under diffraction peaks, represented by the background model chosen for the experiment. |
| Unit cell | The repeating geometry described by cell lengths and angles. |
| Fractional coordinates | A position expressed relative to the unit cell. |
| Space group | The crystallographic symmetry. Its setting identifies the coordinate convention used to describe that symmetry and the atom positions. |
| Occupancy | The occupation of an atom site. |
| Atomic displacement parameters (ADPs) | Displacement around an atom's average position. Isotropic and anisotropic representations use different parameters. |
| Scale factor | The weight of a structure's contribution to an experiment's calculated intensity. Its scientific interpretation depends on the experiment model and phase conventions. |

## Files and dictionaries

| Term | Meaning |
| --- | --- |
| Edi (`.edi`) | EasyDiffraction's saved project format. It uses readable CIF-like syntax with keys that describe the project model. |
| CIF | Crystallographic Information File, a scientific exchange format with dictionaries maintained by the IUCr. A structural CIF and a complete Edi project serve different purposes. |
| coreCIF, pdCIF, magCIF | Dictionaries of general crystallographic, powder-diffraction and magnetic-structure quantities. Edi project keys are EasyDiffraction's project names, mapped to these where one applies. |
