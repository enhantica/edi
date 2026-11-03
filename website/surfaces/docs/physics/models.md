---
template: physics.html
---

# Model catalogue

<span id="planned-scientific-models"></span>

Use the exact model identifier to select its explanation. Planned and proposed capabilities appear beside related models with their status; they have no selectable type token in this reference snapshot. The [parameter index](parameters.md) defines individual scientific fields. [Features and roadmap](../user-guide/features.md) distinguishes editing, execution and planned work in the four interfaces.

## Peak profiles {#peak-profiles}

### Constant-wavelength peak profiles

| Type | Scope | Explanation |
| --- | --- | --- |
| `cwl-gaussian` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> powder | [Physics](profiles/cw.md#eq-cwl-pseudovoigt) |
| `cwl-lorentzian` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> powder | [Physics](profiles/cw.md#eq-cwl-pseudovoigt) |
| `cwl-pseudo-voigt` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> powder | [Physics](profiles/cw.md#eq-caglioti) |
| `cwl-pseudo-voigt-berar-baldinozzi` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> powder | [Physics](profiles/cw.md#eq-berar-baldinozzi) |
| `cwl-tch-pseudo-voigt` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> powder | [Physics](profiles/cw.md#eq-tch) |
| `cwl-tch-pseudo-voigt-fcj` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> powder | [Physics](profiles/cw.md#eq-fcj) |

### Time-of-flight peak profiles

| Type or model | Scope | Explanation |
| --- | --- | --- |
| `tof-jorgensen` | <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../user-guide/experiment-types/#time-of-flight" title="Time of flight">tof</a> neutron powder | [Physics](profiles/tof.md#eq-jorgensen) |
| `tof-jorgensen-von-dreele` | <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../user-guide/experiment-types/#time-of-flight" title="Time of flight">tof</a> neutron powder | [Physics](profiles/tof.md#eq-jorgensen-von-dreele) |
| `tof-pseudo-voigt` | <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../user-guide/experiment-types/#time-of-flight" title="Time of flight">tof</a> neutron powder | [Physics](profiles/tof.md#tof-pseudo-voigt) |
| Ikeda–Carpenter · **Planned** | <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../user-guide/experiment-types/#time-of-flight" title="Time of flight">tof</a> pulse profile | [Planned model](profiles/tof.md#ikeda-carpenter) |

## <span class="ed-reference-icon" data-reference-category="absorption" aria-hidden="true">&#61507;</span> Absorption {#absorption}

| Type | Scope | Explanation |
| --- | --- | --- |
| `none` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a>/<a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../user-guide/experiment-types/#time-of-flight" title="Time of flight">tof</a> | [Physics](corrections/absorption.md#absorption-types) |
| `cylinder-hewat` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a>; <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../user-guide/experiment-types/#time-of-flight" title="Time of flight">tof</a> input spelling cylinder | [Physics](corrections/absorption.md#eq-hewat) |
| `cylinder-lobanov` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> | [Physics](corrections/absorption.md#eq-lobanov) |

## <span class="ed-reference-icon" data-reference-category="extinction" aria-hidden="true">&#62373;</span> Extinction {#extinction}

| Type | Scope | Explanation |
| --- | --- | --- |
| `none` | single-crystal Bragg | [Physics](corrections/extinction.md#extinction-types) |
| `becker-coppens-type-1` | single-crystal Bragg | [Physics](corrections/extinction.md#extinction-types) |
| `becker-coppens-type-2` | single-crystal Bragg | [Physics](corrections/extinction.md#extinction-types) |
| `becker-coppens-mixed` | single-crystal Bragg | [Physics](corrections/extinction.md#extinction-types) |
| `larson-isotropic` | single-crystal Bragg | [Physics](corrections/extinction.md#eq-larson) |
| `larson-anisotropic` | single-crystal Bragg | [Physics](corrections/extinction.md#eq-larson) |

## <span class="ed-reference-icon" data-reference-category="background" aria-hidden="true">&#63550;</span> Background {#background}

| Type | Scope | Explanation |
| --- | --- | --- |
| `line-segment` | powder | [Physics](background.md#eq-line-segment-background) |
| `polynomial` | powder | [Physics](background.md#eq-polynomial-background) |
| `chebyshev` | powder | [Physics](background.md#eq-chebyshev-background) |

## <span class="ed-reference-icon" data-reference-category="atom-site-aniso" aria-hidden="true">&#61618;</span> Atomic displacement {#adp}

| Type | Scope | Explanation |
| --- | --- | --- |
| `Biso` | structure | [Physics](displacement.md#eq-isotropic-adp) |
| `Uiso` | structure | [Physics](displacement.md#eq-isotropic-adp) |
| `Bani` | structure | [Physics](displacement.md#eq-anisotropic-adp) |
| `Uani` | structure | [Physics](displacement.md#eq-anisotropic-adp) |
| `beta` | structure | [Physics](displacement.md#eq-anisotropic-adp) |

## <span class="ed-reference-icon" data-reference-category="background-estimate" aria-hidden="true">&#61648;</span> Background estimation {#background-estimation}

| Type | Scope | Explanation |
| --- | --- | --- |
| `auto` | powder baseline proposal | [Physics](background.md#background-estimation) |
| `arpls` | powder baseline proposal | [Physics](background.md#eq-arpls) |
| `snip` | powder baseline proposal | [Physics](background.md#eq-snip) |
| `fabc` | powder baseline proposal | [Physics](background.md#fabc) |

## Scattering models {#scattering-models}

The current [nuclear neutron](diffraction.md#eq-nuclear-structure-factor) and [X-ray](diffraction.md#eq-xray-structure-factor) models use the source selections listed above.

| Model | Status | Explanation |
| --- | --- | --- |
| Nuclear neutron Bragg | Current | [Structure factor](diffraction.md#eq-nuclear-structure-factor) |
| X-ray Bragg | Current | [Structure factor](diffraction.md#eq-xray-structure-factor) |
| Magnetic diffraction | Planned | [Scattering](diffraction.md#magnetic-diffraction) |
| Polarized diffraction | Planned | [Scattering](diffraction.md#polarized-diffraction) |
| Total scattering and PDF | Planned | [Scattering](diffraction.md#total-scattering-and-pdf) |

## X-ray form factor {#xray-form-factor}

| Type | Scope | Explanation |
| --- | --- | --- |
| `wk1995` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> X-ray | [Physics](diffraction.md#eq-xray-structure-factor) |
| `it1992` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> X-ray | [Physics](diffraction.md#eq-xray-structure-factor) |

## X-ray dispersion {#xray-dispersion}

| Type | Scope | Explanation |
| --- | --- | --- |
| `cromer-liberman` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> X-ray | [Physics](diffraction.md#eq-xray-structure-factor) |
| `sasaki1989` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> X-ray | [Physics](diffraction.md#eq-xray-structure-factor) |
| `it1992` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> X-ray | [Physics](diffraction.md#eq-xray-structure-factor) |
| `none` | <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> X-ray | [Physics](diffraction.md#eq-xray-structure-factor) |

## Neutron scattering length {#neutron-scattering-length}

| Type | Scope | Explanation |
| --- | --- | --- |
| `rauch2003ext` | neutron | [Physics](diffraction.md#eq-nuclear-structure-factor) |
| `sears1992` | neutron | [Physics](diffraction.md#eq-nuclear-structure-factor) |

## <span class="ed-reference-icon" data-reference-category="fitting-mode" aria-hidden="true">&#61918;</span> Fitting mode {#fitting-mode}

| Type | Scope | Explanation |
| --- | --- | --- |
| `single` | project analysis | [Physics](rietveld.md#joint-refinement) |
| `joint` | project analysis | [Physics](rietveld.md#joint-refinement) |
| `sequential` | project analysis | [Physics](rietveld.md#sequential-scans) |
| `independent` | project analysis | [Physics](rietveld.md#independent-scans) |

## Intensity extraction {#intensity-extraction}

| Model | Status | Explanation |
| --- | --- | --- |
| Le Bail | Proposed | [Analysis](rietveld.md#le-bail-intensity-extraction) |
| Pawley | Proposed | [Analysis](rietveld.md#pawley-intensity-extraction) |

## Descent {#descent}

| Type | Scope | Explanation |
| --- | --- | --- |
| `ladder` | least-squares; selected strategies have bound restrictions | [Physics](minimization.md#eq-lm) |
| `fast_descent` | least-squares; selected strategies have bound restrictions | [Physics](minimization.md#eq-lm) |
| `fast_descent_linear_snap` | least-squares; selected strategies have bound restrictions | [Physics](minimization.md#eq-lm) |
| `fast_descent_guarded_linear_snap` | least-squares; selected strategies have bound restrictions | [Physics](minimization.md#eq-lm) |
| `multistart_prune` | least-squares; selected strategies have bound restrictions | [Physics](minimization.md#eq-lm) |

## <span class="ed-reference-icon" data-reference-category="preferred-orientation" aria-hidden="true">&#61774;</span> Preferred orientation {#preferred-orientation}

| Type | Scope | Explanation |
| --- | --- | --- |
| `march-dollase` | linked phase in <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../user-guide/experiment-types/#constant-wavelength" title="Constant wavelength">cwl</a> powder | [Physics](corrections/orientation.md#eq-march-dollase) |

## Reference snapshot {#reference-snapshot}

The [machine-readable catalogue](catalogue.json) records the inspected edi source and its declared crysta SDK, along with the model/parameter identifiers used for this reference. Availability is scoped to that source snapshot; a development build or installed release can differ. Use its declared model list and version when answering a build-specific question.
