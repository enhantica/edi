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

## Diffraction

**Powder diffraction** <!-- glossary-label:powder --><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../user-guide/experiment-types/#powder-diffraction" title="Powder diffraction">pd</a><!-- /glossary-label --> describes diffraction from a sample containing many crystallite orientations. The measured signal is commonly an intensity profile in which reflections can overlap.

**Single-crystal diffraction** <!-- glossary-label:single-crystal --><a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../user-guide/experiment-types/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a><!-- /glossary-label --> measures individual reflections from an oriented crystal. Its observations and fit assessment differ from those of a powder profile.

**Constant wavelength (CWL)** <!-- glossary-label:constant-wavelength --><a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a><!-- /glossary-label --> describes a measurement using a specified wavelength, with a powder pattern commonly expressed against the scattering angle 2θ.

**Time of flight (TOF)** <!-- glossary-label:time-of-flight --><a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../user-guide/experiment-types/#time-of-flight" title="Time of flight">tof</a><!-- /glossary-label --> separates neutron wavelengths through arrival time. The instrument calibration relates time of flight to the diffraction geometry.

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

The catalogue uses <a class="ed-tag ed-tag--technique" href="../user-guide/experiment-types/#powder-diffraction" title="Powder diffraction">pd</a> for powder, <a class="ed-tag ed-tag--neutral" href="../user-guide/experiment-types/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> for single crystal, <a class="ed-tag ed-tag--technique" href="../user-guide/experiment-types/#neutron-diffraction" title="Neutron diffraction">neut</a> for neutron, <a class="ed-tag ed-tag--neutral" href="../user-guide/experiment-types/#x-ray-diffraction" title="X-ray diffraction">xray</a> for X-ray, <a class="ed-tag ed-tag--neutral" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> for constant wavelength and <a class="ed-tag ed-tag--technique" href="../user-guide/experiment-types/#time-of-flight" title="Time of flight">tof</a> for time of flight.

These labels identify measurement types and scientific terms. Current feature availability and model coverage are described by the interface guides and checked examples.



<!-- experiment-labels -->
For linked definitions of `pd`, `sc`, `neut`, `xray`, `cwl` and `tof`, see [Experiment types and labels](experiment-types.md).
<!-- /experiment-labels -->
