---
icon: material/book-alphabet
---

# Glossary

These terms are shared by the application, Python library and command line. The interface changes how you work with them, rather than changing their scientific meaning.

The coloured measurement labels — such as <a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a>, <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a>, <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a>, <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="xray" href="../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a>, <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> and <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> — are catalogued under [Experiment types and labels](#experiment-types-and-labels) at the end of this page. That catalogue is generated from the experiment registry, so its chips always match the measurements the application supports.

## Project and model

| Term | Meaning |
| --- | --- |
| Project | The complete analysis: structures, experiments, data, analysis settings and saved results. A project can be kept as a folder or a `.zip` archive. |
| Structure | A crystallographic model of a phase, including its space group, unit cell and atom sites. |
| Experiment | The observation or simulation associated with an instrument model, profile, background and contributing structures. |
| Parameter | A model quantity such as a cell length, atom coordinate, scale or profile coefficient. A refinable parameter may be free or fixed. |
| Constraint | A declared relationship that reduces independent freedom between model quantities. A tied value is not another independently refined parameter. |

## Diffraction

**Powder diffraction** <!-- glossary-label:powder --><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a><!-- /glossary-label --> describes diffraction from a sample containing many crystallite orientations. The measured signal is commonly an intensity profile in which reflections can overlap.

**Single-crystal diffraction** <!-- glossary-label:single-crystal --><a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a><!-- /glossary-label --> measures individual reflections from an oriented crystal. Its observations and fit assessment differ from those of a powder profile.

**Constant wavelength (CWL)** <!-- glossary-label:constant-wavelength --><a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a><!-- /glossary-label --> describes a measurement using a specified wavelength, with a powder pattern commonly expressed against the scattering angle 2θ.

**Time of flight (TOF)** <!-- glossary-label:time-of-flight --><a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a><!-- /glossary-label --> separates neutron wavelengths through arrival time. The instrument calibration relates time of flight to the diffraction geometry.

**Reflection** refers to diffraction associated with a set of lattice planes. A **Bragg-position mark** indicates where that reflection is expected in the pattern.

**Background** is the slowly varying contribution under diffraction peaks, represented by the background model chosen for the experiment.

## Analysis

| Term | Meaning |
| --- | --- |
| Calculation or simulation | Evaluation of the model with its present parameter values. A simulation may use a calculation range without measured observations. |
| Refinement or fit | Optimisation of the chosen free parameters against measured observations. |
| Residual | The difference between observed and calculated signal. Its pattern can reveal systematic disagreement that a single agreement factor hides. |
| Joint fit | One simultaneous fit using several experiments and their shared model quantities. |
| Sequential fit | Fitting a scan in order, starting each dataset from the preceding fit's parameter values. |
| Independent fit | Fitting the datasets of a scan from the same template starting values. |
| Standard uncertainty | The uncertainty reported with an estimated parameter or observation. A fitted uncertainty reflects the assumptions of the fit, rather than every possible systematic error. |

## Crystallographic quantities

**Unit cell** is the repeating geometry described by cell lengths and angles. **Fractional coordinates** express a position relative to that cell.

**Space group** describes crystallographic symmetry. Its **setting** identifies the coordinate convention used to describe that symmetry and the atom positions.

**Occupancy** describes occupation of an atom site. **Atomic displacement parameters (ADPs)** describe displacement around its average position; isotropic and anisotropic representations use different quantities and conventions.

**Scale factor** weights a structure's contribution to an experiment's calculated intensity. Its scientific interpretation depends on the experiment model and phase conventions.

## Files and labels

**Edi (`.edi`)** is EasyDiffraction's saved project format. It uses readable CIF-like syntax with keys that describe the project model.

**CIF** means Crystallographic Information File, a scientific exchange format with dictionaries maintained by the IUCr. A structural CIF and a complete Edi project serve different purposes.

The **coreCIF** dictionary defines general crystallographic quantities; **pdCIF** defines powder-diffraction quantities; **magCIF** covers magnetic structures. Edi project keys are EasyDiffraction's persistence vocabulary and should not all be assumed to be IUCr dictionary items.

The catalogue uses <a class="ed-tag ed-tag--technique" href="../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> for powder, <a class="ed-tag ed-tag--neutral" href="../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> for single crystal, <a class="ed-tag ed-tag--technique" href="../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> for neutron, <a class="ed-tag ed-tag--neutral" href="../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a> for X-ray, <a class="ed-tag ed-tag--neutral" href="../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> for constant wavelength and <a class="ed-tag ed-tag--technique" href="../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> for time of flight.

These labels identify measurement types and scientific terms. Current feature availability and model coverage are described by the interface guides and checked examples.



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
