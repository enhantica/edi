---
icon: fa5/sliders-h
---

# Parameters

Parameters describe both the sample and the experiment. Changing a cell length moves calculated reflections; changing a scale changes their contribution to intensity; changing a background coefficient changes the signal underneath the peaks.

[Look up GUI labels, Edi keys, Python paths and CIF names](#parameter-names). The tables below lead to a description of every category and field.

## A value and its context

A parameter's value needs its name, units and place in the model to be meaningful. Typical groups include:

| Group | Examples | What to check |
| --- | --- | --- |
| [Unit cell](../physics/crystallography.md#eq-cell-metric) | Lengths and angles | Units, symmetry and plausible geometry |
| [Atom sites](../physics/diffraction.md#eq-nuclear-structure-factor) | Fractional coordinates and occupancies | Site meaning, symmetry restrictions and composition |
| [Displacements](../physics/displacement.md) | Isotropic or anisotropic displacement parameters | Convention, units and physical interpretation |
| [Instrument](../physics/calibration.md) and [profile](../physics/profiles.md) | Calibration shifts and peak-width terms | Instrument geometry and profile definition |
| [Background](../physics/background.md) and [scale](../physics/diffraction.md#phase-fractions) | Background points or terms, phase scales | Baseline behaviour and how phases contribute |

The [project model](analysis-workflow/project.md) keeps structure quantities separate from experiment quantities. They may still be correlated in a fit.

## Free and fixed

A **free** parameter is allowed to change during [refinement](../physics/rietveld.md#eq-weighted-residual). An active **fixed** parameter contributes to the calculation but keeps the value you supplied. A stored-only field is different: retaining it does not establish a calculation effect. The [parameter index](../physics/parameters.md) identifies the known stored-only fields and model-specific roles.

Review the free set before fitting. Only quantities that can vary independently belong in it. A fit cannot vary a value that describes the setup, such as the crystal radius, one that symmetry or a constraint sets, one the fit's data cannot determine, such as a cell fitted only to single-crystal intensities, or one the calculation has no derivative for yet. A value saved as free that cannot be fitted is loaded as fixed, with a message saying so. Keep the chosen free set with the saved project. Edit the free set in the [<span class="ed-interface-icons" aria-hidden="true">:fa5-desktop:</span> <span class="ed-icon-text">Application</span>](../application/analysis/parameters.md){ .ed-interface-link .ed-icon-label } or [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../python/structures.md){ .ed-interface-link .ed-icon-label }. [<span class="ed-interface-icons" aria-hidden="true">:fa5-terminal:</span> <span class="ed-icon-text">Command Line</span>](../cli/fit.md){ .ed-interface-link .ed-icon-label } uses the choices saved in the project.

## Uncertainties

A fitted parameter may have a [standard uncertainty](../physics/minimization.md#eq-covariance). Interpret it together with the measurement uncertainties, the model and correlations with other parameters.

A small standard uncertainty describes precision under the fit's assumptions. It does not remove uncertainty from calibration, sample effects, missing phases, an unsuitable background, or another systematic source.

See [fit quality](analysis-workflow/analysis.md#fit-quality) for how parameter uncertainties relate to agreement factors and the residual.

## Constraints and symmetry

Some values are related by the crystallographic symmetry; others may be linked by a declared constraint. Such values are not independent fitting directions.

For example, a symmetry restriction on a coordinate cannot be treated as an arbitrary free coordinate simply because a table displays it. The application disables the free checkbox on such a value. Inspect the relationship before interpreting how many independently variable quantities the fit has.

## Bounds and starting values

Use meaningful starting values. A fit begins at the project's current parameter values, and its final state can depend on that starting point.

Model-admissibility limits describe which values the model accepts. They have a different purpose from an optimiser's search bounds. Check the applicable model and interface documentation before treating a displayed range as an editable fitting interval.

When interpreting a constrained or limited value, check the applicable model and fitting settings. A result reaching a permitted limit can be a reason to inspect the starting assumptions, observations and parameter correlations.

For scan analyses, the [fitting mode](analysis-workflow/analysis.md#fitting-modes) determines whether each dataset starts from the same template values or from the previous fit.

## Names in code and files

A parameter can have a Python access path, an Edi persistence key, and a scientific CIF report name. These have different jobs. Use the current [Python documentation](../python/index.md) for code and [data formats](data-formats.md) for saved files. The code access path and the saved-file key need not be identical.

<!-- parameter-names -->
## Parameter names across interfaces {#parameter-names}

Compare names used in the app, saved Edi projects, Python and CIF. Select a parameter to read its meaning, units and model restrictions.

??? note "About these names"

    GUI names use the application icon patterns. Python paths are checked against the supplied examples; use `.value` or `.free` on a parameter. CIF mappings can include EasyDiffraction extensions. A dash means no declared mapping was found; a listed field is not necessarily editable or independently refinable in every model.

## Structure parameters

=== "GUI"

    <span class="ed-reference-anchor" id="names-space-group">**[<span class="ed-reference-icon" data-reference-category="space-group" aria-hidden="true">&#63423;</span> Space group](../physics/parameters.md#space-group)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Hermann-Mauguin symbol](../physics/parameters.md#space-group-name-h-m) | name |
    | [Space-group setting](../physics/parameters.md#space-group-coord-system-code) | code |
    | [Space-group number](../physics/parameters.md#space-group-it-number) | number |

    <span class="ed-reference-anchor" id="names-cell">**[<span class="ed-reference-icon" data-reference-category="cell" aria-hidden="true">&#61874;</span> Cell](../physics/parameters.md#cell)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Cell length a](../physics/parameters.md#cell-length-a) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61874;</span> <span class="ed-reference-icon" aria-hidden="true">&#62789;</span> </span><span class="ed-icon-text">a</span></span> |
    | [Cell length b](../physics/parameters.md#cell-length-b) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61874;</span> <span class="ed-reference-icon" aria-hidden="true">&#62789;</span> </span><span class="ed-icon-text">b</span></span> |
    | [Cell length c](../physics/parameters.md#cell-length-c) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61874;</span> <span class="ed-reference-icon" aria-hidden="true">&#62789;</span> </span><span class="ed-icon-text">c</span></span> |
    | [Cell angle α](../physics/parameters.md#cell-angle-alpha) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61874;</span> <span class="ed-reference-icon" aria-hidden="true">&#62789;</span> </span><span class="ed-icon-text">α</span></span> |
    | [Cell angle β](../physics/parameters.md#cell-angle-beta) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61874;</span> <span class="ed-reference-icon" aria-hidden="true">&#62789;</span> </span><span class="ed-icon-text">β</span></span> |
    | [Cell angle γ](../physics/parameters.md#cell-angle-gamma) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61874;</span> <span class="ed-reference-icon" aria-hidden="true">&#62789;</span> </span><span class="ed-icon-text">γ</span></span> |

    <span class="ed-reference-anchor" id="names-atom-site">**[<span class="ed-reference-icon" data-reference-category="atom-site" aria-hidden="true">&#62930;</span> Atom site](../physics/parameters.md#atom-site)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Atom-site identifier](../physics/parameters.md#atom-site-id) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> </span><span class="ed-icon-text">id</span></span> |
    | [Chemical element](../physics/parameters.md#atom-site-type-symbol) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> </span><span class="ed-icon-text">type</span></span> |
    | [Wyckoff position](../physics/parameters.md#atom-site-wyckoff-letter) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> </span><span class="ed-icon-text">WP</span></span> |
    | [Displacement parameter type](../physics/parameters.md#atom-site-adp-type) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> </span><span class="ed-icon-text">ADP type</span></span> |
    | [Fractional x-coordinate](../physics/parameters.md#atom-site-fract-x) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> <span class="ed-reference-icon" aria-hidden="true">&#62405;</span> </span><span class="ed-icon-text">x</span></span> |
    | [Fractional y-coordinate](../physics/parameters.md#atom-site-fract-y) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> <span class="ed-reference-icon" aria-hidden="true">&#62405;</span> </span><span class="ed-icon-text">y</span></span> |
    | [Fractional z-coordinate](../physics/parameters.md#atom-site-fract-z) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> <span class="ed-reference-icon" aria-hidden="true">&#62405;</span> </span><span class="ed-icon-text">z</span></span> |
    | [Occupancy](../physics/parameters.md#atom-site-occupancy) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> <span class="ed-reference-icon" aria-hidden="true">&#62837;</span> </span><span class="ed-icon-text">occ</span></span> |
    | [Isotropic or equivalent displacement](../physics/parameters.md#atom-site-adp-iso) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#62930;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> </span><span class="ed-icon-text">iso/eq</span></span> |

    <span class="ed-reference-anchor" id="names-atom-site-aniso">**[<span class="ed-reference-icon" data-reference-category="atom-site-aniso" aria-hidden="true">&#61618;</span> Atomic displacement](../physics/parameters.md#atom-site-aniso)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Anisotropic atom-site identifier](../physics/parameters.md#atom-site-aniso-id) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> </span><span class="ed-icon-text">id</span></span> |
    | [Displacement tensor component 11](../physics/parameters.md#atom-site-aniso-adp-11) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> </span><span class="ed-icon-text">11</span></span> |
    | [Displacement tensor component 22](../physics/parameters.md#atom-site-aniso-adp-22) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> </span><span class="ed-icon-text">22</span></span> |
    | [Displacement tensor component 33](../physics/parameters.md#atom-site-aniso-adp-33) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> </span><span class="ed-icon-text">33</span></span> |
    | [Displacement tensor component 12](../physics/parameters.md#atom-site-aniso-adp-12) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> </span><span class="ed-icon-text">12</span></span> |
    | [Displacement tensor component 13](../physics/parameters.md#atom-site-aniso-adp-13) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> </span><span class="ed-icon-text">13</span></span> |
    | [Displacement tensor component 23](../physics/parameters.md#atom-site-aniso-adp-23) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> <span class="ed-reference-icon" aria-hidden="true">&#61618;</span> </span><span class="ed-icon-text">23</span></span> |

    <span class="ed-reference-anchor" id="names-scattering-length">**[<span class="ed-reference-icon" data-reference-category="scattering-length" aria-hidden="true">&#62789;</span> Scattering length](../physics/parameters.md#scattering-length)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Type](../physics/parameters.md#scattering-length-type-symbol) | type |
    | [Neutron scattering length](../physics/parameters.md#scattering-length-length-fm) | b |

    <span class="ed-reference-anchor" id="names-geom">**[<span class="ed-reference-icon" data-reference-category="geom" aria-hidden="true">&#62790;</span> Bond settings](../physics/parameters.md#geom)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Minimum bond distance](../physics/parameters.md#geom-min-bond-distance-cutoff) | minimum distance |
    | [Bond-distance tolerance](../physics/parameters.md#geom-bond-distance-inc) | tolerance |

    <span class="ed-reference-anchor" id="names-structure-view">**[<span class="ed-reference-icon" data-reference-category="structure-view" aria-hidden="true">&#62783;</span> Appearance](../physics/parameters.md#structure-view)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Atom radius model](../physics/parameters.md#structure-view-atom-view) | atoms as |
    | [Colours](../physics/parameters.md#structure-view-colour-scheme) | colours |
    | [Atom scale](../physics/parameters.md#structure-view-atom-scale) | atom scale |
    | [Ellipsoid probability](../physics/parameters.md#structure-view-adp-probability) | probability |
    | [Labels](../physics/parameters.md#structure-view-labels) | labels |
    | [Atoms shown](../physics/parameters.md#structure-view-atoms) | atoms shown |
    | [Bonds](../physics/parameters.md#structure-view-bonds) | bonds |
    | [Cell](../physics/parameters.md#structure-view-cell) | cell |
    | [Axes](../physics/parameters.md#structure-view-axes) | axes |

    <span class="ed-reference-anchor" id="names-space-group-symop">**[<span class="ed-reference-icon" data-reference-category="space-group-symop" aria-hidden="true">&#62193;</span> Symmetry operator](../physics/parameters.md#space-group-symop)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Symmetry operation](../physics/parameters.md#space-group-symop-operation-xyz) | operation |

    <span class="ed-reference-anchor" id="names-expanded-atom-site">**[<span class="ed-reference-icon" data-reference-category="expanded-atom-site" aria-hidden="true">&#62113;</span> Atom in the cell](../physics/parameters.md#expanded-atom-site)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Source atom site](../physics/parameters.md#expanded-atom-site-atom-site-id) | site |
    | [Generating symmetry operation](../physics/parameters.md#expanded-atom-site-site-symmetry) | symmetry |
    | [Fractional x-coordinate](../physics/parameters.md#expanded-atom-site-fract-x) | x |
    | [Fractional y-coordinate](../physics/parameters.md#expanded-atom-site-fract-y) | y |
    | [Fractional z-coordinate](../physics/parameters.md#expanded-atom-site-fract-z) | z |
    | [Cartesian x-coordinate](../physics/parameters.md#expanded-atom-site-cartn-x) | X |
    | [Cartesian y-coordinate](../physics/parameters.md#expanded-atom-site-cartn-y) | Y |
    | [Cartesian z-coordinate](../physics/parameters.md#expanded-atom-site-cartn-z) | Z |
    | [Occupancy](../physics/parameters.md#expanded-atom-site-occupancy) | occ |
    | [Isotropic displacement U](../physics/parameters.md#expanded-atom-site-u-iso) | U iso |
    | [Coincident-atom cluster](../physics/parameters.md#expanded-atom-site-cluster-id) | cluster |

    <span class="ed-reference-anchor" id="names-geom-bond">**[<span class="ed-reference-icon" data-reference-category="geom-bond" aria-hidden="true">&#63396;</span> Bond](../physics/parameters.md#geom-bond)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Atom 1](../physics/parameters.md#geom-bond-expanded-atom-site-id-1) | atom 1 |
    | [Atom 2](../physics/parameters.md#geom-bond-expanded-atom-site-id-2) | atom 2 |
    | [Site 1](../physics/parameters.md#geom-bond-atom-site-label-1) | site 1 |
    | [Site 2](../physics/parameters.md#geom-bond-atom-site-label-2) | site 2 |
    | [Symmetry 1](../physics/parameters.md#geom-bond-site-symmetry-1) | symmetry 1 |
    | [Symmetry 2](../physics/parameters.md#geom-bond-site-symmetry-2) | symmetry 2 |
    | [Distance](../physics/parameters.md#geom-bond-distance) | distance |

    <span class="ed-reference-anchor" id="names-atom-sites-cartn-transform">**[<span class="ed-reference-icon" data-reference-category="atom-sites-cartn-transform" aria-hidden="true">&#62923;</span> Cartesian frame](../physics/parameters.md#atom-sites-cartn-transform)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Coordinate-transform element 11](../physics/parameters.md#atom-sites-cartn-transform-mat-11) | M₁₁ |
    | [Coordinate-transform element 12](../physics/parameters.md#atom-sites-cartn-transform-mat-12) | M₁₂ |
    | [Coordinate-transform element 13](../physics/parameters.md#atom-sites-cartn-transform-mat-13) | M₁₃ |
    | [Coordinate-transform element 21](../physics/parameters.md#atom-sites-cartn-transform-mat-21) | M₂₁ |
    | [Coordinate-transform element 22](../physics/parameters.md#atom-sites-cartn-transform-mat-22) | M₂₂ |
    | [Coordinate-transform element 23](../physics/parameters.md#atom-sites-cartn-transform-mat-23) | M₂₃ |
    | [Coordinate-transform element 31](../physics/parameters.md#atom-sites-cartn-transform-mat-31) | M₃₁ |
    | [Coordinate-transform element 32](../physics/parameters.md#atom-sites-cartn-transform-mat-32) | M₃₂ |
    | [Coordinate-transform element 33](../physics/parameters.md#atom-sites-cartn-transform-mat-33) | M₃₃ |
    | [Axes](../physics/parameters.md#atom-sites-cartn-transform-axes) | axes |

=== "Edi"

    **[<span class="ed-reference-icon" data-reference-category="space-group" aria-hidden="true">&#63423;</span> Space group](../physics/parameters.md#space-group)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Hermann-Mauguin symbol](../physics/parameters.md#space-group-name-h-m) | <code>_space_group.name_h_m</code> |
    | [Space-group setting](../physics/parameters.md#space-group-coord-system-code) | <code>_space_group.coord_system_code</code> |
    | [Space-group number](../physics/parameters.md#space-group-it-number) | <code>_space_group.it_number</code> |

    **[<span class="ed-reference-icon" data-reference-category="cell" aria-hidden="true">&#61874;</span> Cell](../physics/parameters.md#cell)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Cell length a](../physics/parameters.md#cell-length-a) | <code>_cell.length_a</code> |
    | [Cell length b](../physics/parameters.md#cell-length-b) | <code>_cell.length_b</code> |
    | [Cell length c](../physics/parameters.md#cell-length-c) | <code>_cell.length_c</code> |
    | [Cell angle α](../physics/parameters.md#cell-angle-alpha) | <code>_cell.angle_alpha</code> |
    | [Cell angle β](../physics/parameters.md#cell-angle-beta) | <code>_cell.angle_beta</code> |
    | [Cell angle γ](../physics/parameters.md#cell-angle-gamma) | <code>_cell.angle_gamma</code> |

    **[<span class="ed-reference-icon" data-reference-category="atom-site" aria-hidden="true">&#62930;</span> Atom site](../physics/parameters.md#atom-site)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Atom-site identifier](../physics/parameters.md#atom-site-id) | <code>_atom_site.id</code><br><small>Also accepted: <code>_atom_site.label</code></small> |
    | [Chemical element](../physics/parameters.md#atom-site-type-symbol) | <code>_atom_site.type_symbol</code> |
    | [Wyckoff position](../physics/parameters.md#atom-site-wyckoff-letter) | <code>_atom_site.wyckoff_letter</code> |
    | [Displacement parameter type](../physics/parameters.md#atom-site-adp-type) | <code>_atom_site.adp_type</code> |
    | [Fractional x-coordinate](../physics/parameters.md#atom-site-fract-x) | <code>_atom_site.fract_x</code> |
    | [Fractional y-coordinate](../physics/parameters.md#atom-site-fract-y) | <code>_atom_site.fract_y</code> |
    | [Fractional z-coordinate](../physics/parameters.md#atom-site-fract-z) | <code>_atom_site.fract_z</code> |
    | [Occupancy](../physics/parameters.md#atom-site-occupancy) | <code>_atom_site.occupancy</code> |
    | [Isotropic or equivalent displacement](../physics/parameters.md#atom-site-adp-iso) | <code>_atom_site.adp_iso</code> |

    **[<span class="ed-reference-icon" data-reference-category="atom-site-aniso" aria-hidden="true">&#61618;</span> Atomic displacement](../physics/parameters.md#atom-site-aniso)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Anisotropic atom-site identifier](../physics/parameters.md#atom-site-aniso-id) | <code>_atom_site_aniso.id</code><br><small>Also accepted: <code>_atom_site_aniso.label</code></small> |
    | [Displacement tensor component 11](../physics/parameters.md#atom-site-aniso-adp-11) | <code>_atom_site_aniso.adp_11</code> |
    | [Displacement tensor component 22](../physics/parameters.md#atom-site-aniso-adp-22) | <code>_atom_site_aniso.adp_22</code> |
    | [Displacement tensor component 33](../physics/parameters.md#atom-site-aniso-adp-33) | <code>_atom_site_aniso.adp_33</code> |
    | [Displacement tensor component 12](../physics/parameters.md#atom-site-aniso-adp-12) | <code>_atom_site_aniso.adp_12</code> |
    | [Displacement tensor component 13](../physics/parameters.md#atom-site-aniso-adp-13) | <code>_atom_site_aniso.adp_13</code> |
    | [Displacement tensor component 23](../physics/parameters.md#atom-site-aniso-adp-23) | <code>_atom_site_aniso.adp_23</code> |

    **[<span class="ed-reference-icon" data-reference-category="scattering-length" aria-hidden="true">&#62789;</span> Scattering length](../physics/parameters.md#scattering-length)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Type](../physics/parameters.md#scattering-length-type-symbol) | <code>_scattering_length.type_symbol</code> |
    | [Neutron scattering length](../physics/parameters.md#scattering-length-length-fm) | <code>_scattering_length.length_fm</code> |

    **[<span class="ed-reference-icon" data-reference-category="geom" aria-hidden="true">&#62790;</span> Bond settings](../physics/parameters.md#geom)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Minimum bond distance](../physics/parameters.md#geom-min-bond-distance-cutoff) | <code>_geom.min_bond_distance_cutoff</code> |
    | [Bond-distance tolerance](../physics/parameters.md#geom-bond-distance-inc) | <code>_geom.bond_distance_inc</code> |

    **[<span class="ed-reference-icon" data-reference-category="structure-view" aria-hidden="true">&#62783;</span> Appearance](../physics/parameters.md#structure-view)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Atom radius model](../physics/parameters.md#structure-view-atom-view) | <code>_structure_view.atom_view</code> |
    | [Colours](../physics/parameters.md#structure-view-colour-scheme) | <code>_structure_view.colour_scheme</code> |
    | [Atom scale](../physics/parameters.md#structure-view-atom-scale) | <code>_structure_view.atom_scale</code> |
    | [Ellipsoid probability](../physics/parameters.md#structure-view-adp-probability) | <code>_structure_view.adp_probability</code> |
    | [Labels](../physics/parameters.md#structure-view-labels) | <code>_structure_view.labels</code> |
    | [Atoms shown](../physics/parameters.md#structure-view-atoms) | <code>_structure_view.atoms</code> |
    | [Bonds](../physics/parameters.md#structure-view-bonds) | <code>_structure_view.bonds</code> |
    | [Cell](../physics/parameters.md#structure-view-cell) | <code>_structure_view.cell</code> |
    | [Axes](../physics/parameters.md#structure-view-axes) | <code>_structure_view.axes</code> |

    **[<span class="ed-reference-icon" data-reference-category="space-group-symop" aria-hidden="true">&#62193;</span> Symmetry operator](../physics/parameters.md#space-group-symop)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Symmetry operation](../physics/parameters.md#space-group-symop-operation-xyz) | <code>_space_group_symop.operation_xyz</code> |

    **[<span class="ed-reference-icon" data-reference-category="expanded-atom-site" aria-hidden="true">&#62113;</span> Atom in the cell](../physics/parameters.md#expanded-atom-site)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Source atom site](../physics/parameters.md#expanded-atom-site-atom-site-id) | <code>_expanded_atom_site.atom_site_id</code> |
    | [Generating symmetry operation](../physics/parameters.md#expanded-atom-site-site-symmetry) | <code>_expanded_atom_site.site_symmetry</code> |
    | [Fractional x-coordinate](../physics/parameters.md#expanded-atom-site-fract-x) | <code>_expanded_atom_site.fract_x</code> |
    | [Fractional y-coordinate](../physics/parameters.md#expanded-atom-site-fract-y) | <code>_expanded_atom_site.fract_y</code> |
    | [Fractional z-coordinate](../physics/parameters.md#expanded-atom-site-fract-z) | <code>_expanded_atom_site.fract_z</code> |
    | [Cartesian x-coordinate](../physics/parameters.md#expanded-atom-site-cartn-x) | <code>_expanded_atom_site.cartn_x</code> |
    | [Cartesian y-coordinate](../physics/parameters.md#expanded-atom-site-cartn-y) | <code>_expanded_atom_site.cartn_y</code> |
    | [Cartesian z-coordinate](../physics/parameters.md#expanded-atom-site-cartn-z) | <code>_expanded_atom_site.cartn_z</code> |
    | [Occupancy](../physics/parameters.md#expanded-atom-site-occupancy) | <code>_expanded_atom_site.occupancy</code> |
    | [Isotropic displacement U](../physics/parameters.md#expanded-atom-site-u-iso) | <code>_expanded_atom_site.u_iso</code> |
    | [Coincident-atom cluster](../physics/parameters.md#expanded-atom-site-cluster-id) | <code>_expanded_atom_site.cluster_id</code> |

    **[<span class="ed-reference-icon" data-reference-category="geom-bond" aria-hidden="true">&#63396;</span> Bond](../physics/parameters.md#geom-bond)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Atom 1](../physics/parameters.md#geom-bond-expanded-atom-site-id-1) | <code>_geom_bond.expanded_atom_site_id_1</code> |
    | [Atom 2](../physics/parameters.md#geom-bond-expanded-atom-site-id-2) | <code>_geom_bond.expanded_atom_site_id_2</code> |
    | [Site 1](../physics/parameters.md#geom-bond-atom-site-label-1) | <code>_geom_bond.atom_site_label_1</code> |
    | [Site 2](../physics/parameters.md#geom-bond-atom-site-label-2) | <code>_geom_bond.atom_site_label_2</code> |
    | [Symmetry 1](../physics/parameters.md#geom-bond-site-symmetry-1) | <code>_geom_bond.site_symmetry_1</code> |
    | [Symmetry 2](../physics/parameters.md#geom-bond-site-symmetry-2) | <code>_geom_bond.site_symmetry_2</code> |
    | [Distance](../physics/parameters.md#geom-bond-distance) | <code>_geom_bond.distance</code> |

    **[<span class="ed-reference-icon" data-reference-category="atom-sites-cartn-transform" aria-hidden="true">&#62923;</span> Cartesian frame](../physics/parameters.md#atom-sites-cartn-transform)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Coordinate-transform element 11](../physics/parameters.md#atom-sites-cartn-transform-mat-11) | <code>_atom_sites_cartn_transform.mat_11</code> |
    | [Coordinate-transform element 12](../physics/parameters.md#atom-sites-cartn-transform-mat-12) | <code>_atom_sites_cartn_transform.mat_12</code> |
    | [Coordinate-transform element 13](../physics/parameters.md#atom-sites-cartn-transform-mat-13) | <code>_atom_sites_cartn_transform.mat_13</code> |
    | [Coordinate-transform element 21](../physics/parameters.md#atom-sites-cartn-transform-mat-21) | <code>_atom_sites_cartn_transform.mat_21</code> |
    | [Coordinate-transform element 22](../physics/parameters.md#atom-sites-cartn-transform-mat-22) | <code>_atom_sites_cartn_transform.mat_22</code> |
    | [Coordinate-transform element 23](../physics/parameters.md#atom-sites-cartn-transform-mat-23) | <code>_atom_sites_cartn_transform.mat_23</code> |
    | [Coordinate-transform element 31](../physics/parameters.md#atom-sites-cartn-transform-mat-31) | <code>_atom_sites_cartn_transform.mat_31</code> |
    | [Coordinate-transform element 32](../physics/parameters.md#atom-sites-cartn-transform-mat-32) | <code>_atom_sites_cartn_transform.mat_32</code> |
    | [Coordinate-transform element 33](../physics/parameters.md#atom-sites-cartn-transform-mat-33) | <code>_atom_sites_cartn_transform.mat_33</code> |
    | [Axes](../physics/parameters.md#atom-sites-cartn-transform-axes) | <code>_atom_sites_cartn_transform.axes</code> |

=== "Python"

    **[<span class="ed-reference-icon" data-reference-category="space-group" aria-hidden="true">&#63423;</span> Space group](../physics/parameters.md#space-group)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Hermann-Mauguin symbol](../physics/parameters.md#space-group-name-h-m) | <code>project.structures[0].space_group.name_h_m</code> |
    | [Space-group setting](../physics/parameters.md#space-group-coord-system-code) | <code>project.structures[0].space_group.coord_system_code</code> |
    | [Space-group number](../physics/parameters.md#space-group-it-number) | <code>project.structures[0].space_group.it_number</code> |

    **[<span class="ed-reference-icon" data-reference-category="cell" aria-hidden="true">&#61874;</span> Cell](../physics/parameters.md#cell)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Cell length a](../physics/parameters.md#cell-length-a) | <code>project.structures[0].cell.length_a</code> |
    | [Cell length b](../physics/parameters.md#cell-length-b) | <code>project.structures[0].cell.length_b</code> |
    | [Cell length c](../physics/parameters.md#cell-length-c) | <code>project.structures[0].cell.length_c</code> |
    | [Cell angle α](../physics/parameters.md#cell-angle-alpha) | <code>project.structures[0].cell.angle_alpha</code> |
    | [Cell angle β](../physics/parameters.md#cell-angle-beta) | <code>project.structures[0].cell.angle_beta</code> |
    | [Cell angle γ](../physics/parameters.md#cell-angle-gamma) | <code>project.structures[0].cell.angle_gamma</code> |

    **[<span class="ed-reference-icon" data-reference-category="atom-site" aria-hidden="true">&#62930;</span> Atom site](../physics/parameters.md#atom-site)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Atom-site identifier](../physics/parameters.md#atom-site-id) | <code>project.structures[0].atom_sites[0].id</code> |
    | [Chemical element](../physics/parameters.md#atom-site-type-symbol) | <code>project.structures[0].atom_sites[0].type_symbol</code> |
    | [Wyckoff position](../physics/parameters.md#atom-site-wyckoff-letter) | <code>project.structures[0].atom_sites[0].wyckoff_letter</code> |
    | [Displacement parameter type](../physics/parameters.md#atom-site-adp-type) | <code>project.structures[0].atom_sites[0].adp_type</code> |
    | [Fractional x-coordinate](../physics/parameters.md#atom-site-fract-x) | <code>project.structures[0].atom_sites[0].fract_x</code> |
    | [Fractional y-coordinate](../physics/parameters.md#atom-site-fract-y) | <code>project.structures[0].atom_sites[0].fract_y</code> |
    | [Fractional z-coordinate](../physics/parameters.md#atom-site-fract-z) | <code>project.structures[0].atom_sites[0].fract_z</code> |
    | [Occupancy](../physics/parameters.md#atom-site-occupancy) | <code>project.structures[0].atom_sites[0].occupancy</code> |
    | [Isotropic or equivalent displacement](../physics/parameters.md#atom-site-adp-iso) | <code>project.structures[0].atom_sites[0].adp_iso</code> |

    **[<span class="ed-reference-icon" data-reference-category="atom-site-aniso" aria-hidden="true">&#61618;</span> Atomic displacement](../physics/parameters.md#atom-site-aniso)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Anisotropic atom-site identifier](../physics/parameters.md#atom-site-aniso-id) | <code>project.structures[0].atom_site_aniso[0].id</code> |
    | [Displacement tensor component 11](../physics/parameters.md#atom-site-aniso-adp-11) | <code>project.structures[0].atom_site_aniso[0].adp_11</code> |
    | [Displacement tensor component 22](../physics/parameters.md#atom-site-aniso-adp-22) | <code>project.structures[0].atom_site_aniso[0].adp_22</code> |
    | [Displacement tensor component 33](../physics/parameters.md#atom-site-aniso-adp-33) | <code>project.structures[0].atom_site_aniso[0].adp_33</code> |
    | [Displacement tensor component 12](../physics/parameters.md#atom-site-aniso-adp-12) | <code>project.structures[0].atom_site_aniso[0].adp_12</code> |
    | [Displacement tensor component 13](../physics/parameters.md#atom-site-aniso-adp-13) | <code>project.structures[0].atom_site_aniso[0].adp_13</code> |
    | [Displacement tensor component 23](../physics/parameters.md#atom-site-aniso-adp-23) | <code>project.structures[0].atom_site_aniso[0].adp_23</code> |

    **[<span class="ed-reference-icon" data-reference-category="scattering-length" aria-hidden="true">&#62789;</span> Scattering length](../physics/parameters.md#scattering-length)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Type](../physics/parameters.md#scattering-length-type-symbol) | — |
    | [Neutron scattering length](../physics/parameters.md#scattering-length-length-fm) | — |

    **[<span class="ed-reference-icon" data-reference-category="geom" aria-hidden="true">&#62790;</span> Bond settings](../physics/parameters.md#geom)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Minimum bond distance](../physics/parameters.md#geom-min-bond-distance-cutoff) | <code>project.structures[0].geom.min_bond_distance_cutoff</code> |
    | [Bond-distance tolerance](../physics/parameters.md#geom-bond-distance-inc) | <code>project.structures[0].geom.bond_distance_inc</code> |

    **[<span class="ed-reference-icon" data-reference-category="structure-view" aria-hidden="true">&#62783;</span> Appearance](../physics/parameters.md#structure-view)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Atom radius model](../physics/parameters.md#structure-view-atom-view) | — |
    | [Colours](../physics/parameters.md#structure-view-colour-scheme) | — |
    | [Atom scale](../physics/parameters.md#structure-view-atom-scale) | — |
    | [Ellipsoid probability](../physics/parameters.md#structure-view-adp-probability) | — |
    | [Labels](../physics/parameters.md#structure-view-labels) | — |
    | [Atoms shown](../physics/parameters.md#structure-view-atoms) | — |
    | [Bonds](../physics/parameters.md#structure-view-bonds) | — |
    | [Cell](../physics/parameters.md#structure-view-cell) | — |
    | [Axes](../physics/parameters.md#structure-view-axes) | — |

    **[<span class="ed-reference-icon" data-reference-category="space-group-symop" aria-hidden="true">&#62193;</span> Symmetry operator](../physics/parameters.md#space-group-symop)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Symmetry operation](../physics/parameters.md#space-group-symop-operation-xyz) | — |

    **[<span class="ed-reference-icon" data-reference-category="expanded-atom-site" aria-hidden="true">&#62113;</span> Atom in the cell](../physics/parameters.md#expanded-atom-site)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Source atom site](../physics/parameters.md#expanded-atom-site-atom-site-id) | — |
    | [Generating symmetry operation](../physics/parameters.md#expanded-atom-site-site-symmetry) | — |
    | [Fractional x-coordinate](../physics/parameters.md#expanded-atom-site-fract-x) | — |
    | [Fractional y-coordinate](../physics/parameters.md#expanded-atom-site-fract-y) | — |
    | [Fractional z-coordinate](../physics/parameters.md#expanded-atom-site-fract-z) | — |
    | [Cartesian x-coordinate](../physics/parameters.md#expanded-atom-site-cartn-x) | — |
    | [Cartesian y-coordinate](../physics/parameters.md#expanded-atom-site-cartn-y) | — |
    | [Cartesian z-coordinate](../physics/parameters.md#expanded-atom-site-cartn-z) | — |
    | [Occupancy](../physics/parameters.md#expanded-atom-site-occupancy) | — |
    | [Isotropic displacement U](../physics/parameters.md#expanded-atom-site-u-iso) | — |
    | [Coincident-atom cluster](../physics/parameters.md#expanded-atom-site-cluster-id) | — |

    **[<span class="ed-reference-icon" data-reference-category="geom-bond" aria-hidden="true">&#63396;</span> Bond](../physics/parameters.md#geom-bond)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Atom 1](../physics/parameters.md#geom-bond-expanded-atom-site-id-1) | — |
    | [Atom 2](../physics/parameters.md#geom-bond-expanded-atom-site-id-2) | — |
    | [Site 1](../physics/parameters.md#geom-bond-atom-site-label-1) | — |
    | [Site 2](../physics/parameters.md#geom-bond-atom-site-label-2) | — |
    | [Symmetry 1](../physics/parameters.md#geom-bond-site-symmetry-1) | — |
    | [Symmetry 2](../physics/parameters.md#geom-bond-site-symmetry-2) | — |
    | [Distance](../physics/parameters.md#geom-bond-distance) | — |

    **[<span class="ed-reference-icon" data-reference-category="atom-sites-cartn-transform" aria-hidden="true">&#62923;</span> Cartesian frame](../physics/parameters.md#atom-sites-cartn-transform)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Coordinate-transform element 11](../physics/parameters.md#atom-sites-cartn-transform-mat-11) | — |
    | [Coordinate-transform element 12](../physics/parameters.md#atom-sites-cartn-transform-mat-12) | — |
    | [Coordinate-transform element 13](../physics/parameters.md#atom-sites-cartn-transform-mat-13) | — |
    | [Coordinate-transform element 21](../physics/parameters.md#atom-sites-cartn-transform-mat-21) | — |
    | [Coordinate-transform element 22](../physics/parameters.md#atom-sites-cartn-transform-mat-22) | — |
    | [Coordinate-transform element 23](../physics/parameters.md#atom-sites-cartn-transform-mat-23) | — |
    | [Coordinate-transform element 31](../physics/parameters.md#atom-sites-cartn-transform-mat-31) | — |
    | [Coordinate-transform element 32](../physics/parameters.md#atom-sites-cartn-transform-mat-32) | — |
    | [Coordinate-transform element 33](../physics/parameters.md#atom-sites-cartn-transform-mat-33) | — |
    | [Axes](../physics/parameters.md#atom-sites-cartn-transform-axes) | — |

=== "CIF"

    **[<span class="ed-reference-icon" data-reference-category="space-group" aria-hidden="true">&#63423;</span> Space group](../physics/parameters.md#space-group)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Hermann-Mauguin symbol](../physics/parameters.md#space-group-name-h-m) | <code>_space_group.name_H-M_alt</code><details><summary>Accepted aliases</summary><code>_space_group_name_H-M_alt</code><br><code>_symmetry.space_group_name_H-M</code><br><code>_symmetry_space_group_name_H-M</code></details> |
    | [Space-group setting](../physics/parameters.md#space-group-coord-system-code) | <code>_space_group.IT_coordinate_system_code</code><details><summary>Accepted aliases</summary><code>_space_group_IT_coordinate_system_code</code><br><code>_symmetry.IT_coordinate_system_code</code><br><code>_symmetry_IT_coordinate_system_code</code></details> |
    | [Space-group number](../physics/parameters.md#space-group-it-number) | <code>_space_group.IT_number</code><details><summary>Accepted aliases</summary><code>_space_group_IT_number</code><br><code>_symmetry.Int_Tables_number</code><br><code>_symmetry_Int_Tables_number</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="cell" aria-hidden="true">&#61874;</span> Cell](../physics/parameters.md#cell)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Cell length a](../physics/parameters.md#cell-length-a) | <code>_cell.length_a</code><details><summary>Accepted aliases</summary><code>_cell_length_a</code></details> |
    | [Cell length b](../physics/parameters.md#cell-length-b) | <code>_cell.length_b</code><details><summary>Accepted aliases</summary><code>_cell_length_b</code></details> |
    | [Cell length c](../physics/parameters.md#cell-length-c) | <code>_cell.length_c</code><details><summary>Accepted aliases</summary><code>_cell_length_c</code></details> |
    | [Cell angle α](../physics/parameters.md#cell-angle-alpha) | <code>_cell.angle_alpha</code><details><summary>Accepted aliases</summary><code>_cell_angle_alpha</code></details> |
    | [Cell angle β](../physics/parameters.md#cell-angle-beta) | <code>_cell.angle_beta</code><details><summary>Accepted aliases</summary><code>_cell_angle_beta</code></details> |
    | [Cell angle γ](../physics/parameters.md#cell-angle-gamma) | <code>_cell.angle_gamma</code><details><summary>Accepted aliases</summary><code>_cell_angle_gamma</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="atom-site" aria-hidden="true">&#62930;</span> Atom site](../physics/parameters.md#atom-site)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Atom-site identifier](../physics/parameters.md#atom-site-id) | <code>_atom_site.label</code><details><summary>Accepted aliases</summary><code>_atom_site_label</code><br><code>_atom_site.id</code></details> |
    | [Chemical element](../physics/parameters.md#atom-site-type-symbol) | <code>_atom_site.type_symbol</code><details><summary>Accepted aliases</summary><code>_atom_site_type_symbol</code></details> |
    | [Wyckoff position](../physics/parameters.md#atom-site-wyckoff-letter) | <code>_atom_site.Wyckoff_symbol</code><details><summary>Accepted aliases</summary><code>_atom_site_Wyckoff_symbol</code><br><code>_atom_site.Wyckoff_letter</code></details> |
    | [Displacement parameter type](../physics/parameters.md#atom-site-adp-type) | <code>_atom_site.ADP_type</code><details><summary>Accepted aliases</summary><code>_atom_site_ADP_type</code><br><code>_atom_site_thermal_displace_type</code><br><code>_atom_site.thermal_displace_type</code></details> |
    | [Fractional x-coordinate](../physics/parameters.md#atom-site-fract-x) | <code>_atom_site.fract_x</code><details><summary>Accepted aliases</summary><code>_atom_site_fract_x</code></details> |
    | [Fractional y-coordinate](../physics/parameters.md#atom-site-fract-y) | <code>_atom_site.fract_y</code><details><summary>Accepted aliases</summary><code>_atom_site_fract_y</code></details> |
    | [Fractional z-coordinate](../physics/parameters.md#atom-site-fract-z) | <code>_atom_site.fract_z</code><details><summary>Accepted aliases</summary><code>_atom_site_fract_z</code></details> |
    | [Occupancy](../physics/parameters.md#atom-site-occupancy) | <code>_atom_site.occupancy</code><details><summary>Accepted aliases</summary><code>_atom_site_occupancy</code></details> |
    | [Isotropic or equivalent displacement](../physics/parameters.md#atom-site-adp-iso) | <code>Biso</code>: <code>_atom_site.B_iso_or_equiv</code><br><code>Uiso</code>: <code>_atom_site.U_iso_or_equiv</code><br><code>Bani</code>: <code>_atom_site.B_iso_or_equiv</code><br><code>Uani</code>: <code>_atom_site.U_iso_or_equiv</code><br><code>beta</code>: <code>_atom_site.B_iso_or_equiv</code><details><summary>Accepted aliases</summary><code>_atom_site_B_iso_or_equiv</code><br><code>_atom_site_U_iso_or_equiv</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="atom-site-aniso" aria-hidden="true">&#61618;</span> Atomic displacement](../physics/parameters.md#atom-site-aniso)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Anisotropic atom-site identifier](../physics/parameters.md#atom-site-aniso-id) | <code>_atom_site_aniso.label</code><details><summary>Accepted aliases</summary><code>_atom_site_aniso_label</code><br><code>_atom_site_anisotrop.id</code></details> |
    | [Displacement tensor component 11](../physics/parameters.md#atom-site-aniso-adp-11) | <code>Uani</code>: <code>_atom_site_aniso.U_11</code><br><code>Bani</code>: <code>_atom_site_aniso.B_11</code><br><code>beta</code>: <code>_atom_site_aniso.beta_11</code><details><summary>Accepted aliases</summary><code>_atom_site_aniso_B_11</code><br><code>_atom_site.aniso_B[1][1]</code><br><code>_atom_site_anisotrop.B[1][1]</code><br><code>_atom_site_aniso_U_11</code><br><code>_atom_site.aniso_U[1][1]</code><br><code>_atom_site_anisotrop.U[1][1]</code><br><code>_atom_site_aniso_beta_11</code></details> |
    | [Displacement tensor component 22](../physics/parameters.md#atom-site-aniso-adp-22) | <code>Uani</code>: <code>_atom_site_aniso.U_22</code><br><code>Bani</code>: <code>_atom_site_aniso.B_22</code><br><code>beta</code>: <code>_atom_site_aniso.beta_22</code><details><summary>Accepted aliases</summary><code>_atom_site_aniso_B_22</code><br><code>_atom_site.aniso_B[2][2]</code><br><code>_atom_site_anisotrop.B[2][2]</code><br><code>_atom_site_aniso_U_22</code><br><code>_atom_site.aniso_U[2][2]</code><br><code>_atom_site_anisotrop.U[2][2]</code><br><code>_atom_site_aniso_beta_22</code></details> |
    | [Displacement tensor component 33](../physics/parameters.md#atom-site-aniso-adp-33) | <code>Uani</code>: <code>_atom_site_aniso.U_33</code><br><code>Bani</code>: <code>_atom_site_aniso.B_33</code><br><code>beta</code>: <code>_atom_site_aniso.beta_33</code><details><summary>Accepted aliases</summary><code>_atom_site_aniso_B_33</code><br><code>_atom_site.aniso_B[3][3]</code><br><code>_atom_site_anisotrop.B[3][3]</code><br><code>_atom_site_aniso_U_33</code><br><code>_atom_site.aniso_U[3][3]</code><br><code>_atom_site_anisotrop.U[3][3]</code><br><code>_atom_site_aniso_beta_33</code></details> |
    | [Displacement tensor component 12](../physics/parameters.md#atom-site-aniso-adp-12) | <code>Uani</code>: <code>_atom_site_aniso.U_12</code><br><code>Bani</code>: <code>_atom_site_aniso.B_12</code><br><code>beta</code>: <code>_atom_site_aniso.beta_12</code><details><summary>Accepted aliases</summary><code>_atom_site_aniso_B_12</code><br><code>_atom_site.aniso_B[1][2]</code><br><code>_atom_site_anisotrop.B[1][2]</code><br><code>_atom_site_aniso_U_12</code><br><code>_atom_site.aniso_U[1][2]</code><br><code>_atom_site_anisotrop.U[1][2]</code><br><code>_atom_site_aniso_beta_12</code></details> |
    | [Displacement tensor component 13](../physics/parameters.md#atom-site-aniso-adp-13) | <code>Uani</code>: <code>_atom_site_aniso.U_13</code><br><code>Bani</code>: <code>_atom_site_aniso.B_13</code><br><code>beta</code>: <code>_atom_site_aniso.beta_13</code><details><summary>Accepted aliases</summary><code>_atom_site_aniso_B_13</code><br><code>_atom_site.aniso_B[1][3]</code><br><code>_atom_site_anisotrop.B[1][3]</code><br><code>_atom_site_aniso_U_13</code><br><code>_atom_site.aniso_U[1][3]</code><br><code>_atom_site_anisotrop.U[1][3]</code><br><code>_atom_site_aniso_beta_13</code></details> |
    | [Displacement tensor component 23](../physics/parameters.md#atom-site-aniso-adp-23) | <code>Uani</code>: <code>_atom_site_aniso.U_23</code><br><code>Bani</code>: <code>_atom_site_aniso.B_23</code><br><code>beta</code>: <code>_atom_site_aniso.beta_23</code><details><summary>Accepted aliases</summary><code>_atom_site_aniso_B_23</code><br><code>_atom_site.aniso_B[2][3]</code><br><code>_atom_site_anisotrop.B[2][3]</code><br><code>_atom_site_aniso_U_23</code><br><code>_atom_site.aniso_U[2][3]</code><br><code>_atom_site_anisotrop.U[2][3]</code><br><code>_atom_site_aniso_beta_23</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="scattering-length" aria-hidden="true">&#62789;</span> Scattering length](../physics/parameters.md#scattering-length)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Type](../physics/parameters.md#scattering-length-type-symbol) | <code>_edi_scattering_length.type_symbol</code> |
    | [Neutron scattering length](../physics/parameters.md#scattering-length-length-fm) | <code>_edi_scattering_length.length_fm</code> |

    **[<span class="ed-reference-icon" data-reference-category="geom" aria-hidden="true">&#62790;</span> Bond settings](../physics/parameters.md#geom)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Minimum bond distance](../physics/parameters.md#geom-min-bond-distance-cutoff) | <code>_geom.min_bond_distance_cutoff</code> |
    | [Bond-distance tolerance](../physics/parameters.md#geom-bond-distance-inc) | <code>_geom.bond_distance_incr</code> |

    **[<span class="ed-reference-icon" data-reference-category="structure-view" aria-hidden="true">&#62783;</span> Appearance](../physics/parameters.md#structure-view)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Atom radius model](../physics/parameters.md#structure-view-atom-view) | <code>_edi_structure_view.atom_view</code> |
    | [Colours](../physics/parameters.md#structure-view-colour-scheme) | <code>_edi_structure_view.colour_scheme</code> |
    | [Atom scale](../physics/parameters.md#structure-view-atom-scale) | <code>_edi_structure_view.atom_scale</code> |
    | [Ellipsoid probability](../physics/parameters.md#structure-view-adp-probability) | <code>_edi_structure_view.adp_probability</code> |
    | [Labels](../physics/parameters.md#structure-view-labels) | <code>_edi_structure_view.labels</code> |
    | [Atoms shown](../physics/parameters.md#structure-view-atoms) | <code>_edi_structure_view.atoms</code> |
    | [Bonds](../physics/parameters.md#structure-view-bonds) | <code>_edi_structure_view.bonds</code> |
    | [Cell](../physics/parameters.md#structure-view-cell) | <code>_edi_structure_view.cell</code> |
    | [Axes](../physics/parameters.md#structure-view-axes) | <code>_edi_structure_view.axes</code> |

    **[<span class="ed-reference-icon" data-reference-category="space-group-symop" aria-hidden="true">&#62193;</span> Symmetry operator](../physics/parameters.md#space-group-symop)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Symmetry operation](../physics/parameters.md#space-group-symop-operation-xyz) | <code>_space_group_symop.operation_xyz</code><details><summary>Accepted aliases</summary><code>_space_group_symop_operation_xyz</code><br><code>_symmetry_equiv.pos_as_xyz</code><br><code>_symmetry_equiv_pos_as_xyz</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="expanded-atom-site" aria-hidden="true">&#62113;</span> Atom in the cell](../physics/parameters.md#expanded-atom-site)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Source atom site](../physics/parameters.md#expanded-atom-site-atom-site-id) | <code>_edi_expanded_atom_site.atom_site_id</code> |
    | [Generating symmetry operation](../physics/parameters.md#expanded-atom-site-site-symmetry) | <code>_edi_expanded_atom_site.site_symmetry</code> |
    | [Fractional x-coordinate](../physics/parameters.md#expanded-atom-site-fract-x) | <code>_edi_expanded_atom_site.fract_x</code> |
    | [Fractional y-coordinate](../physics/parameters.md#expanded-atom-site-fract-y) | <code>_edi_expanded_atom_site.fract_y</code> |
    | [Fractional z-coordinate](../physics/parameters.md#expanded-atom-site-fract-z) | <code>_edi_expanded_atom_site.fract_z</code> |
    | [Cartesian x-coordinate](../physics/parameters.md#expanded-atom-site-cartn-x) | <code>_edi_expanded_atom_site.cartn_x</code> |
    | [Cartesian y-coordinate](../physics/parameters.md#expanded-atom-site-cartn-y) | <code>_edi_expanded_atom_site.cartn_y</code> |
    | [Cartesian z-coordinate](../physics/parameters.md#expanded-atom-site-cartn-z) | <code>_edi_expanded_atom_site.cartn_z</code> |
    | [Occupancy](../physics/parameters.md#expanded-atom-site-occupancy) | <code>_edi_expanded_atom_site.occupancy</code> |
    | [Isotropic displacement U](../physics/parameters.md#expanded-atom-site-u-iso) | <code>_edi_expanded_atom_site.u_iso</code> |
    | [Coincident-atom cluster](../physics/parameters.md#expanded-atom-site-cluster-id) | <code>_edi_expanded_atom_site.cluster_id</code> |

    **[<span class="ed-reference-icon" data-reference-category="geom-bond" aria-hidden="true">&#63396;</span> Bond](../physics/parameters.md#geom-bond)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Atom 1](../physics/parameters.md#geom-bond-expanded-atom-site-id-1) | <code>_edi_geom_bond.expanded_atom_site_id_1</code> |
    | [Atom 2](../physics/parameters.md#geom-bond-expanded-atom-site-id-2) | <code>_edi_geom_bond.expanded_atom_site_id_2</code> |
    | [Site 1](../physics/parameters.md#geom-bond-atom-site-label-1) | <code>_geom_bond.atom_site_label_1</code><details><summary>Accepted aliases</summary><code>_geom_bond_atom_site_label_1</code><br><code>_geom_bond.atom_site_id_1</code></details> |
    | [Site 2](../physics/parameters.md#geom-bond-atom-site-label-2) | <code>_geom_bond.atom_site_label_2</code><details><summary>Accepted aliases</summary><code>_geom_bond_atom_site_label_2</code><br><code>_geom_bond.atom_site_id_2</code></details> |
    | [Symmetry 1](../physics/parameters.md#geom-bond-site-symmetry-1) | <code>_geom_bond.site_symmetry_1</code><details><summary>Accepted aliases</summary><code>_geom_bond_site_symmetry_1</code></details> |
    | [Symmetry 2](../physics/parameters.md#geom-bond-site-symmetry-2) | <code>_geom_bond.site_symmetry_2</code><details><summary>Accepted aliases</summary><code>_geom_bond_site_symmetry_2</code></details> |
    | [Distance](../physics/parameters.md#geom-bond-distance) | <code>_geom_bond.distance</code><details><summary>Accepted aliases</summary><code>_geom_bond_distance</code><br><code>_geom_bond.dist</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="atom-sites-cartn-transform" aria-hidden="true">&#62923;</span> Cartesian frame](../physics/parameters.md#atom-sites-cartn-transform)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Coordinate-transform element 11](../physics/parameters.md#atom-sites-cartn-transform-mat-11) | <code>_atom_sites_Cartn_transform.mat_11</code><details><summary>Accepted aliases</summary><code>_atom_sites_Cartn_tran_matrix_11</code><br><code>_atom_sites.Cartn_transf_matrix[1][1]</code></details> |
    | [Coordinate-transform element 12](../physics/parameters.md#atom-sites-cartn-transform-mat-12) | <code>_atom_sites_Cartn_transform.mat_12</code><details><summary>Accepted aliases</summary><code>_atom_sites_Cartn_tran_matrix_12</code><br><code>_atom_sites.Cartn_transf_matrix[1][2]</code></details> |
    | [Coordinate-transform element 13](../physics/parameters.md#atom-sites-cartn-transform-mat-13) | <code>_atom_sites_Cartn_transform.mat_13</code><details><summary>Accepted aliases</summary><code>_atom_sites_Cartn_tran_matrix_13</code><br><code>_atom_sites.Cartn_transf_matrix[1][3]</code></details> |
    | [Coordinate-transform element 21](../physics/parameters.md#atom-sites-cartn-transform-mat-21) | <code>_atom_sites_Cartn_transform.mat_21</code><details><summary>Accepted aliases</summary><code>_atom_sites_Cartn_tran_matrix_21</code><br><code>_atom_sites.Cartn_transf_matrix[2][1]</code></details> |
    | [Coordinate-transform element 22](../physics/parameters.md#atom-sites-cartn-transform-mat-22) | <code>_atom_sites_Cartn_transform.mat_22</code><details><summary>Accepted aliases</summary><code>_atom_sites_Cartn_tran_matrix_22</code><br><code>_atom_sites.Cartn_transf_matrix[2][2]</code></details> |
    | [Coordinate-transform element 23](../physics/parameters.md#atom-sites-cartn-transform-mat-23) | <code>_atom_sites_Cartn_transform.mat_23</code><details><summary>Accepted aliases</summary><code>_atom_sites_Cartn_tran_matrix_23</code><br><code>_atom_sites.Cartn_transf_matrix[2][3]</code></details> |
    | [Coordinate-transform element 31](../physics/parameters.md#atom-sites-cartn-transform-mat-31) | <code>_atom_sites_Cartn_transform.mat_31</code><details><summary>Accepted aliases</summary><code>_atom_sites_Cartn_tran_matrix_31</code><br><code>_atom_sites.Cartn_transf_matrix[3][1]</code></details> |
    | [Coordinate-transform element 32](../physics/parameters.md#atom-sites-cartn-transform-mat-32) | <code>_atom_sites_Cartn_transform.mat_32</code><details><summary>Accepted aliases</summary><code>_atom_sites_Cartn_tran_matrix_32</code><br><code>_atom_sites.Cartn_transf_matrix[3][2]</code></details> |
    | [Coordinate-transform element 33](../physics/parameters.md#atom-sites-cartn-transform-mat-33) | <code>_atom_sites_Cartn_transform.mat_33</code><details><summary>Accepted aliases</summary><code>_atom_sites_Cartn_tran_matrix_33</code><br><code>_atom_sites.Cartn_transf_matrix[3][3]</code></details> |
    | [Axes](../physics/parameters.md#atom-sites-cartn-transform-axes) | <code>_atom_sites_Cartn_transform.axes</code><details><summary>Accepted aliases</summary><code>_atom_sites_Cartn_transform_axes</code><br><code>_atom_sites.Cartn_transform_axes</code></details> |

## Experiment parameters

=== "GUI"

    <span class="ed-reference-anchor" id="names-experiment-type">**[<span class="ed-reference-icon" data-reference-category="experiment-type" aria-hidden="true">&#63417;</span> Experiment type](../physics/parameters.md#experiment-type)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Beam mode](../physics/parameters.md#experiment-type-beam-mode) | beam mode |
    | [Sample form](../physics/parameters.md#experiment-type-sample-form) | sample form |
    | [Probe](../physics/parameters.md#experiment-type-radiation-probe) | probe |
    | [Scattering type](../physics/parameters.md#experiment-type-scattering-type) | scattering type |
    | [Dimensionality](../physics/parameters.md#experiment-type-dimensionality) | dimensionality |
    | [Polarisation](../physics/parameters.md#experiment-type-polarisation) | polarisation |

    <span class="ed-reference-anchor" id="names-data-range">**[<span class="ed-reference-icon" data-reference-category="data-range" aria-hidden="true">&#62263;</span> Calculation range](../physics/parameters.md#data-range)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Min](../physics/parameters.md#data-range-two-theta-min) | min |
    | [Max](../physics/parameters.md#data-range-two-theta-max) | max |
    | [Step](../physics/parameters.md#data-range-two-theta-step) | step |
    | [Scattering angle](../physics/parameters.md#data-range-two-theta) | 2θ |
    | [Min](../physics/parameters.md#data-range-time-of-flight-min) | min |
    | [Max](../physics/parameters.md#data-range-time-of-flight-max) | max |
    | [Step](../physics/parameters.md#data-range-time-of-flight-step) | step |
    | [Time of flight](../physics/parameters.md#data-range-time-of-flight) | TOF |

    <span class="ed-reference-anchor" id="names-background">**[<span class="ed-reference-icon" data-reference-category="background" aria-hidden="true">&#63550;</span> Background](../physics/parameters.md#background)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Background anchor intensity](../physics/parameters.md#background-intensity) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63550;</span> <span class="ed-reference-icon" aria-hidden="true">&#63228;</span> </span><span class="ed-icon-text">intensity</span></span> |
    | [Background anchor position](../physics/parameters.md#background-position) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63550;</span> </span><span class="ed-icon-text">position</span></span> |
    | [Background coefficient](../physics/parameters.md#background-coef) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63550;</span> </span><span class="ed-icon-text">coefficient</span></span> |
    | [Background term order](../physics/parameters.md#background-order) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63550;</span> </span><span class="ed-icon-text">order</span></span> |
    | [Polynomial background origin](../physics/parameters.md#background-origin) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63550;</span> </span><span class="ed-icon-text">origin</span></span> |
    | [Chebyshev domain minimum](../physics/parameters.md#background-x-min) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63550;</span> </span><span class="ed-icon-text">x min</span></span> |
    | [Chebyshev domain maximum](../physics/parameters.md#background-x-max) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63550;</span> </span><span class="ed-icon-text">x max</span></span> |
    | [Background model](../physics/parameters.md#background-type) | type |
    | [Background row identifier](../physics/parameters.md#background-id) | id |

    <span class="ed-reference-anchor" id="names-background-estimate">**[<span class="ed-reference-icon" data-reference-category="background-estimate" aria-hidden="true">&#61648;</span> Background estimation](../physics/parameters.md#background-estimate)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Estimation mode](../physics/parameters.md#background-estimate-mode) | estimation mode |
    | [Method](../physics/parameters.md#background-estimate-method) | method |
    | [Peak width](../physics/parameters.md#background-estimate-width) | peak width |
    | [Smoothness](../physics/parameters.md#background-estimate-smoothness) | smoothness |
    | [Number of background anchors](../physics/parameters.md#background-estimate-n-points) | points |
    | [Background thinning tolerance](../physics/parameters.md#background-estimate-tolerance) | tolerance |
    | [Anchors within peaks](../physics/parameters.md#background-estimate-in-peaks) | points in peaks |
    | [Calculated-peak treatment](../physics/parameters.md#background-estimate-use-model) | calculated peaks |
    | [Max terms](../physics/parameters.md#background-estimate-max-terms) | max terms |
    | [Inputs digest](../physics/parameters.md#background-estimate-inputs-digest) | inputs digest |
    | [Points digest](../physics/parameters.md#background-estimate-points-digest) | points digest |

    <span class="ed-reference-anchor" id="names-instrument">**[<span class="ed-reference-icon" data-reference-category="instrument" aria-hidden="true">&#62992;</span> Instrument](../physics/parameters.md#instrument)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [TOF offset](../physics/parameters.md#instrument-calib-d-to-tof-offset) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62263;</span> </span><span class="ed-icon-text">TOF offset</span></span> |
    | [TOF linear](../physics/parameters.md#instrument-calib-d-to-tof-linear) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63417;</span> </span><span class="ed-icon-text">TOF linear</span></span> |
    | [TOF quadratic](../physics/parameters.md#instrument-calib-d-to-tof-quadratic) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63417;</span> </span><span class="ed-icon-text">TOF quadratic</span></span> |
    | [TOF reciprocal](../physics/parameters.md#instrument-calib-d-to-tof-reciprocal) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63417;</span> </span><span class="ed-icon-text">TOF reciprocal</span></span> |
    | [Zero-point angular offset](../physics/parameters.md#instrument-calib-twotheta-offset) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62263;</span> </span><span class="ed-icon-text">2θ offset</span></span> |
    | [Wavelength](../physics/parameters.md#instrument-setup-wavelength) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63417;</span> </span><span class="ed-icon-text">Wavelength</span></span> |
    | [Sample displacement](../physics/parameters.md#instrument-calib-sample-displacement) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62263;</span> </span><span class="ed-icon-text">Sample displacement</span></span> |
    | [Sample transparency](../physics/parameters.md#instrument-calib-sample-transparency) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62263;</span> </span><span class="ed-icon-text">Sample transparency</span></span> |
    | [Polarization coefficient](../physics/parameters.md#instrument-setup-polarization-coefficient) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> </span><span class="ed-icon-text">Polarization coefficient</span></span> |
    | [Monochromator 2θ](../physics/parameters.md#instrument-setup-monochromator-twotheta) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> </span><span class="ed-icon-text">Monochromator 2θ</span></span> |
    | [Secondary wavelength](../physics/parameters.md#instrument-setup-wavelength-2) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63417;</span> </span><span class="ed-icon-text">Wavelength 2</span></span> |
    | [Secondary-to-primary intensity ratio](../physics/parameters.md#instrument-setup-wavelength-2-to-1-ratio) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63417;</span> </span><span class="ed-icon-text">Intensity ratio 2/1</span></span> |
    | [Instrument](../physics/parameters.md#instrument-name) | instrument |
    | [Facility](../physics/parameters.md#instrument-facility) | facility |
    | [2θ bank](../physics/parameters.md#instrument-setup-twotheta-bank) | 2θ bank |

    <span class="ed-reference-anchor" id="names-peak">**[<span class="ed-reference-icon" data-reference-category="peak" aria-hidden="true">&#63007;</span> Peak profile](../physics/parameters.md#peak)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Exponential rise coefficient α₀](../physics/parameters.md#peak-rise-alpha-0) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">α₀</span></span> |
    | [Exponential rise coefficient α₁](../physics/parameters.md#peak-rise-alpha-1) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">α₁</span></span> |
    | [Exponential decay coefficient β₀](../physics/parameters.md#peak-decay-beta-0) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">β₀</span></span> |
    | [Exponential decay coefficient β₁](../physics/parameters.md#peak-decay-beta-1) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">β₁</span></span> |
    | [Gaussian broadening σ₀²](../physics/parameters.md#peak-broad-gauss-sigma-0) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">σ₀²</span></span> |
    | [Gaussian broadening σ₁²](../physics/parameters.md#peak-broad-gauss-sigma-1) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">σ₁²</span></span> |
    | [Gaussian broadening σ₂²](../physics/parameters.md#peak-broad-gauss-sigma-2) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">σ₂²</span></span> |
    | [Gaussian broadening size G](../physics/parameters.md#peak-broad-gauss-size) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">size G</span></span> |
    | [Gaussian broadening strain G](../physics/parameters.md#peak-broad-gauss-strain) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">strain G</span></span> |
    | [Lorentzian broadening γ₀](../physics/parameters.md#peak-broad-lorentz-gamma-0) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">γ₀</span></span> |
    | [Lorentzian broadening γ₁](../physics/parameters.md#peak-broad-lorentz-gamma-1) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">γ₁</span></span> |
    | [Lorentzian broadening γ₂](../physics/parameters.md#peak-broad-lorentz-gamma-2) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">γ₂</span></span> |
    | [Lorentzian broadening size L](../physics/parameters.md#peak-broad-lorentz-size) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">size L</span></span> |
    | [Lorentzian broadening strain L](../physics/parameters.md#peak-broad-lorentz-strain) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">strain L</span></span> |
    | [Gaussian broadening U](../physics/parameters.md#peak-broad-gauss-u) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">U</span></span> |
    | [Gaussian broadening V](../physics/parameters.md#peak-broad-gauss-v) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">V</span></span> |
    | [Gaussian broadening W](../physics/parameters.md#peak-broad-gauss-w) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">W</span></span> |
    | [Lorentzian broadening X](../physics/parameters.md#peak-broad-lorentz-x) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">X</span></span> |
    | [Lorentzian broadening Y](../physics/parameters.md#peak-broad-lorentz-y) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">Y</span></span> |
    | [Pseudo-Voigt mixing intercept](../physics/parameters.md#peak-mixing-eta-0) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">Eta0</span></span> |
    | [Pseudo-Voigt mixing slope](../physics/parameters.md#peak-mixing-eta-1) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> </span><span class="ed-icon-text">Eta1</span></span> |
    | [FCJ asymmetry S/L](../physics/parameters.md#peak-asym-fcj-1) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#62741;</span> </span><span class="ed-icon-text">S/L</span></span> |
    | [FCJ asymmetry D/L](../physics/parameters.md#peak-asym-fcj-2) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#62741;</span> </span><span class="ed-icon-text">D/L</span></span> |
    | [Bérar-Baldinozzi asymmetry A₀](../physics/parameters.md#peak-asym-beba-a0) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#62741;</span> </span><span class="ed-icon-text">A₀</span></span> |
    | [Bérar-Baldinozzi asymmetry B₀](../physics/parameters.md#peak-asym-beba-b0) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#62741;</span> </span><span class="ed-icon-text">B₀</span></span> |
    | [Bérar-Baldinozzi asymmetry A₁](../physics/parameters.md#peak-asym-beba-a1) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#62741;</span> </span><span class="ed-icon-text">A₁</span></span> |
    | [Bérar-Baldinozzi asymmetry B₁](../physics/parameters.md#peak-asym-beba-b1) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#62741;</span> </span><span class="ed-icon-text">B₁</span></span> |
    | [Bérar-Baldinozzi asymmetry AsyLim](../physics/parameters.md#peak-asym-beba-limit) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#63007;</span> <span class="ed-reference-icon" aria-hidden="true">&#62741;</span> </span><span class="ed-icon-text">AsyLim</span></span> |
    | [Profile](../physics/parameters.md#peak-type) | profile |
    | [Peak calculation cutoff](../physics/parameters.md#peak-cutoff-fwhm) | cutoff (FWHM) |

    <span class="ed-reference-anchor" id="names-excluded-region">**[<span class="ed-reference-icon" data-reference-category="excluded-region" aria-hidden="true">&#61741;</span> Excluded region](../physics/parameters.md#excluded-region)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Id](../physics/parameters.md#excluded-region-id) | id |
    | [Start](../physics/parameters.md#excluded-region-start) | start |
    | [End](../physics/parameters.md#excluded-region-end) | end |

    <span class="ed-reference-anchor" id="names-extinction">**[<span class="ed-reference-icon" data-reference-category="extinction" aria-hidden="true">&#62373;</span> Extinction](../physics/parameters.md#extinction)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Domain radius](../physics/parameters.md#extinction-domain-radius) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62373;</span> </span><span class="ed-icon-text">Domain radius</span></span> |
    | [Mosaic spread](../physics/parameters.md#extinction-mosaic-spread) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62373;</span> </span><span class="ed-icon-text">Mosaic spread</span></span> |
    | [Crystal radius](../physics/parameters.md#extinction-crystal-radius) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62373;</span> </span><span class="ed-icon-text">Crystal radius</span></span> |
    | [Extinction coefficient](../physics/parameters.md#extinction-coefficient) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62373;</span> </span><span class="ed-icon-text">Extinction coefficient</span></span> |
    | [X11](../physics/parameters.md#extinction-coefficient-11) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62373;</span> </span><span class="ed-icon-text">x11</span></span> |
    | [X22](../physics/parameters.md#extinction-coefficient-22) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62373;</span> </span><span class="ed-icon-text">x22</span></span> |
    | [X33](../physics/parameters.md#extinction-coefficient-33) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62373;</span> </span><span class="ed-icon-text">x33</span></span> |
    | [X12](../physics/parameters.md#extinction-coefficient-12) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62373;</span> </span><span class="ed-icon-text">x12</span></span> |
    | [X13](../physics/parameters.md#extinction-coefficient-13) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62373;</span> </span><span class="ed-icon-text">x13</span></span> |
    | [X23](../physics/parameters.md#extinction-coefficient-23) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62373;</span> </span><span class="ed-icon-text">x23</span></span> |
    | [Type](../physics/parameters.md#extinction-type) | type |
    | [Mosaic distribution](../physics/parameters.md#extinction-mosaic-distribution) | mosaic distribution |

    <span class="ed-reference-anchor" id="names-linked-structure">**[<span class="ed-reference-icon" data-reference-category="linked-structure" aria-hidden="true">&#62973;</span> Linked structure](../physics/parameters.md#linked-structure)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Scale](../physics/parameters.md#linked-structure-scale) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#62973;</span> <span class="ed-reference-icon" aria-hidden="true">&#62614;</span> </span><span class="ed-icon-text">scale</span></span> |
    | [Structure](../physics/parameters.md#linked-structure-structure-id) | structure |
    | [Enabled](../physics/parameters.md#linked-structure-enabled) | enabled |
    | [Phase mass fraction](../physics/parameters.md#linked-structure-weight-fraction) | weight fraction |

    <span class="ed-reference-anchor" id="names-absorption">**[<span class="ed-reference-icon" data-reference-category="absorption" aria-hidden="true">&#61507;</span> Absorption](../physics/parameters.md#absorption)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [ABSCOR1](../physics/parameters.md#absorption-abscor1) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#61507;</span> </span><span class="ed-icon-text">ABSCOR1</span></span> |
    | [ABSCOR2](../physics/parameters.md#absorption-abscor2) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#61507;</span> </span><span class="ed-icon-text">ABSCOR2</span></span> |
    | [ΜR](../physics/parameters.md#absorption-mu-r) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#61507;</span> </span><span class="ed-icon-text">μR</span></span> |
    | [Type](../physics/parameters.md#absorption-type) | type |

    <span class="ed-reference-anchor" id="names-preferred-orientation">**[<span class="ed-reference-icon" data-reference-category="preferred-orientation" aria-hidden="true">&#61774;</span> Preferred orientation](../physics/parameters.md#preferred-orientation)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [March-Dollase coefficient](../physics/parameters.md#preferred-orientation-march-r) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#61774;</span> </span><span class="ed-icon-text">r</span></span> |
    | [Randomly oriented fraction](../physics/parameters.md#preferred-orientation-march-random-fract) | <span class="ed-icon-label"><span class="ed-icon-group" aria-hidden="true"><span class="ed-reference-icon" aria-hidden="true">&#62992;</span> <span class="ed-reference-icon" aria-hidden="true">&#61774;</span> </span><span class="ed-icon-text">f rand</span></span> |
    | [Structure](../physics/parameters.md#preferred-orientation-structure-id) | structure |
    | [Miller index h](../physics/parameters.md#preferred-orientation-index-h) | h |
    | [Miller index k](../physics/parameters.md#preferred-orientation-index-k) | k |
    | [Miller index l](../physics/parameters.md#preferred-orientation-index-l) | l |

    <span class="ed-reference-anchor" id="names-reflns">**[<span class="ed-reference-icon" data-reference-category="reflns" aria-hidden="true">&#61616;</span> Observed reflections](../physics/parameters.md#reflns)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Observed-reflection threshold](../physics/parameters.md#reflns-threshold-sigma) | observed above (su) |
    | [On](../physics/parameters.md#reflns-threshold-basis) | on |
    | [Threshold](../physics/parameters.md#reflns-threshold-expression) | threshold |

    <span class="ed-reference-anchor" id="names-scattering-source">**[<span class="ed-reference-icon" data-reference-category="scattering-source" aria-hidden="true">&#62930;</span> Scattering source](../physics/parameters.md#scattering-source)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [X-ray form factors](../physics/parameters.md#scattering-source-xray-form-factor) | X-ray form factors |
    | [X-ray dispersion](../physics/parameters.md#scattering-source-xray-dispersion) | X-ray dispersion |
    | [Neutron scattering lengths](../physics/parameters.md#scattering-source-neutron-scattering-length) | neutron scattering lengths |

    <span class="ed-reference-anchor" id="names-data-source">**[<span class="ed-reference-icon" data-reference-category="data-source" aria-hidden="true">&#62831;</span> Data source](../physics/parameters.md#data-source)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Measured-data filename](../physics/parameters.md#data-source-file-name) | data file |

    <span class="ed-reference-anchor" id="names-data">**[<span class="ed-reference-icon" data-reference-category="data" aria-hidden="true">&#62263;</span> Measured data point](../physics/parameters.md#data)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Scattering angle](../physics/parameters.md#data-two-theta) | 2θ |
    | [Time of flight](../physics/parameters.md#data-time-of-flight) | TOF |
    | [Measured intensity](../physics/parameters.md#data-intensity-meas) | meas |
    | [Measured intensity uncertainty](../physics/parameters.md#data-intensity-meas-su) | s.u. |
    | [Interplanar spacing](../physics/parameters.md#data-d-spacing) | d |
    | [Calculated intensity](../physics/parameters.md#data-intensity-calc) | calc |
    | [Background intensity](../physics/parameters.md#data-intensity-bkg) | bkg |
    | [Calculation status](../physics/parameters.md#data-calc-status) | status |

    <span class="ed-reference-anchor" id="names-data-calc">**[<span class="ed-reference-icon" data-reference-category="data-calc" aria-hidden="true">&#61950;</span> Calculated point](../physics/parameters.md#data-calc)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Point](../physics/parameters.md#data-calc-point-id) | point |

    <span class="ed-reference-anchor" id="names-pd-calc-overall">**[<span class="ed-reference-icon" data-reference-category="pd-calc-overall" aria-hidden="true">&#61950;</span> Structure curves](../physics/parameters.md#pd-calc-overall)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Structure order](../physics/parameters.md#pd-calc-overall-component-presentation-order) | structure order |

    <span class="ed-reference-anchor" id="names-pd-calc">**[<span class="ed-reference-icon" data-reference-category="pd-calc" aria-hidden="true">&#61950;</span> Structure curve](../physics/parameters.md#pd-calc)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Structure calc](../physics/parameters.md#pd-calc-component-intensities-net) | structure calc |

    <span class="ed-reference-anchor" id="names-refln">**[<span class="ed-reference-icon" data-reference-category="refln" aria-hidden="true">&#61498;</span> Reflection](../physics/parameters.md#refln)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Structure](../physics/parameters.md#refln-structure-id) | structure |
    | [Interplanar spacing](../physics/parameters.md#refln-d-spacing) | d |
    | [Sin θ/λ](../physics/parameters.md#refln-sin-theta-over-lambda) | sin θ/λ |
    | [Miller index h](../physics/parameters.md#refln-index-h) | h |
    | [Miller index k](../physics/parameters.md#refln-index-k) | k |
    | [Miller index l](../physics/parameters.md#refln-index-l) | l |
    | [F calc](../physics/parameters.md#refln-f-calc) | F calc |
    | [F meas](../physics/parameters.md#refln-f-meas) | F meas |
    | [F² calc](../physics/parameters.md#refln-f-squared-calc) | F² calc |
    | [Measured intensity](../physics/parameters.md#refln-intensity-meas) | F² meas |
    | [Measured intensity uncertainty](../physics/parameters.md#refln-intensity-meas-su) | s.u. |
    | [Calculated intensity](../physics/parameters.md#refln-intensity-calc) | F² calc |
    | [Λ](../physics/parameters.md#refln-wavelength) | λ |
    | [Scattering angle](../physics/parameters.md#refln-two-theta) | 2θ |
    | [Time of flight](../physics/parameters.md#refln-time-of-flight) | TOF |

=== "Edi"

    **[<span class="ed-reference-icon" data-reference-category="experiment-type" aria-hidden="true">&#63417;</span> Experiment type](../physics/parameters.md#experiment-type)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Beam mode](../physics/parameters.md#experiment-type-beam-mode) | <code>_experiment_type.beam_mode</code> |
    | [Sample form](../physics/parameters.md#experiment-type-sample-form) | <code>_experiment_type.sample_form</code> |
    | [Probe](../physics/parameters.md#experiment-type-radiation-probe) | <code>_experiment_type.radiation_probe</code> |
    | [Scattering type](../physics/parameters.md#experiment-type-scattering-type) | <code>_experiment_type.scattering_type</code> |
    | [Dimensionality](../physics/parameters.md#experiment-type-dimensionality) | <code>_experiment_type.dimensionality</code> |
    | [Polarisation](../physics/parameters.md#experiment-type-polarisation) | <code>_experiment_type.polarisation</code> |

    **[<span class="ed-reference-icon" data-reference-category="data-range" aria-hidden="true">&#62263;</span> Calculation range](../physics/parameters.md#data-range)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Min](../physics/parameters.md#data-range-two-theta-min) | <code>_data_range.two_theta_min</code> |
    | [Max](../physics/parameters.md#data-range-two-theta-max) | <code>_data_range.two_theta_max</code> |
    | [Step](../physics/parameters.md#data-range-two-theta-step) | <code>_data_range.two_theta_step</code> |
    | [Scattering angle](../physics/parameters.md#data-range-two-theta) | <code>_data_range.two_theta</code> |
    | [Min](../physics/parameters.md#data-range-time-of-flight-min) | <code>_data_range.time_of_flight_min</code> |
    | [Max](../physics/parameters.md#data-range-time-of-flight-max) | <code>_data_range.time_of_flight_max</code> |
    | [Step](../physics/parameters.md#data-range-time-of-flight-step) | <code>_data_range.time_of_flight_step</code> |
    | [Time of flight](../physics/parameters.md#data-range-time-of-flight) | <code>_data_range.time_of_flight</code> |

    **[<span class="ed-reference-icon" data-reference-category="background" aria-hidden="true">&#63550;</span> Background](../physics/parameters.md#background)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Background anchor intensity](../physics/parameters.md#background-intensity) | <code>_background.intensity</code> |
    | [Background anchor position](../physics/parameters.md#background-position) | <code>_background.position</code> |
    | [Background coefficient](../physics/parameters.md#background-coef) | <code>_background.coef</code> |
    | [Background term order](../physics/parameters.md#background-order) | <code>_background.order</code> |
    | [Polynomial background origin](../physics/parameters.md#background-origin) | <code>_background.origin</code> |
    | [Chebyshev domain minimum](../physics/parameters.md#background-x-min) | <code>_background.x_min</code> |
    | [Chebyshev domain maximum](../physics/parameters.md#background-x-max) | <code>_background.x_max</code> |
    | [Background model](../physics/parameters.md#background-type) | <code>_background.type</code> |
    | [Background row identifier](../physics/parameters.md#background-id) | <code>_background.id</code> |

    **[<span class="ed-reference-icon" data-reference-category="background-estimate" aria-hidden="true">&#61648;</span> Background estimation](../physics/parameters.md#background-estimate)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Estimation mode](../physics/parameters.md#background-estimate-mode) | <code>_background_estimate.mode</code> |
    | [Method](../physics/parameters.md#background-estimate-method) | <code>_background_estimate.method</code> |
    | [Peak width](../physics/parameters.md#background-estimate-width) | <code>_background_estimate.width</code> |
    | [Smoothness](../physics/parameters.md#background-estimate-smoothness) | <code>_background_estimate.smoothness</code> |
    | [Number of background anchors](../physics/parameters.md#background-estimate-n-points) | <code>_background_estimate.n_points</code> |
    | [Background thinning tolerance](../physics/parameters.md#background-estimate-tolerance) | <code>_background_estimate.tolerance</code> |
    | [Anchors within peaks](../physics/parameters.md#background-estimate-in-peaks) | <code>_background_estimate.in_peaks</code> |
    | [Calculated-peak treatment](../physics/parameters.md#background-estimate-use-model) | <code>_background_estimate.use_model</code> |
    | [Max terms](../physics/parameters.md#background-estimate-max-terms) | <code>_background_estimate.max_terms</code> |
    | [Inputs digest](../physics/parameters.md#background-estimate-inputs-digest) | <code>_background_estimate.inputs_digest</code> |
    | [Points digest](../physics/parameters.md#background-estimate-points-digest) | <code>_background_estimate.points_digest</code> |

    **[<span class="ed-reference-icon" data-reference-category="instrument" aria-hidden="true">&#62992;</span> Instrument](../physics/parameters.md#instrument)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [TOF offset](../physics/parameters.md#instrument-calib-d-to-tof-offset) | <code>_instrument.calib_d_to_tof_offset</code> |
    | [TOF linear](../physics/parameters.md#instrument-calib-d-to-tof-linear) | <code>_instrument.calib_d_to_tof_linear</code> |
    | [TOF quadratic](../physics/parameters.md#instrument-calib-d-to-tof-quadratic) | <code>_instrument.calib_d_to_tof_quadratic</code> |
    | [TOF reciprocal](../physics/parameters.md#instrument-calib-d-to-tof-reciprocal) | <code>_instrument.calib_d_to_tof_reciprocal</code> |
    | [Zero-point angular offset](../physics/parameters.md#instrument-calib-twotheta-offset) | <code>_instrument.calib_twotheta_offset</code> |
    | [Wavelength](../physics/parameters.md#instrument-setup-wavelength) | <code>_instrument.setup_wavelength</code> |
    | [Sample displacement](../physics/parameters.md#instrument-calib-sample-displacement) | <code>_instrument.calib_sample_displacement</code> |
    | [Sample transparency](../physics/parameters.md#instrument-calib-sample-transparency) | <code>_instrument.calib_sample_transparency</code> |
    | [Polarization coefficient](../physics/parameters.md#instrument-setup-polarization-coefficient) | <code>_instrument.setup_polarization_coefficient</code> |
    | [Monochromator 2θ](../physics/parameters.md#instrument-setup-monochromator-twotheta) | <code>_instrument.setup_monochromator_twotheta</code> |
    | [Secondary wavelength](../physics/parameters.md#instrument-setup-wavelength-2) | <code>_instrument.setup_wavelength_2</code> |
    | [Secondary-to-primary intensity ratio](../physics/parameters.md#instrument-setup-wavelength-2-to-1-ratio) | <code>_instrument.setup_wavelength_2_to_1_ratio</code> |
    | [Instrument](../physics/parameters.md#instrument-name) | <code>_instrument.name</code> |
    | [Facility](../physics/parameters.md#instrument-facility) | <code>_instrument.facility</code> |
    | [2θ bank](../physics/parameters.md#instrument-setup-twotheta-bank) | <code>_instrument.setup_twotheta_bank</code> |

    **[<span class="ed-reference-icon" data-reference-category="peak" aria-hidden="true">&#63007;</span> Peak profile](../physics/parameters.md#peak)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Exponential rise coefficient α₀](../physics/parameters.md#peak-rise-alpha-0) | <code>_peak.rise_alpha_0</code> |
    | [Exponential rise coefficient α₁](../physics/parameters.md#peak-rise-alpha-1) | <code>_peak.rise_alpha_1</code> |
    | [Exponential decay coefficient β₀](../physics/parameters.md#peak-decay-beta-0) | <code>_peak.decay_beta_0</code> |
    | [Exponential decay coefficient β₁](../physics/parameters.md#peak-decay-beta-1) | <code>_peak.decay_beta_1</code> |
    | [Gaussian broadening σ₀²](../physics/parameters.md#peak-broad-gauss-sigma-0) | <code>_peak.broad_gauss_sigma_0</code> |
    | [Gaussian broadening σ₁²](../physics/parameters.md#peak-broad-gauss-sigma-1) | <code>_peak.broad_gauss_sigma_1</code> |
    | [Gaussian broadening σ₂²](../physics/parameters.md#peak-broad-gauss-sigma-2) | <code>_peak.broad_gauss_sigma_2</code> |
    | [Gaussian broadening size G](../physics/parameters.md#peak-broad-gauss-size) | <code>_peak.broad_gauss_size</code> |
    | [Gaussian broadening strain G](../physics/parameters.md#peak-broad-gauss-strain) | <code>_peak.broad_gauss_strain</code> |
    | [Lorentzian broadening γ₀](../physics/parameters.md#peak-broad-lorentz-gamma-0) | <code>_peak.broad_lorentz_gamma_0</code> |
    | [Lorentzian broadening γ₁](../physics/parameters.md#peak-broad-lorentz-gamma-1) | <code>_peak.broad_lorentz_gamma_1</code> |
    | [Lorentzian broadening γ₂](../physics/parameters.md#peak-broad-lorentz-gamma-2) | <code>_peak.broad_lorentz_gamma_2</code> |
    | [Lorentzian broadening size L](../physics/parameters.md#peak-broad-lorentz-size) | <code>_peak.broad_lorentz_size</code> |
    | [Lorentzian broadening strain L](../physics/parameters.md#peak-broad-lorentz-strain) | <code>_peak.broad_lorentz_strain</code> |
    | [Gaussian broadening U](../physics/parameters.md#peak-broad-gauss-u) | <code>_peak.broad_gauss_u</code> |
    | [Gaussian broadening V](../physics/parameters.md#peak-broad-gauss-v) | <code>_peak.broad_gauss_v</code> |
    | [Gaussian broadening W](../physics/parameters.md#peak-broad-gauss-w) | <code>_peak.broad_gauss_w</code> |
    | [Lorentzian broadening X](../physics/parameters.md#peak-broad-lorentz-x) | <code>_peak.broad_lorentz_x</code> |
    | [Lorentzian broadening Y](../physics/parameters.md#peak-broad-lorentz-y) | <code>_peak.broad_lorentz_y</code> |
    | [Pseudo-Voigt mixing intercept](../physics/parameters.md#peak-mixing-eta-0) | <code>_peak.mixing_eta_0</code> |
    | [Pseudo-Voigt mixing slope](../physics/parameters.md#peak-mixing-eta-1) | <code>_peak.mixing_eta_1</code> |
    | [FCJ asymmetry S/L](../physics/parameters.md#peak-asym-fcj-1) | <code>_peak.asym_fcj_1</code> |
    | [FCJ asymmetry D/L](../physics/parameters.md#peak-asym-fcj-2) | <code>_peak.asym_fcj_2</code> |
    | [Bérar-Baldinozzi asymmetry A₀](../physics/parameters.md#peak-asym-beba-a0) | <code>_peak.asym_beba_a0</code> |
    | [Bérar-Baldinozzi asymmetry B₀](../physics/parameters.md#peak-asym-beba-b0) | <code>_peak.asym_beba_b0</code> |
    | [Bérar-Baldinozzi asymmetry A₁](../physics/parameters.md#peak-asym-beba-a1) | <code>_peak.asym_beba_a1</code> |
    | [Bérar-Baldinozzi asymmetry B₁](../physics/parameters.md#peak-asym-beba-b1) | <code>_peak.asym_beba_b1</code> |
    | [Bérar-Baldinozzi asymmetry AsyLim](../physics/parameters.md#peak-asym-beba-limit) | <code>_peak.asym_beba_limit</code> |
    | [Profile](../physics/parameters.md#peak-type) | <code>_peak.type</code> |
    | [Peak calculation cutoff](../physics/parameters.md#peak-cutoff-fwhm) | <code>_peak.cutoff_fwhm</code> |

    **[<span class="ed-reference-icon" data-reference-category="excluded-region" aria-hidden="true">&#61741;</span> Excluded region](../physics/parameters.md#excluded-region)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Id](../physics/parameters.md#excluded-region-id) | <code>_excluded_region.id</code> |
    | [Start](../physics/parameters.md#excluded-region-start) | <code>_excluded_region.start</code> |
    | [End](../physics/parameters.md#excluded-region-end) | <code>_excluded_region.end</code> |

    **[<span class="ed-reference-icon" data-reference-category="extinction" aria-hidden="true">&#62373;</span> Extinction](../physics/parameters.md#extinction)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Domain radius](../physics/parameters.md#extinction-domain-radius) | <code>_extinction.domain_radius</code> |
    | [Mosaic spread](../physics/parameters.md#extinction-mosaic-spread) | <code>_extinction.mosaic_spread</code> |
    | [Crystal radius](../physics/parameters.md#extinction-crystal-radius) | <code>_extinction.crystal_radius</code> |
    | [Extinction coefficient](../physics/parameters.md#extinction-coefficient) | <code>_extinction.coefficient</code> |
    | [X11](../physics/parameters.md#extinction-coefficient-11) | <code>_extinction.coefficient_11</code> |
    | [X22](../physics/parameters.md#extinction-coefficient-22) | <code>_extinction.coefficient_22</code> |
    | [X33](../physics/parameters.md#extinction-coefficient-33) | <code>_extinction.coefficient_33</code> |
    | [X12](../physics/parameters.md#extinction-coefficient-12) | <code>_extinction.coefficient_12</code> |
    | [X13](../physics/parameters.md#extinction-coefficient-13) | <code>_extinction.coefficient_13</code> |
    | [X23](../physics/parameters.md#extinction-coefficient-23) | <code>_extinction.coefficient_23</code> |
    | [Type](../physics/parameters.md#extinction-type) | <code>_extinction.type</code> |
    | [Mosaic distribution](../physics/parameters.md#extinction-mosaic-distribution) | <code>_extinction.mosaic_distribution</code> |

    **[<span class="ed-reference-icon" data-reference-category="linked-structure" aria-hidden="true">&#62973;</span> Linked structure](../physics/parameters.md#linked-structure)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Scale](../physics/parameters.md#linked-structure-scale) | <code>_linked_structure.scale</code><br><small>Also accepted: <code>_scale.value</code></small> |
    | [Structure](../physics/parameters.md#linked-structure-structure-id) | <code>_linked_structure.structure_id</code> |
    | [Enabled](../physics/parameters.md#linked-structure-enabled) | <code>_linked_structure.enabled</code> |
    | [Phase mass fraction](../physics/parameters.md#linked-structure-weight-fraction) | <code>_linked_structure.weight_fraction</code> |

    **[<span class="ed-reference-icon" data-reference-category="absorption" aria-hidden="true">&#61507;</span> Absorption](../physics/parameters.md#absorption)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [ABSCOR1](../physics/parameters.md#absorption-abscor1) | <code>_absorption.abscor1</code> |
    | [ABSCOR2](../physics/parameters.md#absorption-abscor2) | <code>_absorption.abscor2</code> |
    | [ΜR](../physics/parameters.md#absorption-mu-r) | <code>_absorption.mu_r</code> |
    | [Type](../physics/parameters.md#absorption-type) | <code>_absorption.type</code> |

    **[<span class="ed-reference-icon" data-reference-category="preferred-orientation" aria-hidden="true">&#61774;</span> Preferred orientation](../physics/parameters.md#preferred-orientation)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [March-Dollase coefficient](../physics/parameters.md#preferred-orientation-march-r) | <code>_preferred_orientation.march_r</code> |
    | [Randomly oriented fraction](../physics/parameters.md#preferred-orientation-march-random-fract) | <code>_preferred_orientation.march_random_fract</code> |
    | [Structure](../physics/parameters.md#preferred-orientation-structure-id) | <code>_preferred_orientation.structure_id</code> |
    | [Miller index h](../physics/parameters.md#preferred-orientation-index-h) | <code>_preferred_orientation.index_h</code> |
    | [Miller index k](../physics/parameters.md#preferred-orientation-index-k) | <code>_preferred_orientation.index_k</code> |
    | [Miller index l](../physics/parameters.md#preferred-orientation-index-l) | <code>_preferred_orientation.index_l</code> |

    **[<span class="ed-reference-icon" data-reference-category="reflns" aria-hidden="true">&#61616;</span> Observed reflections](../physics/parameters.md#reflns)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Observed-reflection threshold](../physics/parameters.md#reflns-threshold-sigma) | <code>_reflns.threshold_sigma</code> |
    | [On](../physics/parameters.md#reflns-threshold-basis) | <code>_reflns.threshold_basis</code> |
    | [Threshold](../physics/parameters.md#reflns-threshold-expression) | <code>_reflns.threshold_expression</code> |

    **[<span class="ed-reference-icon" data-reference-category="scattering-source" aria-hidden="true">&#62930;</span> Scattering source](../physics/parameters.md#scattering-source)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [X-ray form factors](../physics/parameters.md#scattering-source-xray-form-factor) | <code>_scattering_source.xray_form_factor</code> |
    | [X-ray dispersion](../physics/parameters.md#scattering-source-xray-dispersion) | <code>_scattering_source.xray_dispersion</code> |
    | [Neutron scattering lengths](../physics/parameters.md#scattering-source-neutron-scattering-length) | <code>_scattering_source.neutron_scattering_length</code> |

    **[<span class="ed-reference-icon" data-reference-category="data-source" aria-hidden="true">&#62831;</span> Data source](../physics/parameters.md#data-source)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Measured-data filename](../physics/parameters.md#data-source-file-name) | <code>_data_source.file_name</code> |

    **[<span class="ed-reference-icon" data-reference-category="data" aria-hidden="true">&#62263;</span> Measured data point](../physics/parameters.md#data)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Scattering angle](../physics/parameters.md#data-two-theta) | <code>_data.two_theta</code> |
    | [Time of flight](../physics/parameters.md#data-time-of-flight) | <code>_data.time_of_flight</code> |
    | [Measured intensity](../physics/parameters.md#data-intensity-meas) | <code>_data.intensity_meas</code> |
    | [Measured intensity uncertainty](../physics/parameters.md#data-intensity-meas-su) | <code>_data.intensity_meas_su</code> |
    | [Interplanar spacing](../physics/parameters.md#data-d-spacing) | <code>_data.d_spacing</code> |
    | [Calculated intensity](../physics/parameters.md#data-intensity-calc) | <code>_data.intensity_calc</code> |
    | [Background intensity](../physics/parameters.md#data-intensity-bkg) | <code>_data.intensity_bkg</code> |
    | [Calculation status](../physics/parameters.md#data-calc-status) | <code>_data.calc_status</code> |

    **[<span class="ed-reference-icon" data-reference-category="data-calc" aria-hidden="true">&#61950;</span> Calculated point](../physics/parameters.md#data-calc)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Point](../physics/parameters.md#data-calc-point-id) | <code>_data_calc.point_id</code> |

    **[<span class="ed-reference-icon" data-reference-category="pd-calc-overall" aria-hidden="true">&#61950;</span> Structure curves](../physics/parameters.md#pd-calc-overall)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Structure order](../physics/parameters.md#pd-calc-overall-component-presentation-order) | <code>_pd_calc_overall.component_presentation_order</code> |

    **[<span class="ed-reference-icon" data-reference-category="pd-calc" aria-hidden="true">&#61950;</span> Structure curve](../physics/parameters.md#pd-calc)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Structure calc](../physics/parameters.md#pd-calc-component-intensities-net) | <code>_pd_calc.component_intensities_net</code> |

    **[<span class="ed-reference-icon" data-reference-category="refln" aria-hidden="true">&#61498;</span> Reflection](../physics/parameters.md#refln)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Structure](../physics/parameters.md#refln-structure-id) | <code>_refln.structure_id</code> |
    | [Interplanar spacing](../physics/parameters.md#refln-d-spacing) | <code>_refln.d_spacing</code> |
    | [Sin θ/λ](../physics/parameters.md#refln-sin-theta-over-lambda) | <code>_refln.sin_theta_over_lambda</code> |
    | [Miller index h](../physics/parameters.md#refln-index-h) | <code>_refln.index_h</code> |
    | [Miller index k](../physics/parameters.md#refln-index-k) | <code>_refln.index_k</code> |
    | [Miller index l](../physics/parameters.md#refln-index-l) | <code>_refln.index_l</code> |
    | [F calc](../physics/parameters.md#refln-f-calc) | <code>_refln.f_calc</code> |
    | [F meas](../physics/parameters.md#refln-f-meas) | <code>_refln.f_meas</code> |
    | [F² calc](../physics/parameters.md#refln-f-squared-calc) | <code>_refln.f_squared_calc</code> |
    | [Measured intensity](../physics/parameters.md#refln-intensity-meas) | <code>_refln.intensity_meas</code> |
    | [Measured intensity uncertainty](../physics/parameters.md#refln-intensity-meas-su) | <code>_refln.intensity_meas_su</code> |
    | [Calculated intensity](../physics/parameters.md#refln-intensity-calc) | <code>_refln.intensity_calc</code> |
    | [Λ](../physics/parameters.md#refln-wavelength) | <code>_refln.wavelength</code> |
    | [Scattering angle](../physics/parameters.md#refln-two-theta) | <code>_refln.two_theta</code> |
    | [Time of flight](../physics/parameters.md#refln-time-of-flight) | <code>_refln.time_of_flight</code> |

=== "Python"

    **[<span class="ed-reference-icon" data-reference-category="experiment-type" aria-hidden="true">&#63417;</span> Experiment type](../physics/parameters.md#experiment-type)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Beam mode](../physics/parameters.md#experiment-type-beam-mode) | <code>project.experiments[0].experiment_type.beam_mode</code> |
    | [Sample form](../physics/parameters.md#experiment-type-sample-form) | <code>project.experiments[0].experiment_type.sample_form</code> |
    | [Probe](../physics/parameters.md#experiment-type-radiation-probe) | <code>project.experiments[0].experiment_type.radiation_probe</code> |
    | [Scattering type](../physics/parameters.md#experiment-type-scattering-type) | <code>project.experiments[0].experiment_type.scattering_type</code> |
    | [Dimensionality](../physics/parameters.md#experiment-type-dimensionality) | <code>project.experiments[0].experiment_type.dimensionality</code> |
    | [Polarisation](../physics/parameters.md#experiment-type-polarisation) | <code>project.experiments[0].experiment_type.polarisation</code> |

    **[<span class="ed-reference-icon" data-reference-category="data-range" aria-hidden="true">&#62263;</span> Calculation range](../physics/parameters.md#data-range)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Min](../physics/parameters.md#data-range-two-theta-min) | — |
    | [Max](../physics/parameters.md#data-range-two-theta-max) | — |
    | [Step](../physics/parameters.md#data-range-two-theta-step) | — |
    | [Scattering angle](../physics/parameters.md#data-range-two-theta) | — |
    | [Min](../physics/parameters.md#data-range-time-of-flight-min) | — |
    | [Max](../physics/parameters.md#data-range-time-of-flight-max) | — |
    | [Step](../physics/parameters.md#data-range-time-of-flight-step) | — |
    | [Time of flight](../physics/parameters.md#data-range-time-of-flight) | — |

    **[<span class="ed-reference-icon" data-reference-category="background" aria-hidden="true">&#63550;</span> Background](../physics/parameters.md#background)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Background anchor intensity](../physics/parameters.md#background-intensity) | <code>project.experiments[0].background[0].intensity</code> |
    | [Background anchor position](../physics/parameters.md#background-position) | <code>project.experiments[0].background[0].position</code> |
    | [Background coefficient](../physics/parameters.md#background-coef) | — |
    | [Background term order](../physics/parameters.md#background-order) | — |
    | [Polynomial background origin](../physics/parameters.md#background-origin) | <code>project.experiments[0].background_origin</code> |
    | [Chebyshev domain minimum](../physics/parameters.md#background-x-min) | <code>project.experiments[0].background_x_min</code> |
    | [Chebyshev domain maximum](../physics/parameters.md#background-x-max) | <code>project.experiments[0].background_x_max</code> |
    | [Background model](../physics/parameters.md#background-type) | <code>project.experiments[0].background_type</code> |
    | [Background row identifier](../physics/parameters.md#background-id) | <code>project.experiments[0].background[0].id</code> |

    **[<span class="ed-reference-icon" data-reference-category="background-estimate" aria-hidden="true">&#61648;</span> Background estimation](../physics/parameters.md#background-estimate)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Estimation mode](../physics/parameters.md#background-estimate-mode) | — |
    | [Method](../physics/parameters.md#background-estimate-method) | — |
    | [Peak width](../physics/parameters.md#background-estimate-width) | — |
    | [Smoothness](../physics/parameters.md#background-estimate-smoothness) | — |
    | [Number of background anchors](../physics/parameters.md#background-estimate-n-points) | — |
    | [Background thinning tolerance](../physics/parameters.md#background-estimate-tolerance) | — |
    | [Anchors within peaks](../physics/parameters.md#background-estimate-in-peaks) | — |
    | [Calculated-peak treatment](../physics/parameters.md#background-estimate-use-model) | — |
    | [Max terms](../physics/parameters.md#background-estimate-max-terms) | — |
    | [Inputs digest](../physics/parameters.md#background-estimate-inputs-digest) | — |
    | [Points digest](../physics/parameters.md#background-estimate-points-digest) | — |

    **[<span class="ed-reference-icon" data-reference-category="instrument" aria-hidden="true">&#62992;</span> Instrument](../physics/parameters.md#instrument)**

    | Parameter or field | Python name |
    | --- | --- |
    | [TOF offset](../physics/parameters.md#instrument-calib-d-to-tof-offset) | <code>project.experiments[0].instrument.calib_d_to_tof_offset</code> |
    | [TOF linear](../physics/parameters.md#instrument-calib-d-to-tof-linear) | <code>project.experiments[0].instrument.calib_d_to_tof_linear</code> |
    | [TOF quadratic](../physics/parameters.md#instrument-calib-d-to-tof-quadratic) | <code>project.experiments[0].instrument.calib_d_to_tof_quadratic</code> |
    | [TOF reciprocal](../physics/parameters.md#instrument-calib-d-to-tof-reciprocal) | <code>project.experiments[0].instrument.calib_d_to_tof_reciprocal</code> |
    | [Zero-point angular offset](../physics/parameters.md#instrument-calib-twotheta-offset) | <code>project.experiments[0].instrument.calib_twotheta_offset</code> |
    | [Wavelength](../physics/parameters.md#instrument-setup-wavelength) | <code>project.experiments[0].instrument.setup_wavelength</code> |
    | [Sample displacement](../physics/parameters.md#instrument-calib-sample-displacement) | <code>project.experiments[0].instrument.calib_sample_displacement</code> |
    | [Sample transparency](../physics/parameters.md#instrument-calib-sample-transparency) | <code>project.experiments[0].instrument.calib_sample_transparency</code> |
    | [Polarization coefficient](../physics/parameters.md#instrument-setup-polarization-coefficient) | <code>project.experiments[0].instrument.setup_polarization_coefficient</code> |
    | [Monochromator 2θ](../physics/parameters.md#instrument-setup-monochromator-twotheta) | <code>project.experiments[0].instrument.setup_monochromator_twotheta</code> |
    | [Secondary wavelength](../physics/parameters.md#instrument-setup-wavelength-2) | <code>project.experiments[0].instrument.setup_wavelength_2</code> |
    | [Secondary-to-primary intensity ratio](../physics/parameters.md#instrument-setup-wavelength-2-to-1-ratio) | <code>project.experiments[0].instrument.setup_wavelength_2_to_1_ratio</code> |
    | [Instrument](../physics/parameters.md#instrument-name) | <code>project.experiments[0].instrument.name</code> |
    | [Facility](../physics/parameters.md#instrument-facility) | <code>project.experiments[0].instrument.facility</code> |
    | [2θ bank](../physics/parameters.md#instrument-setup-twotheta-bank) | <code>project.experiments[0].instrument.setup_twotheta_bank</code> |

    **[<span class="ed-reference-icon" data-reference-category="peak" aria-hidden="true">&#63007;</span> Peak profile](../physics/parameters.md#peak)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Exponential rise coefficient α₀](../physics/parameters.md#peak-rise-alpha-0) | <code>project.experiments[0].peak.rise_alpha_0</code> |
    | [Exponential rise coefficient α₁](../physics/parameters.md#peak-rise-alpha-1) | <code>project.experiments[0].peak.rise_alpha_1</code> |
    | [Exponential decay coefficient β₀](../physics/parameters.md#peak-decay-beta-0) | <code>project.experiments[0].peak.decay_beta_0</code> |
    | [Exponential decay coefficient β₁](../physics/parameters.md#peak-decay-beta-1) | <code>project.experiments[0].peak.decay_beta_1</code> |
    | [Gaussian broadening σ₀²](../physics/parameters.md#peak-broad-gauss-sigma-0) | <code>project.experiments[0].peak.broad_gauss_sigma_0</code> |
    | [Gaussian broadening σ₁²](../physics/parameters.md#peak-broad-gauss-sigma-1) | <code>project.experiments[0].peak.broad_gauss_sigma_1</code> |
    | [Gaussian broadening σ₂²](../physics/parameters.md#peak-broad-gauss-sigma-2) | <code>project.experiments[0].peak.broad_gauss_sigma_2</code> |
    | [Gaussian broadening size G](../physics/parameters.md#peak-broad-gauss-size) | <code>project.experiments[0].peak.broad_gauss_size</code> |
    | [Gaussian broadening strain G](../physics/parameters.md#peak-broad-gauss-strain) | <code>project.experiments[0].peak.broad_gauss_strain</code> |
    | [Lorentzian broadening γ₀](../physics/parameters.md#peak-broad-lorentz-gamma-0) | <code>project.experiments[0].peak.broad_lorentz_gamma_0</code> |
    | [Lorentzian broadening γ₁](../physics/parameters.md#peak-broad-lorentz-gamma-1) | <code>project.experiments[0].peak.broad_lorentz_gamma_1</code> |
    | [Lorentzian broadening γ₂](../physics/parameters.md#peak-broad-lorentz-gamma-2) | <code>project.experiments[0].peak.broad_lorentz_gamma_2</code> |
    | [Lorentzian broadening size L](../physics/parameters.md#peak-broad-lorentz-size) | <code>project.experiments[0].peak.broad_lorentz_size</code> |
    | [Lorentzian broadening strain L](../physics/parameters.md#peak-broad-lorentz-strain) | <code>project.experiments[0].peak.broad_lorentz_strain</code> |
    | [Gaussian broadening U](../physics/parameters.md#peak-broad-gauss-u) | <code>project.experiments[0].peak.broad_gauss_u</code> |
    | [Gaussian broadening V](../physics/parameters.md#peak-broad-gauss-v) | <code>project.experiments[0].peak.broad_gauss_v</code> |
    | [Gaussian broadening W](../physics/parameters.md#peak-broad-gauss-w) | <code>project.experiments[0].peak.broad_gauss_w</code> |
    | [Lorentzian broadening X](../physics/parameters.md#peak-broad-lorentz-x) | <code>project.experiments[0].peak.broad_lorentz_x</code> |
    | [Lorentzian broadening Y](../physics/parameters.md#peak-broad-lorentz-y) | <code>project.experiments[0].peak.broad_lorentz_y</code> |
    | [Pseudo-Voigt mixing intercept](../physics/parameters.md#peak-mixing-eta-0) | <code>project.experiments[0].peak.mixing_eta_0</code> |
    | [Pseudo-Voigt mixing slope](../physics/parameters.md#peak-mixing-eta-1) | <code>project.experiments[0].peak.mixing_eta_1</code> |
    | [FCJ asymmetry S/L](../physics/parameters.md#peak-asym-fcj-1) | <code>project.experiments[0].peak.asym_fcj_1</code> |
    | [FCJ asymmetry D/L](../physics/parameters.md#peak-asym-fcj-2) | <code>project.experiments[0].peak.asym_fcj_2</code> |
    | [Bérar-Baldinozzi asymmetry A₀](../physics/parameters.md#peak-asym-beba-a0) | <code>project.experiments[0].peak.asym_beba_a0</code> |
    | [Bérar-Baldinozzi asymmetry B₀](../physics/parameters.md#peak-asym-beba-b0) | <code>project.experiments[0].peak.asym_beba_b0</code> |
    | [Bérar-Baldinozzi asymmetry A₁](../physics/parameters.md#peak-asym-beba-a1) | <code>project.experiments[0].peak.asym_beba_a1</code> |
    | [Bérar-Baldinozzi asymmetry B₁](../physics/parameters.md#peak-asym-beba-b1) | <code>project.experiments[0].peak.asym_beba_b1</code> |
    | [Bérar-Baldinozzi asymmetry AsyLim](../physics/parameters.md#peak-asym-beba-limit) | <code>project.experiments[0].peak.asym_beba_limit</code> |
    | [Profile](../physics/parameters.md#peak-type) | <code>project.experiments[0].peak.type</code> |
    | [Peak calculation cutoff](../physics/parameters.md#peak-cutoff-fwhm) | <code>project.experiments[0].peak.cutoff_fwhm</code> |

    **[<span class="ed-reference-icon" data-reference-category="excluded-region" aria-hidden="true">&#61741;</span> Excluded region](../physics/parameters.md#excluded-region)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Id](../physics/parameters.md#excluded-region-id) | — |
    | [Start](../physics/parameters.md#excluded-region-start) | — |
    | [End](../physics/parameters.md#excluded-region-end) | — |

    **[<span class="ed-reference-icon" data-reference-category="extinction" aria-hidden="true">&#62373;</span> Extinction](../physics/parameters.md#extinction)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Domain radius](../physics/parameters.md#extinction-domain-radius) | — |
    | [Mosaic spread](../physics/parameters.md#extinction-mosaic-spread) | — |
    | [Crystal radius](../physics/parameters.md#extinction-crystal-radius) | — |
    | [Extinction coefficient](../physics/parameters.md#extinction-coefficient) | — |
    | [X11](../physics/parameters.md#extinction-coefficient-11) | — |
    | [X22](../physics/parameters.md#extinction-coefficient-22) | — |
    | [X33](../physics/parameters.md#extinction-coefficient-33) | — |
    | [X12](../physics/parameters.md#extinction-coefficient-12) | — |
    | [X13](../physics/parameters.md#extinction-coefficient-13) | — |
    | [X23](../physics/parameters.md#extinction-coefficient-23) | — |
    | [Type](../physics/parameters.md#extinction-type) | — |
    | [Mosaic distribution](../physics/parameters.md#extinction-mosaic-distribution) | — |

    **[<span class="ed-reference-icon" data-reference-category="linked-structure" aria-hidden="true">&#62973;</span> Linked structure](../physics/parameters.md#linked-structure)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Scale](../physics/parameters.md#linked-structure-scale) | <code>project.experiments[0].linked_structures[0].scale</code> |
    | [Structure](../physics/parameters.md#linked-structure-structure-id) | <code>project.experiments[0].linked_structures[0].structure_id</code> |
    | [Enabled](../physics/parameters.md#linked-structure-enabled) | <code>project.experiments[0].linked_structures[0].enabled</code> |
    | [Phase mass fraction](../physics/parameters.md#linked-structure-weight-fraction) | — |

    **[<span class="ed-reference-icon" data-reference-category="absorption" aria-hidden="true">&#61507;</span> Absorption](../physics/parameters.md#absorption)**

    | Parameter or field | Python name |
    | --- | --- |
    | [ABSCOR1](../physics/parameters.md#absorption-abscor1) | <code>project.experiments[0].absorption.abscor1</code> |
    | [ABSCOR2](../physics/parameters.md#absorption-abscor2) | <code>project.experiments[0].absorption.abscor2</code> |
    | [ΜR](../physics/parameters.md#absorption-mu-r) | <code>project.experiments[0].absorption.mu_r</code> |
    | [Type](../physics/parameters.md#absorption-type) | <code>project.experiments[0].absorption.type</code> |

    **[<span class="ed-reference-icon" data-reference-category="preferred-orientation" aria-hidden="true">&#61774;</span> Preferred orientation](../physics/parameters.md#preferred-orientation)**

    | Parameter or field | Python name |
    | --- | --- |
    | [March-Dollase coefficient](../physics/parameters.md#preferred-orientation-march-r) | — |
    | [Randomly oriented fraction](../physics/parameters.md#preferred-orientation-march-random-fract) | — |
    | [Structure](../physics/parameters.md#preferred-orientation-structure-id) | — |
    | [Miller index h](../physics/parameters.md#preferred-orientation-index-h) | — |
    | [Miller index k](../physics/parameters.md#preferred-orientation-index-k) | — |
    | [Miller index l](../physics/parameters.md#preferred-orientation-index-l) | — |

    **[<span class="ed-reference-icon" data-reference-category="reflns" aria-hidden="true">&#61616;</span> Observed reflections](../physics/parameters.md#reflns)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Observed-reflection threshold](../physics/parameters.md#reflns-threshold-sigma) | — |
    | [On](../physics/parameters.md#reflns-threshold-basis) | — |
    | [Threshold](../physics/parameters.md#reflns-threshold-expression) | — |

    **[<span class="ed-reference-icon" data-reference-category="scattering-source" aria-hidden="true">&#62930;</span> Scattering source](../physics/parameters.md#scattering-source)**

    | Parameter or field | Python name |
    | --- | --- |
    | [X-ray form factors](../physics/parameters.md#scattering-source-xray-form-factor) | — |
    | [X-ray dispersion](../physics/parameters.md#scattering-source-xray-dispersion) | — |
    | [Neutron scattering lengths](../physics/parameters.md#scattering-source-neutron-scattering-length) | — |

    **[<span class="ed-reference-icon" data-reference-category="data-source" aria-hidden="true">&#62831;</span> Data source](../physics/parameters.md#data-source)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Measured-data filename](../physics/parameters.md#data-source-file-name) | — |

    **[<span class="ed-reference-icon" data-reference-category="data" aria-hidden="true">&#62263;</span> Measured data point](../physics/parameters.md#data)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Scattering angle](../physics/parameters.md#data-two-theta) | — |
    | [Time of flight](../physics/parameters.md#data-time-of-flight) | — |
    | [Measured intensity](../physics/parameters.md#data-intensity-meas) | — |
    | [Measured intensity uncertainty](../physics/parameters.md#data-intensity-meas-su) | — |
    | [Interplanar spacing](../physics/parameters.md#data-d-spacing) | — |
    | [Calculated intensity](../physics/parameters.md#data-intensity-calc) | — |
    | [Background intensity](../physics/parameters.md#data-intensity-bkg) | — |
    | [Calculation status](../physics/parameters.md#data-calc-status) | — |

    **[<span class="ed-reference-icon" data-reference-category="data-calc" aria-hidden="true">&#61950;</span> Calculated point](../physics/parameters.md#data-calc)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Point](../physics/parameters.md#data-calc-point-id) | — |

    **[<span class="ed-reference-icon" data-reference-category="pd-calc-overall" aria-hidden="true">&#61950;</span> Structure curves](../physics/parameters.md#pd-calc-overall)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Structure order](../physics/parameters.md#pd-calc-overall-component-presentation-order) | — |

    **[<span class="ed-reference-icon" data-reference-category="pd-calc" aria-hidden="true">&#61950;</span> Structure curve](../physics/parameters.md#pd-calc)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Structure calc](../physics/parameters.md#pd-calc-component-intensities-net) | — |

    **[<span class="ed-reference-icon" data-reference-category="refln" aria-hidden="true">&#61498;</span> Reflection](../physics/parameters.md#refln)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Structure](../physics/parameters.md#refln-structure-id) | — |
    | [Interplanar spacing](../physics/parameters.md#refln-d-spacing) | — |
    | [Sin θ/λ](../physics/parameters.md#refln-sin-theta-over-lambda) | — |
    | [Miller index h](../physics/parameters.md#refln-index-h) | — |
    | [Miller index k](../physics/parameters.md#refln-index-k) | — |
    | [Miller index l](../physics/parameters.md#refln-index-l) | — |
    | [F calc](../physics/parameters.md#refln-f-calc) | — |
    | [F meas](../physics/parameters.md#refln-f-meas) | — |
    | [F² calc](../physics/parameters.md#refln-f-squared-calc) | — |
    | [Measured intensity](../physics/parameters.md#refln-intensity-meas) | — |
    | [Measured intensity uncertainty](../physics/parameters.md#refln-intensity-meas-su) | — |
    | [Calculated intensity](../physics/parameters.md#refln-intensity-calc) | — |
    | [Λ](../physics/parameters.md#refln-wavelength) | — |
    | [Scattering angle](../physics/parameters.md#refln-two-theta) | — |
    | [Time of flight](../physics/parameters.md#refln-time-of-flight) | — |

=== "CIF"

    **[<span class="ed-reference-icon" data-reference-category="experiment-type" aria-hidden="true">&#63417;</span> Experiment type](../physics/parameters.md#experiment-type)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Beam mode](../physics/parameters.md#experiment-type-beam-mode) | <code>_edi_experiment_type.beam_mode</code><details><summary>Accepted aliases</summary><code>_easydiffraction_experiment_type.beam_mode</code><br><code>_expt_type.beam_mode</code></details> |
    | [Sample form](../physics/parameters.md#experiment-type-sample-form) | <code>_edi_experiment_type.sample_form</code><details><summary>Accepted aliases</summary><code>_easydiffraction_experiment_type.sample_form</code><br><code>_expt_type.sample_form</code></details> |
    | [Probe](../physics/parameters.md#experiment-type-radiation-probe) | <code>_diffrn_radiation.probe</code><details><summary>Accepted aliases</summary><code>_diffrn_radiation_probe</code><br><code>_easydiffraction_experiment_type.radiation_probe</code><br><code>_expt_type.radiation_probe</code></details> |
    | [Scattering type](../physics/parameters.md#experiment-type-scattering-type) | <code>_edi_experiment_type.scattering_type</code><details><summary>Accepted aliases</summary><code>_easydiffraction_experiment_type.scattering_type</code><br><code>_expt_type.scattering_type</code></details> |
    | [Dimensionality](../physics/parameters.md#experiment-type-dimensionality) | <code>_edi_experiment_type.dimensionality</code> |
    | [Polarisation](../physics/parameters.md#experiment-type-polarisation) | <code>_edi_experiment_type.polarisation</code> |

    **[<span class="ed-reference-icon" data-reference-category="data-range" aria-hidden="true">&#62263;</span> Calculation range](../physics/parameters.md#data-range)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Min](../physics/parameters.md#data-range-two-theta-min) | <code>_pd_meas.2theta_range_min</code><details><summary>Accepted aliases</summary><code>_pd_meas_2theta_range_min</code></details> |
    | [Max](../physics/parameters.md#data-range-two-theta-max) | <code>_pd_meas.2theta_range_max</code><details><summary>Accepted aliases</summary><code>_pd_meas_2theta_range_max</code></details> |
    | [Step](../physics/parameters.md#data-range-two-theta-step) | <code>_pd_meas.2theta_range_inc</code><details><summary>Accepted aliases</summary><code>_pd_meas_2theta_range_inc</code></details> |
    | [Scattering angle](../physics/parameters.md#data-range-two-theta) | <code>_edi_data_range.two_theta</code> |
    | [Min](../physics/parameters.md#data-range-time-of-flight-min) | <code>_edi_data_range.time_of_flight_min</code><details><summary>Accepted aliases</summary><code>_pd_meas.time_of_flight_range_min</code></details> |
    | [Max](../physics/parameters.md#data-range-time-of-flight-max) | <code>_edi_data_range.time_of_flight_max</code><details><summary>Accepted aliases</summary><code>_pd_meas.time_of_flight_range_max</code></details> |
    | [Step](../physics/parameters.md#data-range-time-of-flight-step) | <code>_edi_data_range.time_of_flight_step</code> |
    | [Time of flight](../physics/parameters.md#data-range-time-of-flight) | <code>_edi_data_range.time_of_flight</code> |

    **[<span class="ed-reference-icon" data-reference-category="background" aria-hidden="true">&#63550;</span> Background](../physics/parameters.md#background)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Background anchor intensity](../physics/parameters.md#background-intensity) | <code>_pd_background.line_segment_intensity</code><details><summary>Accepted aliases</summary><code>_pd_background_line_segment_intensity</code></details> |
    | [Background anchor position](../physics/parameters.md#background-position) | <code>_pd_background.line_segment_X</code><details><summary>Accepted aliases</summary><code>_pd_background_line_segment_X</code></details> |
    | [Background coefficient](../physics/parameters.md#background-coef) | <code>_pd_background.Chebyshev_coef</code> |
    | [Background term order](../physics/parameters.md#background-order) | <code>_pd_background.Chebyshev_order</code> |
    | [Polynomial background origin](../physics/parameters.md#background-origin) | <code>_edi_background.origin</code> |
    | [Chebyshev domain minimum](../physics/parameters.md#background-x-min) | <code>_edi_background.x_min</code> |
    | [Chebyshev domain maximum](../physics/parameters.md#background-x-max) | <code>_edi_background.x_max</code> |
    | [Background model](../physics/parameters.md#background-type) | <code>_edi_background.type</code><details><summary>Accepted aliases</summary><code>_easydiffraction_background.type</code></details> |
    | [Background row identifier](../physics/parameters.md#background-id) | <code>_pd_background.id</code> |

    **[<span class="ed-reference-icon" data-reference-category="background-estimate" aria-hidden="true">&#61648;</span> Background estimation](../physics/parameters.md#background-estimate)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Estimation mode](../physics/parameters.md#background-estimate-mode) | <code>_edi_background_estimate.mode</code> |
    | [Method](../physics/parameters.md#background-estimate-method) | <code>_edi_background_estimate.method</code> |
    | [Peak width](../physics/parameters.md#background-estimate-width) | <code>_edi_background_estimate.width</code> |
    | [Smoothness](../physics/parameters.md#background-estimate-smoothness) | <code>_edi_background_estimate.smoothness</code> |
    | [Number of background anchors](../physics/parameters.md#background-estimate-n-points) | <code>_edi_background_estimate.n_points</code> |
    | [Background thinning tolerance](../physics/parameters.md#background-estimate-tolerance) | <code>_edi_background_estimate.tolerance</code> |
    | [Anchors within peaks](../physics/parameters.md#background-estimate-in-peaks) | <code>_edi_background_estimate.in_peaks</code> |
    | [Calculated-peak treatment](../physics/parameters.md#background-estimate-use-model) | <code>_edi_background_estimate.use_model</code> |
    | [Max terms](../physics/parameters.md#background-estimate-max-terms) | <code>_edi_background_estimate.max_terms</code> |
    | [Inputs digest](../physics/parameters.md#background-estimate-inputs-digest) | <code>_edi_background_estimate.inputs_digest</code> |
    | [Points digest](../physics/parameters.md#background-estimate-points-digest) | <code>_edi_background_estimate.points_digest</code> |

    **[<span class="ed-reference-icon" data-reference-category="instrument" aria-hidden="true">&#62992;</span> Instrument](../physics/parameters.md#instrument)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [TOF offset](../physics/parameters.md#instrument-calib-d-to-tof-offset) | <code>_edi_instrument.calib_d_to_tof_offset</code><details><summary>Accepted aliases</summary><code>_instr.d_to_tof_offset</code></details> |
    | [TOF linear](../physics/parameters.md#instrument-calib-d-to-tof-linear) | <code>_edi_instrument.calib_d_to_tof_linear</code><details><summary>Accepted aliases</summary><code>_instr.d_to_tof_linear</code></details> |
    | [TOF quadratic](../physics/parameters.md#instrument-calib-d-to-tof-quadratic) | <code>_edi_instrument.calib_d_to_tof_quadratic</code><details><summary>Accepted aliases</summary><code>_instr.d_to_tof_quad</code></details> |
    | [TOF reciprocal](../physics/parameters.md#instrument-calib-d-to-tof-reciprocal) | <code>_edi_instrument.calib_d_to_tof_reciprocal</code><details><summary>Accepted aliases</summary><code>_instr.d_to_tof_recip</code></details> |
    | [Zero-point angular offset](../physics/parameters.md#instrument-calib-twotheta-offset) | <code>_pd_calib.2theta_offset</code><details><summary>Accepted aliases</summary><code>_pd_calib_2theta_offset</code><br><code>_instr.2theta_offset</code></details> |
    | [Wavelength](../physics/parameters.md#instrument-setup-wavelength) | <code>_diffrn_radiation_wavelength.value</code><details><summary>Accepted aliases</summary><code>_diffrn_radiation_wavelength</code><br><code>_diffrn_radiation_wavelength.wavelength</code><br><code>_instr.wavelength</code></details> |
    | [Sample displacement](../physics/parameters.md#instrument-calib-sample-displacement) | <code>_edi_instrument.calib_sample_displacement</code><details><summary>Accepted aliases</summary><code>_instr.sample_displacement</code></details> |
    | [Sample transparency](../physics/parameters.md#instrument-calib-sample-transparency) | <code>_edi_instrument.calib_sample_transparency</code><details><summary>Accepted aliases</summary><code>_instr.sample_transparency</code></details> |
    | [Polarization coefficient](../physics/parameters.md#instrument-setup-polarization-coefficient) | <code>_edi_instrument.setup_polarization_coefficient</code> |
    | [Monochromator 2θ](../physics/parameters.md#instrument-setup-monochromator-twotheta) | <code>_edi_instrument.setup_monochromator_twotheta</code> |
    | [Secondary wavelength](../physics/parameters.md#instrument-setup-wavelength-2) | <code>_edi_instrument.setup_wavelength_2</code> |
    | [Secondary-to-primary intensity ratio](../physics/parameters.md#instrument-setup-wavelength-2-to-1-ratio) | <code>_edi_instrument.setup_wavelength_2_to_1_ratio</code> |
    | [Instrument](../physics/parameters.md#instrument-name) | <code>_diffrn_source.beamline</code> |
    | [Facility](../physics/parameters.md#instrument-facility) | <code>_diffrn_source.facility</code> |
    | [2θ bank](../physics/parameters.md#instrument-setup-twotheta-bank) | <code>_pd_meas.2theta_fixed</code><details><summary>Accepted aliases</summary><code>_pd_meas_2theta_fixed</code><br><code>_instr.2theta_bank</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="peak" aria-hidden="true">&#63007;</span> Peak profile](../physics/parameters.md#peak)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Exponential rise coefficient α₀](../physics/parameters.md#peak-rise-alpha-0) | <code>_edi_peak.rise_alpha_0</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.rise_alpha_0</code></details> |
    | [Exponential rise coefficient α₁](../physics/parameters.md#peak-rise-alpha-1) | <code>_edi_peak.rise_alpha_1</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.rise_alpha_1</code></details> |
    | [Exponential decay coefficient β₀](../physics/parameters.md#peak-decay-beta-0) | <code>_edi_peak.decay_beta_0</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.decay_beta_0</code></details> |
    | [Exponential decay coefficient β₁](../physics/parameters.md#peak-decay-beta-1) | <code>_edi_peak.decay_beta_1</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.decay_beta_1</code></details> |
    | [Gaussian broadening σ₀²](../physics/parameters.md#peak-broad-gauss-sigma-0) | <code>_edi_peak.broad_gauss_sigma_0</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.broad_gauss_sigma_0</code></details> |
    | [Gaussian broadening σ₁²](../physics/parameters.md#peak-broad-gauss-sigma-1) | <code>_edi_peak.broad_gauss_sigma_1</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.broad_gauss_sigma_1</code></details> |
    | [Gaussian broadening σ₂²](../physics/parameters.md#peak-broad-gauss-sigma-2) | <code>_edi_peak.broad_gauss_sigma_2</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.broad_gauss_sigma_2</code></details> |
    | [Gaussian broadening size G](../physics/parameters.md#peak-broad-gauss-size) | <code>_edi_peak.broad_gauss_size</code> |
    | [Gaussian broadening strain G](../physics/parameters.md#peak-broad-gauss-strain) | <code>_edi_peak.broad_gauss_strain</code> |
    | [Lorentzian broadening γ₀](../physics/parameters.md#peak-broad-lorentz-gamma-0) | <code>_edi_peak.broad_lorentz_gamma_0</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.broad_lorentz_gamma_0</code></details> |
    | [Lorentzian broadening γ₁](../physics/parameters.md#peak-broad-lorentz-gamma-1) | <code>_edi_peak.broad_lorentz_gamma_1</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.broad_lorentz_gamma_1</code></details> |
    | [Lorentzian broadening γ₂](../physics/parameters.md#peak-broad-lorentz-gamma-2) | <code>_edi_peak.broad_lorentz_gamma_2</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.broad_lorentz_gamma_2</code></details> |
    | [Lorentzian broadening size L](../physics/parameters.md#peak-broad-lorentz-size) | <code>_edi_peak.broad_lorentz_size</code> |
    | [Lorentzian broadening strain L](../physics/parameters.md#peak-broad-lorentz-strain) | <code>_edi_peak.broad_lorentz_strain</code> |
    | [Gaussian broadening U](../physics/parameters.md#peak-broad-gauss-u) | <code>_edi_peak.broad_gauss_u</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.broad_gauss_u</code></details> |
    | [Gaussian broadening V](../physics/parameters.md#peak-broad-gauss-v) | <code>_edi_peak.broad_gauss_v</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.broad_gauss_v</code></details> |
    | [Gaussian broadening W](../physics/parameters.md#peak-broad-gauss-w) | <code>_edi_peak.broad_gauss_w</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.broad_gauss_w</code></details> |
    | [Lorentzian broadening X](../physics/parameters.md#peak-broad-lorentz-x) | <code>_edi_peak.broad_lorentz_x</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.broad_lorentz_x</code></details> |
    | [Lorentzian broadening Y](../physics/parameters.md#peak-broad-lorentz-y) | <code>_edi_peak.broad_lorentz_y</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.broad_lorentz_y</code></details> |
    | [Pseudo-Voigt mixing intercept](../physics/parameters.md#peak-mixing-eta-0) | <code>_edi_peak.mixing_eta_0</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.mixing_eta_0</code></details> |
    | [Pseudo-Voigt mixing slope](../physics/parameters.md#peak-mixing-eta-1) | <code>_edi_peak.mixing_eta_1</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.mixing_eta_1</code></details> |
    | [FCJ asymmetry S/L](../physics/parameters.md#peak-asym-fcj-1) | <code>_edi_peak.asym_fcj_1</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.asym_fcj_1</code></details> |
    | [FCJ asymmetry D/L](../physics/parameters.md#peak-asym-fcj-2) | <code>_edi_peak.asym_fcj_2</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.asym_fcj_2</code></details> |
    | [Bérar-Baldinozzi asymmetry A₀](../physics/parameters.md#peak-asym-beba-a0) | <code>_edi_peak.asym_beba_a0</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.asym_beba_a0</code></details> |
    | [Bérar-Baldinozzi asymmetry B₀](../physics/parameters.md#peak-asym-beba-b0) | <code>_edi_peak.asym_beba_b0</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.asym_beba_b0</code></details> |
    | [Bérar-Baldinozzi asymmetry A₁](../physics/parameters.md#peak-asym-beba-a1) | <code>_edi_peak.asym_beba_a1</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.asym_beba_a1</code></details> |
    | [Bérar-Baldinozzi asymmetry B₁](../physics/parameters.md#peak-asym-beba-b1) | <code>_edi_peak.asym_beba_b1</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.asym_beba_b1</code></details> |
    | [Bérar-Baldinozzi asymmetry AsyLim](../physics/parameters.md#peak-asym-beba-limit) | <code>_edi_peak.asym_beba_limit</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.asym_beba_limit</code></details> |
    | [Profile](../physics/parameters.md#peak-type) | <code>_edi_peak.type</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.type</code></details> |
    | [Peak calculation cutoff](../physics/parameters.md#peak-cutoff-fwhm) | <code>_edi_peak.cutoff_fwhm</code><details><summary>Accepted aliases</summary><code>_easydiffraction_peak.cutoff_fwhm</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="excluded-region" aria-hidden="true">&#61741;</span> Excluded region](../physics/parameters.md#excluded-region)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Id](../physics/parameters.md#excluded-region-id) | <code>_edi_excluded_region.id</code><details><summary>Accepted aliases</summary><code>_easydiffraction_excluded_region.id</code></details> |
    | [Start](../physics/parameters.md#excluded-region-start) | <code>_edi_excluded_region.start</code><details><summary>Accepted aliases</summary><code>_easydiffraction_excluded_region.start</code></details> |
    | [End](../physics/parameters.md#excluded-region-end) | <code>_edi_excluded_region.end</code><details><summary>Accepted aliases</summary><code>_easydiffraction_excluded_region.end</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="extinction" aria-hidden="true">&#62373;</span> Extinction](../physics/parameters.md#extinction)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Domain radius](../physics/parameters.md#extinction-domain-radius) | <code>_edi_extinction.domain_radius</code> |
    | [Mosaic spread](../physics/parameters.md#extinction-mosaic-spread) | <code>_edi_extinction.mosaic_spread</code> |
    | [Crystal radius](../physics/parameters.md#extinction-crystal-radius) | <code>_exptl_crystal.size_rad</code><details><summary>Accepted aliases</summary><code>_exptl_crystal_size_rad</code></details> |
    | [Extinction coefficient](../physics/parameters.md#extinction-coefficient) | <code>_edi_extinction.coefficient</code> |
    | [X11](../physics/parameters.md#extinction-coefficient-11) | <code>_edi_extinction.coefficient_11</code> |
    | [X22](../physics/parameters.md#extinction-coefficient-22) | <code>_edi_extinction.coefficient_22</code> |
    | [X33](../physics/parameters.md#extinction-coefficient-33) | <code>_edi_extinction.coefficient_33</code> |
    | [X12](../physics/parameters.md#extinction-coefficient-12) | <code>_edi_extinction.coefficient_12</code> |
    | [X13](../physics/parameters.md#extinction-coefficient-13) | <code>_edi_extinction.coefficient_13</code> |
    | [X23](../physics/parameters.md#extinction-coefficient-23) | <code>_edi_extinction.coefficient_23</code> |
    | [Type](../physics/parameters.md#extinction-type) | <code>_edi_extinction.type</code><details><summary>Accepted aliases</summary><code>_easydiffraction_extinction.type</code></details> |
    | [Mosaic distribution](../physics/parameters.md#extinction-mosaic-distribution) | <code>_edi_extinction.mosaic_distribution</code> |

    **[<span class="ed-reference-icon" data-reference-category="linked-structure" aria-hidden="true">&#62973;</span> Linked structure](../physics/parameters.md#linked-structure)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Scale](../physics/parameters.md#linked-structure-scale) | <code>_edi_linked_structure.scale</code><details><summary>Accepted aliases</summary><code>_pd_phase_block.scale</code><br><code>_easydiffraction_sc_crystal_block.scale</code><br><code>_sc_crystal_block.scale</code></details> |
    | [Structure](../physics/parameters.md#linked-structure-structure-id) | <code>_pd_phase_block.id</code><details><summary>Accepted aliases</summary><code>_pd_phase_block_id</code><br><code>_easydiffraction_sc_crystal_block.id</code><br><code>_sc_crystal_block.id</code></details> |
    | [Enabled](../physics/parameters.md#linked-structure-enabled) | <code>_edi_linked_structure.enabled</code> |
    | [Phase mass fraction](../physics/parameters.md#linked-structure-weight-fraction) | <code>_edi_linked_structure.weight_fraction</code> |

    **[<span class="ed-reference-icon" data-reference-category="absorption" aria-hidden="true">&#61507;</span> Absorption](../physics/parameters.md#absorption)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [ABSCOR1](../physics/parameters.md#absorption-abscor1) | <code>_edi_absorption.abscor1</code> |
    | [ABSCOR2](../physics/parameters.md#absorption-abscor2) | <code>_edi_absorption.abscor2</code> |
    | [ΜR](../physics/parameters.md#absorption-mu-r) | <code>_edi_absorption.mu_r</code><details><summary>Accepted aliases</summary><code>_easydiffraction_absorption.mu_r</code></details> |
    | [Type](../physics/parameters.md#absorption-type) | <code>_edi_absorption.type</code><details><summary>Accepted aliases</summary><code>_easydiffraction_absorption.type</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="preferred-orientation" aria-hidden="true">&#61774;</span> Preferred orientation](../physics/parameters.md#preferred-orientation)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [March-Dollase coefficient](../physics/parameters.md#preferred-orientation-march-r) | <code>_pd_pref_orient_March_Dollase.r</code><details><summary>Accepted aliases</summary><code>_pref_orient.march_r</code></details> |
    | [Randomly oriented fraction](../physics/parameters.md#preferred-orientation-march-random-fract) | <code>_edi_preferred_orientation.march_random_fract</code><details><summary>Accepted aliases</summary><code>_easydiffraction_pref_orient.march_random_fract</code><br><code>_pref_orient.march_random_fract</code></details> |
    | [Structure](../physics/parameters.md#preferred-orientation-structure-id) | <code>_pd_pref_orient_March_Dollase.phase_id</code><details><summary>Accepted aliases</summary><code>_pref_orient.phase_id</code></details> |
    | [Miller index h](../physics/parameters.md#preferred-orientation-index-h) | <code>_pd_pref_orient_March_Dollase.index_h</code><details><summary>Accepted aliases</summary><code>_pref_orient.index_h</code></details> |
    | [Miller index k](../physics/parameters.md#preferred-orientation-index-k) | <code>_pd_pref_orient_March_Dollase.index_k</code><details><summary>Accepted aliases</summary><code>_pref_orient.index_k</code></details> |
    | [Miller index l](../physics/parameters.md#preferred-orientation-index-l) | <code>_pd_pref_orient_March_Dollase.index_l</code><details><summary>Accepted aliases</summary><code>_pref_orient.index_l</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="reflns" aria-hidden="true">&#61616;</span> Observed reflections](../physics/parameters.md#reflns)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Observed-reflection threshold](../physics/parameters.md#reflns-threshold-sigma) | <code>_edi_reflns.threshold_sigma</code> |
    | [On](../physics/parameters.md#reflns-threshold-basis) | <code>_edi_reflns.threshold_basis</code> |
    | [Threshold](../physics/parameters.md#reflns-threshold-expression) | <code>_reflns.threshold_expression</code><details><summary>Accepted aliases</summary><code>_reflns_threshold_expression</code><br><code>_reflns_observed_criterion</code><br><code>_reflns.observed_criterion</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="scattering-source" aria-hidden="true">&#62930;</span> Scattering source](../physics/parameters.md#scattering-source)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [X-ray form factors](../physics/parameters.md#scattering-source-xray-form-factor) | <code>_edi_scattering_source.xray_form_factor</code> |
    | [X-ray dispersion](../physics/parameters.md#scattering-source-xray-dispersion) | <code>_edi_scattering_source.xray_dispersion</code> |
    | [Neutron scattering lengths](../physics/parameters.md#scattering-source-neutron-scattering-length) | <code>_edi_scattering_source.neutron_scattering_length</code> |

    **[<span class="ed-reference-icon" data-reference-category="data-source" aria-hidden="true">&#62831;</span> Data source](../physics/parameters.md#data-source)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Measured-data filename](../physics/parameters.md#data-source-file-name) | <code>_edi_data_source.file_name</code> |

    **[<span class="ed-reference-icon" data-reference-category="data" aria-hidden="true">&#62263;</span> Measured data point](../physics/parameters.md#data)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Scattering angle](../physics/parameters.md#data-two-theta) | <code>_pd_meas.2theta_scan</code><details><summary>Accepted aliases</summary><code>_pd_meas_2theta_scan</code><br><code>_pd_meas_angle_2theta</code><br><code>_pd_proc.2theta_scan</code></details> |
    | [Time of flight](../physics/parameters.md#data-time-of-flight) | <code>_pd_meas.time_of_flight</code><details><summary>Accepted aliases</summary><code>_pd_meas_time_of_flight</code></details> |
    | [Measured intensity](../physics/parameters.md#data-intensity-meas) | <code>_pd_meas.intensity_total</code><details><summary>Accepted aliases</summary><code>_pd_meas_intensity_total</code><br><code>_pd_proc.intensity_norm</code></details> |
    | [Measured intensity uncertainty](../physics/parameters.md#data-intensity-meas-su) | <code>_pd_meas.intensity_total_su</code><details><summary>Accepted aliases</summary><code>_pd_proc.intensity_norm_su</code></details> |
    | [Interplanar spacing](../physics/parameters.md#data-d-spacing) | <code>_pd_proc.d_spacing</code><details><summary>Accepted aliases</summary><code>_pd_proc_d_spacing</code></details> |
    | [Calculated intensity](../physics/parameters.md#data-intensity-calc) | <code>_pd_calc.intensity_total</code><details><summary>Accepted aliases</summary><code>_pd_calc_intensity_total</code></details> |
    | [Background intensity](../physics/parameters.md#data-intensity-bkg) | <code>_pd_calc.intensity_bkg</code> |
    | [Calculation status](../physics/parameters.md#data-calc-status) | <code>_edi_data.calc_status</code><details><summary>Accepted aliases</summary><code>_pd_data.refinement_status</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="data-calc" aria-hidden="true">&#61950;</span> Calculated point](../physics/parameters.md#data-calc)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Point](../physics/parameters.md#data-calc-point-id) | <code>_pd_data.point_id</code><details><summary>Accepted aliases</summary><code>_pd_data_point_id</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="pd-calc-overall" aria-hidden="true">&#61950;</span> Structure curves](../physics/parameters.md#pd-calc-overall)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Structure order](../physics/parameters.md#pd-calc-overall-component-presentation-order) | <code>_edi_pd_calc_overall.component_presentation_order</code> |

    **[<span class="ed-reference-icon" data-reference-category="pd-calc" aria-hidden="true">&#61950;</span> Structure curve](../physics/parameters.md#pd-calc)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Structure calc](../physics/parameters.md#pd-calc-component-intensities-net) | <code>_pd_calc.component_intensities_net</code> |

    **[<span class="ed-reference-icon" data-reference-category="refln" aria-hidden="true">&#61498;</span> Reflection](../physics/parameters.md#refln)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Structure](../physics/parameters.md#refln-structure-id) | <code>_pd_refln.phase_id</code><details><summary>Accepted aliases</summary><code>_pd_refln_phase_id</code><br><code>_refln.phase_id</code></details> |
    | [Interplanar spacing](../physics/parameters.md#refln-d-spacing) | <code>_refln.d_spacing</code><details><summary>Accepted aliases</summary><code>_refln_d_spacing</code></details> |
    | [Sin θ/λ](../physics/parameters.md#refln-sin-theta-over-lambda) | <code>_refln.sin_theta_over_lambda</code><details><summary>Accepted aliases</summary><code>_refln_sint/lambda</code><br><code>_refln_sin_theta_over_lambda</code><br><code>_refln.sint_over_lambda</code></details> |
    | [Miller index h](../physics/parameters.md#refln-index-h) | <code>_refln.index_h</code><details><summary>Accepted aliases</summary><code>_refln_index_h</code></details> |
    | [Miller index k](../physics/parameters.md#refln-index-k) | <code>_refln.index_k</code><details><summary>Accepted aliases</summary><code>_refln_index_k</code></details> |
    | [Miller index l](../physics/parameters.md#refln-index-l) | <code>_refln.index_l</code><details><summary>Accepted aliases</summary><code>_refln_index_l</code></details> |
    | [F calc](../physics/parameters.md#refln-f-calc) | <code>_refln.F_calc</code><details><summary>Accepted aliases</summary><code>_refln_F_calc</code><br><code>_refln.f_calc</code></details> |
    | [F meas](../physics/parameters.md#refln-f-meas) | <code>_refln.F_meas</code><details><summary>Accepted aliases</summary><code>_refln_F_meas</code></details> |
    | [F² calc](../physics/parameters.md#refln-f-squared-calc) | <code>_refln.F_squared_calc</code><details><summary>Accepted aliases</summary><code>_refln_F_squared_calc</code><br><code>_refln.f_squared_calc</code></details> |
    | [Measured intensity](../physics/parameters.md#refln-intensity-meas) | <code>_refln.intensity_meas</code><details><summary>Accepted aliases</summary><code>_refln_intensity_meas</code></details> |
    | [Measured intensity uncertainty](../physics/parameters.md#refln-intensity-meas-su) | <code>_refln.intensity_meas_su</code><details><summary>Accepted aliases</summary><code>_refln_intensity_meas_su</code><br><code>_refln.intensity_sigma</code><br><code>_refln_intensity_sigma</code></details> |
    | [Calculated intensity](../physics/parameters.md#refln-intensity-calc) | <code>_refln.intensity_calc</code><details><summary>Accepted aliases</summary><code>_refln_intensity_calc</code></details> |
    | [Λ](../physics/parameters.md#refln-wavelength) | <code>_refln.wavelength</code><details><summary>Accepted aliases</summary><code>_refln_wavelength</code></details> |
    | [Scattering angle](../physics/parameters.md#refln-two-theta) | <code>_edi_refln.two_theta</code><details><summary>Accepted aliases</summary><code>_refln.two_theta</code></details> |
    | [Time of flight](../physics/parameters.md#refln-time-of-flight) | <code>_edi_refln.time_of_flight</code><details><summary>Accepted aliases</summary><code>_refln.time_of_flight</code></details> |

## Project and analysis settings

=== "GUI"

    <span class="ed-reference-anchor" id="names-metadata">**[<span class="ed-reference-icon" data-reference-category="metadata" aria-hidden="true">&#61831;</span> Project](../physics/parameters.md#metadata)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Name](../physics/parameters.md#metadata-name) | name |
    | [Title](../physics/parameters.md#metadata-title) | title |
    | [Description](../physics/parameters.md#metadata-description) | description |
    | [Authors](../physics/parameters.md#metadata-authors) | authors |
    | [Location](../physics/parameters.md#metadata-path) | location |
    | [Created](../physics/parameters.md#metadata-created) | created |
    | [Last modified](../physics/parameters.md#metadata-last-modified) | last modified |
    | [Timestamp](../physics/parameters.md#metadata-timestamp) | timestamp |

    <span class="ed-reference-anchor" id="names-su-format">**[<span class="ed-reference-icon" data-reference-category="su-format" aria-hidden="true">&#62030;</span> Standard uncertainties](../physics/parameters.md#su-format)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Uncertainty rounding rule](../physics/parameters.md#su-format-rule) | rule |

    <span class="ed-reference-anchor" id="names-report">**[<span class="ed-reference-icon" data-reference-category="report" aria-hidden="true">&#61788;</span> Report](../physics/parameters.md#report)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [HTML](../physics/parameters.md#report-html) | HTML |
    | [PDF](../physics/parameters.md#report-pdf) | PDF |
    | [CIF](../physics/parameters.md#report-cif) | CIF |
    | [Embed chart libraries](../physics/parameters.md#report-html-offline) | embed chart libraries |
    | [Excluded](../physics/parameters.md#report-excluded) | excluded |

    <span class="ed-reference-anchor" id="names-correlation-chart">**[<span class="ed-reference-icon" data-reference-category="correlation-chart" aria-hidden="true">&#61450;</span> Correlation chart](../physics/parameters.md#correlation-chart)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Threshold](../physics/parameters.md#correlation-chart-threshold) | threshold |

    <span class="ed-reference-anchor" id="names-pattern-chart">**[<span class="ed-reference-icon" data-reference-category="pattern-chart" aria-hidden="true">&#61953;</span> Pattern chart](../physics/parameters.md#pattern-chart)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [X-axis](../physics/parameters.md#pattern-chart-x-axis) | x-axis |

    <span class="ed-reference-anchor" id="names-calculator">**[<span class="ed-reference-icon" data-reference-category="calculator" aria-hidden="true">&#61932;</span> Calculator](../physics/parameters.md#calculator)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Calculator](../physics/parameters.md#calculator-type) | calculator |

    <span class="ed-reference-anchor" id="names-minimizer">**[<span class="ed-reference-icon" data-reference-category="minimizer" aria-hidden="true">&#62398;</span> Minimizer](../physics/parameters.md#minimizer)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Minimizer](../physics/parameters.md#minimizer-type) | minimizer |
    | [Max iterations](../physics/parameters.md#minimizer-max-iterations) | max iterations |
    | [Descent](../physics/parameters.md#minimizer-descent) | descent |
    | [Tolerance](../physics/parameters.md#minimizer-chi-square-tolerance) | tolerance |

    <span class="ed-reference-anchor" id="names-fitting-mode">**[<span class="ed-reference-icon" data-reference-category="fitting-mode" aria-hidden="true">&#61918;</span> Fitting mode](../physics/parameters.md#fitting-mode)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Fitting mode](../physics/parameters.md#fitting-mode-type) | mode |

    <span class="ed-reference-anchor" id="names-refine-ls">**[<span class="ed-reference-icon" data-reference-category="refine-ls" aria-hidden="true">&#61636;</span> Fitted reflections](../physics/parameters.md#refine-ls)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Fitted-reflection threshold](../physics/parameters.md#refine-ls-threshold-sigma) | fit reflections above (su) |

    <span class="ed-reference-anchor" id="names-alias">**[<span class="ed-reference-icon" data-reference-category="alias" aria-hidden="true">&#61483;</span> Alias](../physics/parameters.md#alias)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Alias](../physics/parameters.md#alias-id) | alias |
    | [Parameter](../physics/parameters.md#alias-parameter-unique-name) | parameter |

    <span class="ed-reference-anchor" id="names-constraint">**[<span class="ed-reference-icon" data-reference-category="constraint" aria-hidden="true">&#62764;</span> Constraint](../physics/parameters.md#constraint)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Id](../physics/parameters.md#constraint-id) | id |
    | [Expression](../physics/parameters.md#constraint-expression) | expression |
    | [Enabled](../physics/parameters.md#constraint-enabled) | enabled |

    <span class="ed-reference-anchor" id="names-joint-fit">**[<span class="ed-reference-icon" data-reference-category="joint-fit" aria-hidden="true">&#61633;</span> Joint-fit weights](../physics/parameters.md#joint-fit)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Weight](../physics/parameters.md#joint-fit-weight) | weight |

    <span class="ed-reference-anchor" id="names-sequential-fit">**[<span class="ed-reference-icon" data-reference-category="sequential-fit" aria-hidden="true">&#61643;</span> Sequential fit](../physics/parameters.md#sequential-fit)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Data directory](../physics/parameters.md#sequential-fit-data-dir) | data directory |
    | [Files](../physics/parameters.md#sequential-fit-file-pattern) | files |
    | [Reverse](../physics/parameters.md#sequential-fit-reverse) | reverse |
    | [Template](../physics/parameters.md#sequential-fit-template-file) | template |

    <span class="ed-reference-anchor" id="names-sequential-fit-extract">**[<span class="ed-reference-icon" data-reference-category="sequential-fit-extract" aria-hidden="true">&#61616;</span> Scan extraction rule](../physics/parameters.md#sequential-fit-extract)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Id](../physics/parameters.md#sequential-fit-extract-id) | id |
    | [Extracted value name](../physics/parameters.md#sequential-fit-extract-target) | target |
    | [Pattern](../physics/parameters.md#sequential-fit-extract-pattern) | pattern |
    | [Required](../physics/parameters.md#sequential-fit-extract-required) | required |

    <span class="ed-reference-anchor" id="names-edi">**[<span class="ed-reference-icon" data-reference-category="edi" aria-hidden="true">&#61897;</span> File header](../physics/parameters.md#edi)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Schema version](../physics/parameters.md#edi-schema-version) | schema version |

    <span class="ed-reference-anchor" id="names-report-file">**[<span class="ed-reference-icon" data-reference-category="report-file" aria-hidden="true">&#61787;</span> Saved report](../physics/parameters.md#report-file)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Format](../physics/parameters.md#report-file-format) | format |
    | [File](../physics/parameters.md#report-file-name) | file |
    | [Saved](../physics/parameters.md#report-file-saved) | saved |
    | [Project saved](../physics/parameters.md#report-file-project-last-modified) | project saved |
    | [Digest](../physics/parameters.md#report-file-digest) | digest |

    <span class="ed-reference-anchor" id="names-fit-parameter">**[<span class="ed-reference-icon" data-reference-category="fit-parameter" aria-hidden="true">&#61914;</span> Fit start value](../physics/parameters.md#fit-parameter)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Parameter](../physics/parameters.md#fit-parameter-id) | parameter |
    | [Start value](../physics/parameters.md#fit-parameter-start-value) | start value |
    | [Start error](../physics/parameters.md#fit-parameter-start-uncertainty) | start error |
    | [Start tied](../physics/parameters.md#fit-parameter-start-tied) | start tied |

    <span class="ed-reference-anchor" id="names-fit-result">**[<span class="ed-reference-icon" data-reference-category="fit-result" aria-hidden="true">&#61528;</span> Fit result](../physics/parameters.md#fit-result)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Kind](../physics/parameters.md#fit-result-result-kind) | kind |
    | [Success](../physics/parameters.md#fit-result-success) | success |
    | [Message](../physics/parameters.md#fit-result-message) | message |
    | [Iterations](../physics/parameters.md#fit-result-iterations) | iterations |
    | [Time](../physics/parameters.md#fit-result-fitting-time) | time |
    | [Reduced χ²](../physics/parameters.md#fit-result-reduced-chi-square) | reduced χ² |
    | [Objective](../physics/parameters.md#fit-result-objective-name) | objective |
    | [Objective value](../physics/parameters.md#fit-result-objective-value) | objective value |
    | [Number of fitted observations](../physics/parameters.md#fit-result-n-data-points) | points |
    | [Parameters](../physics/parameters.md#fit-result-n-parameters) | parameters |
    | [Free parameters](../physics/parameters.md#fit-result-n-free-parameters) | free parameters |
    | [Degrees of freedom](../physics/parameters.md#fit-result-degrees-of-freedom) | degrees of freedom |
    | [Covariance](../physics/parameters.md#fit-result-covariance-available) | covariance |
    | [Exit reason](../physics/parameters.md#fit-result-exit-reason) | exit reason |
    | [Rwp](../physics/parameters.md#fit-result-prof-wr-factor) | Rwp |
    | [Rp](../physics/parameters.md#fit-result-prof-r-factor) | Rp |
    | [Rexp](../physics/parameters.md#fit-result-prof-wr-expected) | Rexp |
    | [CRp](../physics/parameters.md#fit-result-prof-cr-factor) | cRp |
    | [CRwp](../physics/parameters.md#fit-result-prof-cwr-factor) | cRwp |
    | [Profile](../physics/parameters.md#fit-result-profile-function) | profile |
    | [Background](../physics/parameters.md#fit-result-background-function) | background |
    | [Descent](../physics/parameters.md#fit-result-descent) | descent |

    <span class="ed-reference-anchor" id="names-fit-result-bank">**[<span class="ed-reference-icon" data-reference-category="fit-result-bank" aria-hidden="true">&#61452;</span> Experiment fit result](../physics/parameters.md#fit-result-bank)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Number of fitted observations](../physics/parameters.md#fit-result-bank-n-data-points) | points |
    | [Rp](../physics/parameters.md#fit-result-bank-prof-r-factor) | Rp |
    | [Rwp](../physics/parameters.md#fit-result-bank-prof-wr-factor) | Rwp |
    | [Rexp](../physics/parameters.md#fit-result-bank-prof-wr-expected) | Rexp |
    | [CRp](../physics/parameters.md#fit-result-bank-prof-cr-factor) | cRp |
    | [CRwp](../physics/parameters.md#fit-result-bank-prof-cwr-factor) | cRwp |
    | [Reduced χ²](../physics/parameters.md#fit-result-bank-chi-square) | reduced χ² |

    <span class="ed-reference-anchor" id="names-fit-result-phase">**[<span class="ed-reference-icon" data-reference-category="fit-result-phase" aria-hidden="true">&#61452;</span> Structure fit result](../physics/parameters.md#fit-result-phase)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [R Bragg](../physics/parameters.md#fit-result-phase-bragg-r-factor) | R Bragg |
    | [R F](../physics/parameters.md#fit-result-phase-f-r-factor) | R F |

    <span class="ed-reference-anchor" id="names-fit-parameter-correlation">**[<span class="ed-reference-icon" data-reference-category="fit-parameter-correlation" aria-hidden="true">&#61449;</span> Correlation](../physics/parameters.md#fit-parameter-correlation)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Id](../physics/parameters.md#fit-parameter-correlation-id) | id |
    | [Source](../physics/parameters.md#fit-parameter-correlation-source-kind) | source |
    | [Parameter 1](../physics/parameters.md#fit-parameter-correlation-parameter-unique-name-i) | parameter 1 |
    | [Parameter 2](../physics/parameters.md#fit-parameter-correlation-parameter-unique-name-j) | parameter 2 |
    | [Correlation](../physics/parameters.md#fit-parameter-correlation-correlation) | correlation |
    | [File](../physics/parameters.md#fit-parameter-correlation-file-path) | file |

    <span class="ed-reference-anchor" id="names-pd-block">**[<span class="ed-reference-icon" data-reference-category="pd-block" aria-hidden="true">&#61897;</span> Report block](../physics/parameters.md#pd-block)**</span>

    | Parameter or field | GUI name |
    | --- | --- |
    | [Block](../physics/parameters.md#pd-block-id) | block |

=== "Edi"

    **[<span class="ed-reference-icon" data-reference-category="metadata" aria-hidden="true">&#61831;</span> Project](../physics/parameters.md#metadata)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Name](../physics/parameters.md#metadata-name) | <code>_metadata.name</code> |
    | [Title](../physics/parameters.md#metadata-title) | <code>_metadata.title</code> |
    | [Description](../physics/parameters.md#metadata-description) | <code>_metadata.description</code> |
    | [Authors](../physics/parameters.md#metadata-authors) | <code>_metadata.authors</code> |
    | [Location](../physics/parameters.md#metadata-path) | <code>_metadata.path</code> |
    | [Created](../physics/parameters.md#metadata-created) | <code>_metadata.created</code> |
    | [Last modified](../physics/parameters.md#metadata-last-modified) | <code>_metadata.last_modified</code> |
    | [Timestamp](../physics/parameters.md#metadata-timestamp) | <code>_metadata.timestamp</code> |

    **[<span class="ed-reference-icon" data-reference-category="su-format" aria-hidden="true">&#62030;</span> Standard uncertainties](../physics/parameters.md#su-format)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Uncertainty rounding rule](../physics/parameters.md#su-format-rule) | <code>_su_format.rule</code> |

    **[<span class="ed-reference-icon" data-reference-category="report" aria-hidden="true">&#61788;</span> Report](../physics/parameters.md#report)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [HTML](../physics/parameters.md#report-html) | <code>_report.html</code> |
    | [PDF](../physics/parameters.md#report-pdf) | <code>_report.pdf</code> |
    | [CIF](../physics/parameters.md#report-cif) | <code>_report.cif</code> |
    | [Embed chart libraries](../physics/parameters.md#report-html-offline) | <code>_report.html_offline</code> |
    | [Excluded](../physics/parameters.md#report-excluded) | <code>_report.excluded</code> |

    **[<span class="ed-reference-icon" data-reference-category="correlation-chart" aria-hidden="true">&#61450;</span> Correlation chart](../physics/parameters.md#correlation-chart)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Threshold](../physics/parameters.md#correlation-chart-threshold) | <code>_correlation_chart.threshold</code> |

    **[<span class="ed-reference-icon" data-reference-category="pattern-chart" aria-hidden="true">&#61953;</span> Pattern chart](../physics/parameters.md#pattern-chart)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [X-axis](../physics/parameters.md#pattern-chart-x-axis) | <code>_pattern_chart.x_axis</code> |

    **[<span class="ed-reference-icon" data-reference-category="calculator" aria-hidden="true">&#61932;</span> Calculator](../physics/parameters.md#calculator)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Calculator](../physics/parameters.md#calculator-type) | <code>_calculator.type</code> |

    **[<span class="ed-reference-icon" data-reference-category="minimizer" aria-hidden="true">&#62398;</span> Minimizer](../physics/parameters.md#minimizer)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Minimizer](../physics/parameters.md#minimizer-type) | <code>_minimizer.type</code> |
    | [Max iterations](../physics/parameters.md#minimizer-max-iterations) | <code>_minimizer.max_iterations</code> |
    | [Descent](../physics/parameters.md#minimizer-descent) | <code>_minimizer.descent</code> |
    | [Tolerance](../physics/parameters.md#minimizer-chi-square-tolerance) | <code>_minimizer.chi_square_tolerance</code> |

    **[<span class="ed-reference-icon" data-reference-category="fitting-mode" aria-hidden="true">&#61918;</span> Fitting mode](../physics/parameters.md#fitting-mode)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Fitting mode](../physics/parameters.md#fitting-mode-type) | <code>_fitting_mode.type</code> |

    **[<span class="ed-reference-icon" data-reference-category="refine-ls" aria-hidden="true">&#61636;</span> Fitted reflections](../physics/parameters.md#refine-ls)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Fitted-reflection threshold](../physics/parameters.md#refine-ls-threshold-sigma) | <code>_refine_ls.threshold_sigma</code> |

    **[<span class="ed-reference-icon" data-reference-category="alias" aria-hidden="true">&#61483;</span> Alias](../physics/parameters.md#alias)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Alias](../physics/parameters.md#alias-id) | <code>_alias.id</code> |
    | [Parameter](../physics/parameters.md#alias-parameter-unique-name) | <code>_alias.parameter_unique_name</code> |

    **[<span class="ed-reference-icon" data-reference-category="constraint" aria-hidden="true">&#62764;</span> Constraint](../physics/parameters.md#constraint)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Id](../physics/parameters.md#constraint-id) | <code>_constraint.id</code> |
    | [Expression](../physics/parameters.md#constraint-expression) | <code>_constraint.expression</code> |
    | [Enabled](../physics/parameters.md#constraint-enabled) | <code>_constraint.enabled</code> |

    **[<span class="ed-reference-icon" data-reference-category="joint-fit" aria-hidden="true">&#61633;</span> Joint-fit weights](../physics/parameters.md#joint-fit)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Weight](../physics/parameters.md#joint-fit-weight) | <code>_joint_fit.weight</code> |

    **[<span class="ed-reference-icon" data-reference-category="sequential-fit" aria-hidden="true">&#61643;</span> Sequential fit](../physics/parameters.md#sequential-fit)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Data directory](../physics/parameters.md#sequential-fit-data-dir) | <code>_sequential_fit.data_dir</code> |
    | [Files](../physics/parameters.md#sequential-fit-file-pattern) | <code>_sequential_fit.file_pattern</code> |
    | [Reverse](../physics/parameters.md#sequential-fit-reverse) | <code>_sequential_fit.reverse</code> |
    | [Template](../physics/parameters.md#sequential-fit-template-file) | <code>_sequential_fit.template_file</code> |

    **[<span class="ed-reference-icon" data-reference-category="sequential-fit-extract" aria-hidden="true">&#61616;</span> Scan extraction rule](../physics/parameters.md#sequential-fit-extract)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Id](../physics/parameters.md#sequential-fit-extract-id) | <code>_sequential_fit_extract.id</code> |
    | [Extracted value name](../physics/parameters.md#sequential-fit-extract-target) | <code>_sequential_fit_extract.target</code> |
    | [Pattern](../physics/parameters.md#sequential-fit-extract-pattern) | <code>_sequential_fit_extract.pattern</code> |
    | [Required](../physics/parameters.md#sequential-fit-extract-required) | <code>_sequential_fit_extract.required</code> |

    **[<span class="ed-reference-icon" data-reference-category="edi" aria-hidden="true">&#61897;</span> File header](../physics/parameters.md#edi)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Schema version](../physics/parameters.md#edi-schema-version) | <code>_edi.schema_version</code> |

    **[<span class="ed-reference-icon" data-reference-category="report-file" aria-hidden="true">&#61787;</span> Saved report](../physics/parameters.md#report-file)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Format](../physics/parameters.md#report-file-format) | <code>_report_file.format</code> |
    | [File](../physics/parameters.md#report-file-name) | <code>_report_file.name</code> |
    | [Saved](../physics/parameters.md#report-file-saved) | <code>_report_file.saved</code> |
    | [Project saved](../physics/parameters.md#report-file-project-last-modified) | <code>_report_file.project_last_modified</code> |
    | [Digest](../physics/parameters.md#report-file-digest) | <code>_report_file.digest</code> |

    **[<span class="ed-reference-icon" data-reference-category="fit-parameter" aria-hidden="true">&#61914;</span> Fit start value](../physics/parameters.md#fit-parameter)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Parameter](../physics/parameters.md#fit-parameter-id) | <code>_fit_parameter.id</code> |
    | [Start value](../physics/parameters.md#fit-parameter-start-value) | <code>_fit_parameter.start_value</code> |
    | [Start error](../physics/parameters.md#fit-parameter-start-uncertainty) | <code>_fit_parameter.start_uncertainty</code> |
    | [Start tied](../physics/parameters.md#fit-parameter-start-tied) | <code>_fit_parameter.start_tied</code> |

    **[<span class="ed-reference-icon" data-reference-category="fit-result" aria-hidden="true">&#61528;</span> Fit result](../physics/parameters.md#fit-result)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Kind](../physics/parameters.md#fit-result-result-kind) | <code>_fit_result.result_kind</code> |
    | [Success](../physics/parameters.md#fit-result-success) | <code>_fit_result.success</code> |
    | [Message](../physics/parameters.md#fit-result-message) | <code>_fit_result.message</code> |
    | [Iterations](../physics/parameters.md#fit-result-iterations) | <code>_fit_result.iterations</code> |
    | [Time](../physics/parameters.md#fit-result-fitting-time) | <code>_fit_result.fitting_time</code> |
    | [Reduced χ²](../physics/parameters.md#fit-result-reduced-chi-square) | <code>_fit_result.reduced_chi_square</code> |
    | [Objective](../physics/parameters.md#fit-result-objective-name) | <code>_fit_result.objective_name</code> |
    | [Objective value](../physics/parameters.md#fit-result-objective-value) | <code>_fit_result.objective_value</code> |
    | [Number of fitted observations](../physics/parameters.md#fit-result-n-data-points) | <code>_fit_result.n_data_points</code> |
    | [Parameters](../physics/parameters.md#fit-result-n-parameters) | <code>_fit_result.n_parameters</code> |
    | [Free parameters](../physics/parameters.md#fit-result-n-free-parameters) | <code>_fit_result.n_free_parameters</code> |
    | [Degrees of freedom](../physics/parameters.md#fit-result-degrees-of-freedom) | <code>_fit_result.degrees_of_freedom</code> |
    | [Covariance](../physics/parameters.md#fit-result-covariance-available) | <code>_fit_result.covariance_available</code> |
    | [Exit reason](../physics/parameters.md#fit-result-exit-reason) | <code>_fit_result.exit_reason</code> |
    | [Rwp](../physics/parameters.md#fit-result-prof-wr-factor) | <code>_fit_result.prof_wr_factor</code> |
    | [Rp](../physics/parameters.md#fit-result-prof-r-factor) | <code>_fit_result.prof_r_factor</code> |
    | [Rexp](../physics/parameters.md#fit-result-prof-wr-expected) | <code>_fit_result.prof_wr_expected</code> |
    | [CRp](../physics/parameters.md#fit-result-prof-cr-factor) | <code>_fit_result.prof_cr_factor</code> |
    | [CRwp](../physics/parameters.md#fit-result-prof-cwr-factor) | <code>_fit_result.prof_cwr_factor</code> |
    | [Profile](../physics/parameters.md#fit-result-profile-function) | <code>_fit_result.profile_function</code> |
    | [Background](../physics/parameters.md#fit-result-background-function) | <code>_fit_result.background_function</code> |
    | [Descent](../physics/parameters.md#fit-result-descent) | <code>_fit_result.descent</code> |

    **[<span class="ed-reference-icon" data-reference-category="fit-result-bank" aria-hidden="true">&#61452;</span> Experiment fit result](../physics/parameters.md#fit-result-bank)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Number of fitted observations](../physics/parameters.md#fit-result-bank-n-data-points) | <code>_fit_result_bank.n_data_points</code> |
    | [Rp](../physics/parameters.md#fit-result-bank-prof-r-factor) | <code>_fit_result_bank.prof_r_factor</code> |
    | [Rwp](../physics/parameters.md#fit-result-bank-prof-wr-factor) | <code>_fit_result_bank.prof_wr_factor</code> |
    | [Rexp](../physics/parameters.md#fit-result-bank-prof-wr-expected) | <code>_fit_result_bank.prof_wr_expected</code> |
    | [CRp](../physics/parameters.md#fit-result-bank-prof-cr-factor) | <code>_fit_result_bank.prof_cr_factor</code> |
    | [CRwp](../physics/parameters.md#fit-result-bank-prof-cwr-factor) | <code>_fit_result_bank.prof_cwr_factor</code> |
    | [Reduced χ²](../physics/parameters.md#fit-result-bank-chi-square) | <code>_fit_result_bank.chi_square</code> |

    **[<span class="ed-reference-icon" data-reference-category="fit-result-phase" aria-hidden="true">&#61452;</span> Structure fit result](../physics/parameters.md#fit-result-phase)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [R Bragg](../physics/parameters.md#fit-result-phase-bragg-r-factor) | <code>_fit_result_phase.bragg_r_factor</code> |
    | [R F](../physics/parameters.md#fit-result-phase-f-r-factor) | <code>_fit_result_phase.f_r_factor</code> |

    **[<span class="ed-reference-icon" data-reference-category="fit-parameter-correlation" aria-hidden="true">&#61449;</span> Correlation](../physics/parameters.md#fit-parameter-correlation)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Id](../physics/parameters.md#fit-parameter-correlation-id) | <code>_fit_parameter_correlation.id</code> |
    | [Source](../physics/parameters.md#fit-parameter-correlation-source-kind) | <code>_fit_parameter_correlation.source_kind</code> |
    | [Parameter 1](../physics/parameters.md#fit-parameter-correlation-parameter-unique-name-i) | <code>_fit_parameter_correlation.parameter_unique_name_i</code> |
    | [Parameter 2](../physics/parameters.md#fit-parameter-correlation-parameter-unique-name-j) | <code>_fit_parameter_correlation.parameter_unique_name_j</code> |
    | [Correlation](../physics/parameters.md#fit-parameter-correlation-correlation) | <code>_fit_parameter_correlation.correlation</code> |
    | [File](../physics/parameters.md#fit-parameter-correlation-file-path) | <code>_fit_parameter_correlation.file_path</code> |

    **[<span class="ed-reference-icon" data-reference-category="pd-block" aria-hidden="true">&#61897;</span> Report block](../physics/parameters.md#pd-block)**

    | Parameter or field | Edi name |
    | --- | --- |
    | [Block](../physics/parameters.md#pd-block-id) | <code>_pd_block.id</code> |

=== "Python"

    **[<span class="ed-reference-icon" data-reference-category="metadata" aria-hidden="true">&#61831;</span> Project](../physics/parameters.md#metadata)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Name](../physics/parameters.md#metadata-name) | <code>project.metadata.name</code> |
    | [Title](../physics/parameters.md#metadata-title) | <code>project.metadata.title</code> |
    | [Description](../physics/parameters.md#metadata-description) | <code>project.metadata.description</code> |
    | [Authors](../physics/parameters.md#metadata-authors) | <code>project.metadata.authors</code> |
    | [Location](../physics/parameters.md#metadata-path) | <code>project.metadata.path</code> |
    | [Created](../physics/parameters.md#metadata-created) | <code>project.metadata.created</code> |
    | [Last modified](../physics/parameters.md#metadata-last-modified) | <code>project.metadata.last_modified</code> |
    | [Timestamp](../physics/parameters.md#metadata-timestamp) | <code>project.metadata.timestamp</code> |

    **[<span class="ed-reference-icon" data-reference-category="su-format" aria-hidden="true">&#62030;</span> Standard uncertainties](../physics/parameters.md#su-format)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Uncertainty rounding rule](../physics/parameters.md#su-format-rule) | <code>project.su_rule</code> |

    **[<span class="ed-reference-icon" data-reference-category="report" aria-hidden="true">&#61788;</span> Report](../physics/parameters.md#report)**

    | Parameter or field | Python name |
    | --- | --- |
    | [HTML](../physics/parameters.md#report-html) | — |
    | [PDF](../physics/parameters.md#report-pdf) | — |
    | [CIF](../physics/parameters.md#report-cif) | — |
    | [Embed chart libraries](../physics/parameters.md#report-html-offline) | — |
    | [Excluded](../physics/parameters.md#report-excluded) | — |

    **[<span class="ed-reference-icon" data-reference-category="correlation-chart" aria-hidden="true">&#61450;</span> Correlation chart](../physics/parameters.md#correlation-chart)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Threshold](../physics/parameters.md#correlation-chart-threshold) | — |

    **[<span class="ed-reference-icon" data-reference-category="pattern-chart" aria-hidden="true">&#61953;</span> Pattern chart](../physics/parameters.md#pattern-chart)**

    | Parameter or field | Python name |
    | --- | --- |
    | [X-axis](../physics/parameters.md#pattern-chart-x-axis) | — |

    **[<span class="ed-reference-icon" data-reference-category="calculator" aria-hidden="true">&#61932;</span> Calculator](../physics/parameters.md#calculator)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Calculator](../physics/parameters.md#calculator-type) | — |

    **[<span class="ed-reference-icon" data-reference-category="minimizer" aria-hidden="true">&#62398;</span> Minimizer](../physics/parameters.md#minimizer)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Minimizer](../physics/parameters.md#minimizer-type) | — |
    | [Max iterations](../physics/parameters.md#minimizer-max-iterations) | — |
    | [Descent](../physics/parameters.md#minimizer-descent) | <code>project.descent</code> |
    | [Tolerance](../physics/parameters.md#minimizer-chi-square-tolerance) | — |

    **[<span class="ed-reference-icon" data-reference-category="fitting-mode" aria-hidden="true">&#61918;</span> Fitting mode](../physics/parameters.md#fitting-mode)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Fitting mode](../physics/parameters.md#fitting-mode-type) | <code>project.fitting_mode</code> |

    **[<span class="ed-reference-icon" data-reference-category="refine-ls" aria-hidden="true">&#61636;</span> Fitted reflections](../physics/parameters.md#refine-ls)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Fitted-reflection threshold](../physics/parameters.md#refine-ls-threshold-sigma) | — |

    **[<span class="ed-reference-icon" data-reference-category="alias" aria-hidden="true">&#61483;</span> Alias](../physics/parameters.md#alias)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Alias](../physics/parameters.md#alias-id) | — |
    | [Parameter](../physics/parameters.md#alias-parameter-unique-name) | — |

    **[<span class="ed-reference-icon" data-reference-category="constraint" aria-hidden="true">&#62764;</span> Constraint](../physics/parameters.md#constraint)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Id](../physics/parameters.md#constraint-id) | — |
    | [Expression](../physics/parameters.md#constraint-expression) | — |
    | [Enabled](../physics/parameters.md#constraint-enabled) | — |

    **[<span class="ed-reference-icon" data-reference-category="joint-fit" aria-hidden="true">&#61633;</span> Joint-fit weights](../physics/parameters.md#joint-fit)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Weight](../physics/parameters.md#joint-fit-weight) | <code>project.experiments[0].dataset_weight</code> |

    **[<span class="ed-reference-icon" data-reference-category="sequential-fit" aria-hidden="true">&#61643;</span> Sequential fit](../physics/parameters.md#sequential-fit)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Data directory](../physics/parameters.md#sequential-fit-data-dir) | — |
    | [Files](../physics/parameters.md#sequential-fit-file-pattern) | — |
    | [Reverse](../physics/parameters.md#sequential-fit-reverse) | — |
    | [Template](../physics/parameters.md#sequential-fit-template-file) | — |

    **[<span class="ed-reference-icon" data-reference-category="sequential-fit-extract" aria-hidden="true">&#61616;</span> Scan extraction rule](../physics/parameters.md#sequential-fit-extract)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Id](../physics/parameters.md#sequential-fit-extract-id) | — |
    | [Extracted value name](../physics/parameters.md#sequential-fit-extract-target) | — |
    | [Pattern](../physics/parameters.md#sequential-fit-extract-pattern) | — |
    | [Required](../physics/parameters.md#sequential-fit-extract-required) | — |

    **[<span class="ed-reference-icon" data-reference-category="edi" aria-hidden="true">&#61897;</span> File header](../physics/parameters.md#edi)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Schema version](../physics/parameters.md#edi-schema-version) | — |

    **[<span class="ed-reference-icon" data-reference-category="report-file" aria-hidden="true">&#61787;</span> Saved report](../physics/parameters.md#report-file)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Format](../physics/parameters.md#report-file-format) | — |
    | [File](../physics/parameters.md#report-file-name) | — |
    | [Saved](../physics/parameters.md#report-file-saved) | — |
    | [Project saved](../physics/parameters.md#report-file-project-last-modified) | — |
    | [Digest](../physics/parameters.md#report-file-digest) | — |

    **[<span class="ed-reference-icon" data-reference-category="fit-parameter" aria-hidden="true">&#61914;</span> Fit start value](../physics/parameters.md#fit-parameter)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Parameter](../physics/parameters.md#fit-parameter-id) | — |
    | [Start value](../physics/parameters.md#fit-parameter-start-value) | — |
    | [Start error](../physics/parameters.md#fit-parameter-start-uncertainty) | — |
    | [Start tied](../physics/parameters.md#fit-parameter-start-tied) | — |

    **[<span class="ed-reference-icon" data-reference-category="fit-result" aria-hidden="true">&#61528;</span> Fit result](../physics/parameters.md#fit-result)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Kind](../physics/parameters.md#fit-result-result-kind) | — |
    | [Success](../physics/parameters.md#fit-result-success) | — |
    | [Message](../physics/parameters.md#fit-result-message) | — |
    | [Iterations](../physics/parameters.md#fit-result-iterations) | — |
    | [Time](../physics/parameters.md#fit-result-fitting-time) | — |
    | [Reduced χ²](../physics/parameters.md#fit-result-reduced-chi-square) | — |
    | [Objective](../physics/parameters.md#fit-result-objective-name) | — |
    | [Objective value](../physics/parameters.md#fit-result-objective-value) | — |
    | [Number of fitted observations](../physics/parameters.md#fit-result-n-data-points) | — |
    | [Parameters](../physics/parameters.md#fit-result-n-parameters) | — |
    | [Free parameters](../physics/parameters.md#fit-result-n-free-parameters) | — |
    | [Degrees of freedom](../physics/parameters.md#fit-result-degrees-of-freedom) | — |
    | [Covariance](../physics/parameters.md#fit-result-covariance-available) | — |
    | [Exit reason](../physics/parameters.md#fit-result-exit-reason) | — |
    | [Rwp](../physics/parameters.md#fit-result-prof-wr-factor) | — |
    | [Rp](../physics/parameters.md#fit-result-prof-r-factor) | — |
    | [Rexp](../physics/parameters.md#fit-result-prof-wr-expected) | — |
    | [CRp](../physics/parameters.md#fit-result-prof-cr-factor) | — |
    | [CRwp](../physics/parameters.md#fit-result-prof-cwr-factor) | — |
    | [Profile](../physics/parameters.md#fit-result-profile-function) | — |
    | [Background](../physics/parameters.md#fit-result-background-function) | — |
    | [Descent](../physics/parameters.md#fit-result-descent) | — |

    **[<span class="ed-reference-icon" data-reference-category="fit-result-bank" aria-hidden="true">&#61452;</span> Experiment fit result](../physics/parameters.md#fit-result-bank)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Number of fitted observations](../physics/parameters.md#fit-result-bank-n-data-points) | — |
    | [Rp](../physics/parameters.md#fit-result-bank-prof-r-factor) | — |
    | [Rwp](../physics/parameters.md#fit-result-bank-prof-wr-factor) | — |
    | [Rexp](../physics/parameters.md#fit-result-bank-prof-wr-expected) | — |
    | [CRp](../physics/parameters.md#fit-result-bank-prof-cr-factor) | — |
    | [CRwp](../physics/parameters.md#fit-result-bank-prof-cwr-factor) | — |
    | [Reduced χ²](../physics/parameters.md#fit-result-bank-chi-square) | — |

    **[<span class="ed-reference-icon" data-reference-category="fit-result-phase" aria-hidden="true">&#61452;</span> Structure fit result](../physics/parameters.md#fit-result-phase)**

    | Parameter or field | Python name |
    | --- | --- |
    | [R Bragg](../physics/parameters.md#fit-result-phase-bragg-r-factor) | — |
    | [R F](../physics/parameters.md#fit-result-phase-f-r-factor) | — |

    **[<span class="ed-reference-icon" data-reference-category="fit-parameter-correlation" aria-hidden="true">&#61449;</span> Correlation](../physics/parameters.md#fit-parameter-correlation)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Id](../physics/parameters.md#fit-parameter-correlation-id) | — |
    | [Source](../physics/parameters.md#fit-parameter-correlation-source-kind) | — |
    | [Parameter 1](../physics/parameters.md#fit-parameter-correlation-parameter-unique-name-i) | — |
    | [Parameter 2](../physics/parameters.md#fit-parameter-correlation-parameter-unique-name-j) | — |
    | [Correlation](../physics/parameters.md#fit-parameter-correlation-correlation) | — |
    | [File](../physics/parameters.md#fit-parameter-correlation-file-path) | — |

    **[<span class="ed-reference-icon" data-reference-category="pd-block" aria-hidden="true">&#61897;</span> Report block](../physics/parameters.md#pd-block)**

    | Parameter or field | Python name |
    | --- | --- |
    | [Block](../physics/parameters.md#pd-block-id) | — |

=== "CIF"

    **[<span class="ed-reference-icon" data-reference-category="metadata" aria-hidden="true">&#61831;</span> Project](../physics/parameters.md#metadata)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Name](../physics/parameters.md#metadata-name) | <code>_edi_metadata.name</code><details><summary>Accepted aliases</summary><code>_project.id</code></details> |
    | [Title](../physics/parameters.md#metadata-title) | <code>_edi_metadata.title</code><details><summary>Accepted aliases</summary><code>_project.title</code></details> |
    | [Description](../physics/parameters.md#metadata-description) | <code>_edi_metadata.description</code><details><summary>Accepted aliases</summary><code>_project.description</code></details> |
    | [Authors](../physics/parameters.md#metadata-authors) | <code>_edi_metadata.authors</code> |
    | [Location](../physics/parameters.md#metadata-path) | <code>_edi_metadata.path</code> |
    | [Created](../physics/parameters.md#metadata-created) | <code>_edi_metadata.created</code><details><summary>Accepted aliases</summary><code>_project.created</code></details> |
    | [Last modified](../physics/parameters.md#metadata-last-modified) | <code>_edi_metadata.last_modified</code><details><summary>Accepted aliases</summary><code>_project.last_modified</code></details> |
    | [Timestamp](../physics/parameters.md#metadata-timestamp) | <code>_edi_metadata.timestamp</code><details><summary>Accepted aliases</summary><code>_easydiffraction_project.timestamp</code><br><code>_software.timestamp</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="su-format" aria-hidden="true">&#62030;</span> Standard uncertainties](../physics/parameters.md#su-format)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Uncertainty rounding rule](../physics/parameters.md#su-format-rule) | <code>_edi_su_format.rule</code> |

    **[<span class="ed-reference-icon" data-reference-category="report" aria-hidden="true">&#61788;</span> Report](../physics/parameters.md#report)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [HTML](../physics/parameters.md#report-html) | <code>_edi_report.html</code><details><summary>Accepted aliases</summary><code>_report.html</code></details> |
    | [PDF](../physics/parameters.md#report-pdf) | <code>_edi_report.pdf</code><details><summary>Accepted aliases</summary><code>_report.pdf</code></details> |
    | [CIF](../physics/parameters.md#report-cif) | <code>_edi_report.cif</code><details><summary>Accepted aliases</summary><code>_report.cif</code></details> |
    | [Embed chart libraries](../physics/parameters.md#report-html-offline) | <code>_edi_report.html_offline</code><details><summary>Accepted aliases</summary><code>_report.html_offline</code></details> |
    | [Excluded](../physics/parameters.md#report-excluded) | <code>_edi_report.excluded</code> |

    **[<span class="ed-reference-icon" data-reference-category="correlation-chart" aria-hidden="true">&#61450;</span> Correlation chart](../physics/parameters.md#correlation-chart)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Threshold](../physics/parameters.md#correlation-chart-threshold) | <code>_edi_correlation_chart.threshold</code> |

    **[<span class="ed-reference-icon" data-reference-category="pattern-chart" aria-hidden="true">&#61953;</span> Pattern chart](../physics/parameters.md#pattern-chart)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [X-axis](../physics/parameters.md#pattern-chart-x-axis) | <code>_edi_pattern_chart.x_axis</code> |

    **[<span class="ed-reference-icon" data-reference-category="calculator" aria-hidden="true">&#61932;</span> Calculator](../physics/parameters.md#calculator)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Calculator](../physics/parameters.md#calculator-type) | <code>_edi_calculator.type</code><details><summary>Accepted aliases</summary><code>_easydiffraction_calculator.type</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="minimizer" aria-hidden="true">&#62398;</span> Minimizer](../physics/parameters.md#minimizer)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Minimizer](../physics/parameters.md#minimizer-type) | <code>_edi_minimizer.type</code><details><summary>Accepted aliases</summary><code>_easydiffraction_minimizer.type</code></details> |
    | [Max iterations](../physics/parameters.md#minimizer-max-iterations) | <code>_edi_minimizer.max_iterations</code><details><summary>Accepted aliases</summary><code>_easydiffraction_minimizer.max_iterations</code></details> |
    | [Descent](../physics/parameters.md#minimizer-descent) | <code>_edi_minimizer.descent</code> |
    | [Tolerance](../physics/parameters.md#minimizer-chi-square-tolerance) | <code>_edi_minimizer.chi_square_tolerance</code> |

    **[<span class="ed-reference-icon" data-reference-category="fitting-mode" aria-hidden="true">&#61918;</span> Fitting mode](../physics/parameters.md#fitting-mode)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Fitting mode](../physics/parameters.md#fitting-mode-type) | <code>_edi_fitting_mode.type</code><details><summary>Accepted aliases</summary><code>_easydiffraction_fitting_mode.type</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="refine-ls" aria-hidden="true">&#61636;</span> Fitted reflections](../physics/parameters.md#refine-ls)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Fitted-reflection threshold](../physics/parameters.md#refine-ls-threshold-sigma) | <code>_edi_refine_ls.threshold_sigma</code> |

    **[<span class="ed-reference-icon" data-reference-category="alias" aria-hidden="true">&#61483;</span> Alias](../physics/parameters.md#alias)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Alias](../physics/parameters.md#alias-id) | <code>_edi_alias.id</code><details><summary>Accepted aliases</summary><code>_easydiffraction_alias.id</code><br><code>_alias.label</code></details> |
    | [Parameter](../physics/parameters.md#alias-parameter-unique-name) | <code>_edi_alias.parameter_unique_name</code><details><summary>Accepted aliases</summary><code>_easydiffraction_alias.parameter_unique_name</code><br><code>_alias.param_unique_name</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="constraint" aria-hidden="true">&#62764;</span> Constraint](../physics/parameters.md#constraint)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Id](../physics/parameters.md#constraint-id) | <code>_edi_constraint.id</code><details><summary>Accepted aliases</summary><code>_easydiffraction_constraint.id</code></details> |
    | [Expression](../physics/parameters.md#constraint-expression) | <code>_edi_constraint.expression</code><details><summary>Accepted aliases</summary><code>_easydiffraction_constraint.expression</code></details> |
    | [Enabled](../physics/parameters.md#constraint-enabled) | <code>_edi_constraint.enabled</code> |

    **[<span class="ed-reference-icon" data-reference-category="joint-fit" aria-hidden="true">&#61633;</span> Joint-fit weights](../physics/parameters.md#joint-fit)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Weight](../physics/parameters.md#joint-fit-weight) | <code>_edi_joint_fit.weight</code><details><summary>Accepted aliases</summary><code>_easydiffraction_joint_fit.weight</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="sequential-fit" aria-hidden="true">&#61643;</span> Sequential fit](../physics/parameters.md#sequential-fit)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Data directory](../physics/parameters.md#sequential-fit-data-dir) | <code>_edi_sequential_fit.data_dir</code><details><summary>Accepted aliases</summary><code>_easydiffraction_sequential_fit.data_dir</code></details> |
    | [Files](../physics/parameters.md#sequential-fit-file-pattern) | <code>_edi_sequential_fit.file_pattern</code><details><summary>Accepted aliases</summary><code>_easydiffraction_sequential_fit.file_pattern</code></details> |
    | [Reverse](../physics/parameters.md#sequential-fit-reverse) | <code>_edi_sequential_fit.reverse</code><details><summary>Accepted aliases</summary><code>_easydiffraction_sequential_fit.reverse</code></details> |
    | [Template](../physics/parameters.md#sequential-fit-template-file) | <code>_edi_sequential_fit.template_file</code> |

    **[<span class="ed-reference-icon" data-reference-category="sequential-fit-extract" aria-hidden="true">&#61616;</span> Scan extraction rule](../physics/parameters.md#sequential-fit-extract)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Id](../physics/parameters.md#sequential-fit-extract-id) | <code>_edi_sequential_fit_extract.id</code><details><summary>Accepted aliases</summary><code>_easydiffraction_sequential_fit_extract.id</code></details> |
    | [Extracted value name](../physics/parameters.md#sequential-fit-extract-target) | <code>_edi_sequential_fit_extract.target</code><details><summary>Accepted aliases</summary><code>_easydiffraction_sequential_fit_extract.target</code></details> |
    | [Pattern](../physics/parameters.md#sequential-fit-extract-pattern) | <code>_edi_sequential_fit_extract.pattern</code><details><summary>Accepted aliases</summary><code>_easydiffraction_sequential_fit_extract.pattern</code></details> |
    | [Required](../physics/parameters.md#sequential-fit-extract-required) | <code>_edi_sequential_fit_extract.required</code><details><summary>Accepted aliases</summary><code>_easydiffraction_sequential_fit_extract.required</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="edi" aria-hidden="true">&#61897;</span> File header](../physics/parameters.md#edi)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Schema version](../physics/parameters.md#edi-schema-version) | <code>_edi_edi.schema_version</code> |

    **[<span class="ed-reference-icon" data-reference-category="report-file" aria-hidden="true">&#61787;</span> Saved report](../physics/parameters.md#report-file)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Format](../physics/parameters.md#report-file-format) | <code>_edi_report_file.format</code> |
    | [File](../physics/parameters.md#report-file-name) | <code>_edi_report_file.name</code> |
    | [Saved](../physics/parameters.md#report-file-saved) | <code>_edi_report_file.saved</code> |
    | [Project saved](../physics/parameters.md#report-file-project-last-modified) | <code>_edi_report_file.project_last_modified</code> |
    | [Digest](../physics/parameters.md#report-file-digest) | <code>_edi_report_file.digest</code> |

    **[<span class="ed-reference-icon" data-reference-category="fit-parameter" aria-hidden="true">&#61914;</span> Fit start value](../physics/parameters.md#fit-parameter)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Parameter](../physics/parameters.md#fit-parameter-id) | <code>_edi_fit_parameter.id</code> |
    | [Start value](../physics/parameters.md#fit-parameter-start-value) | <code>_edi_fit_parameter.start_value</code><details><summary>Accepted aliases</summary><code>_fit_parameter.start_value</code></details> |
    | [Start error](../physics/parameters.md#fit-parameter-start-uncertainty) | <code>_edi_fit_parameter.start_uncertainty</code><details><summary>Accepted aliases</summary><code>_fit_parameter.start_uncertainty</code></details> |
    | [Start tied](../physics/parameters.md#fit-parameter-start-tied) | <code>_edi_fit_parameter.start_tied</code> |

    **[<span class="ed-reference-icon" data-reference-category="fit-result" aria-hidden="true">&#61528;</span> Fit result](../physics/parameters.md#fit-result)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Kind](../physics/parameters.md#fit-result-result-kind) | <code>_edi_fit_result.result_kind</code><details><summary>Accepted aliases</summary><code>_fit_result.result_kind</code></details> |
    | [Success](../physics/parameters.md#fit-result-success) | <code>_edi_fit_result.success</code><details><summary>Accepted aliases</summary><code>_fit_result.success</code></details> |
    | [Message](../physics/parameters.md#fit-result-message) | <code>_edi_fit_result.message</code><details><summary>Accepted aliases</summary><code>_fit_result.message</code></details> |
    | [Iterations](../physics/parameters.md#fit-result-iterations) | <code>_edi_fit_result.iterations</code><details><summary>Accepted aliases</summary><code>_fit_result.iterations</code></details> |
    | [Time](../physics/parameters.md#fit-result-fitting-time) | <code>_edi_fit_result.fitting_time</code><details><summary>Accepted aliases</summary><code>_fit_result.fitting_time</code></details> |
    | [Reduced χ²](../physics/parameters.md#fit-result-reduced-chi-square) | <code>_edi_fit_result.reduced_chi_square</code><details><summary>Accepted aliases</summary><code>_fit_result.reduced_chi_square</code></details> |
    | [Objective](../physics/parameters.md#fit-result-objective-name) | <code>_edi_fit_result.objective_name</code><details><summary>Accepted aliases</summary><code>_fit_result.objective_name</code></details> |
    | [Objective value](../physics/parameters.md#fit-result-objective-value) | <code>_edi_fit_result.objective_value</code><details><summary>Accepted aliases</summary><code>_fit_result.objective_value</code></details> |
    | [Number of fitted observations](../physics/parameters.md#fit-result-n-data-points) | <code>_edi_fit_result.n_data_points</code><details><summary>Accepted aliases</summary><code>_fit_result.n_data_points</code></details> |
    | [Parameters](../physics/parameters.md#fit-result-n-parameters) | <code>_edi_fit_result.n_parameters</code><details><summary>Accepted aliases</summary><code>_fit_result.n_parameters</code></details> |
    | [Free parameters](../physics/parameters.md#fit-result-n-free-parameters) | <code>_edi_fit_result.n_free_parameters</code><details><summary>Accepted aliases</summary><code>_fit_result.n_free_parameters</code></details> |
    | [Degrees of freedom](../physics/parameters.md#fit-result-degrees-of-freedom) | <code>_edi_fit_result.degrees_of_freedom</code><details><summary>Accepted aliases</summary><code>_fit_result.degrees_of_freedom</code></details> |
    | [Covariance](../physics/parameters.md#fit-result-covariance-available) | <code>_edi_fit_result.covariance_available</code><details><summary>Accepted aliases</summary><code>_fit_result.covariance_available</code></details> |
    | [Exit reason](../physics/parameters.md#fit-result-exit-reason) | <code>_edi_fit_result.exit_reason</code><details><summary>Accepted aliases</summary><code>_fit_result.exit_reason</code></details> |
    | [Rwp](../physics/parameters.md#fit-result-prof-wr-factor) | <code>_edi_fit_result.prof_wr_factor</code><details><summary>Accepted aliases</summary><code>_fit_result.prof_wR_factor</code></details> |
    | [Rp](../physics/parameters.md#fit-result-prof-r-factor) | <code>_edi_fit_result.prof_r_factor</code><details><summary>Accepted aliases</summary><code>_fit_result.prof_R_factor</code></details> |
    | [Rexp](../physics/parameters.md#fit-result-prof-wr-expected) | <code>_edi_fit_result.prof_wr_expected</code><details><summary>Accepted aliases</summary><code>_fit_result.prof_wR_expected</code></details> |
    | [CRp](../physics/parameters.md#fit-result-prof-cr-factor) | <code>_edi_fit_result.prof_cr_factor</code> |
    | [CRwp](../physics/parameters.md#fit-result-prof-cwr-factor) | <code>_edi_fit_result.prof_cwr_factor</code> |
    | [Profile](../physics/parameters.md#fit-result-profile-function) | <code>_edi_fit_result.profile_function</code><details><summary>Accepted aliases</summary><code>_fit_result.profile_function</code></details> |
    | [Background](../physics/parameters.md#fit-result-background-function) | <code>_edi_fit_result.background_function</code><details><summary>Accepted aliases</summary><code>_fit_result.background_function</code></details> |
    | [Descent](../physics/parameters.md#fit-result-descent) | <code>_edi_fit_result.descent</code> |

    **[<span class="ed-reference-icon" data-reference-category="fit-result-bank" aria-hidden="true">&#61452;</span> Experiment fit result](../physics/parameters.md#fit-result-bank)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Number of fitted observations](../physics/parameters.md#fit-result-bank-n-data-points) | <code>_edi_fit_result_bank.n_data_points</code> |
    | [Rp](../physics/parameters.md#fit-result-bank-prof-r-factor) | <code>_pd_proc_ls.prof_R_factor</code><details><summary>Accepted aliases</summary><code>_pd_proc_ls_prof_R_factor</code></details> |
    | [Rwp](../physics/parameters.md#fit-result-bank-prof-wr-factor) | <code>_pd_proc_ls.prof_wR_factor</code><details><summary>Accepted aliases</summary><code>_pd_proc_ls_prof_wR_factor</code></details> |
    | [Rexp](../physics/parameters.md#fit-result-bank-prof-wr-expected) | <code>_pd_proc_ls.prof_wR_expected</code><details><summary>Accepted aliases</summary><code>_pd_proc_ls_prof_wR_expected</code></details> |
    | [CRp](../physics/parameters.md#fit-result-bank-prof-cr-factor) | <code>_edi_fit_result_bank.prof_cr_factor</code> |
    | [CRwp](../physics/parameters.md#fit-result-bank-prof-cwr-factor) | <code>_edi_fit_result_bank.prof_cwr_factor</code> |
    | [Reduced χ²](../physics/parameters.md#fit-result-bank-chi-square) | <code>_edi_fit_result_bank.chi_square</code> |

    **[<span class="ed-reference-icon" data-reference-category="fit-result-phase" aria-hidden="true">&#61452;</span> Structure fit result](../physics/parameters.md#fit-result-phase)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [R Bragg](../physics/parameters.md#fit-result-phase-bragg-r-factor) | <code>_refine_ls.R_I_factor</code><details><summary>Accepted aliases</summary><code>_refine_ls_R_I_factor</code><br><code>_refine.ls_R_I_factor_obs</code></details> |
    | [R F](../physics/parameters.md#fit-result-phase-f-r-factor) | <code>_refine_ls.R_factor_all</code><details><summary>Accepted aliases</summary><code>_refine_ls_R_factor_all</code><br><code>_refine.ls_R_factor_all</code></details> |

    **[<span class="ed-reference-icon" data-reference-category="fit-parameter-correlation" aria-hidden="true">&#61449;</span> Correlation](../physics/parameters.md#fit-parameter-correlation)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Id](../physics/parameters.md#fit-parameter-correlation-id) | <code>_edi_fit_parameter_correlation.id</code><details><summary>Accepted aliases</summary><code>_fit_parameter_correlation.id</code></details> |
    | [Source](../physics/parameters.md#fit-parameter-correlation-source-kind) | <code>_edi_fit_parameter_correlation.source_kind</code><details><summary>Accepted aliases</summary><code>_fit_parameter_correlation.source_kind</code></details> |
    | [Parameter 1](../physics/parameters.md#fit-parameter-correlation-parameter-unique-name-i) | <code>_edi_fit_parameter_correlation.parameter_unique_name_i</code><details><summary>Accepted aliases</summary><code>_fit_parameter_correlation.param_unique_name_i</code></details> |
    | [Parameter 2](../physics/parameters.md#fit-parameter-correlation-parameter-unique-name-j) | <code>_edi_fit_parameter_correlation.parameter_unique_name_j</code><details><summary>Accepted aliases</summary><code>_fit_parameter_correlation.param_unique_name_j</code></details> |
    | [Correlation](../physics/parameters.md#fit-parameter-correlation-correlation) | <code>_edi_fit_parameter_correlation.correlation</code><details><summary>Accepted aliases</summary><code>_fit_parameter_correlation.correlation</code></details> |
    | [File](../physics/parameters.md#fit-parameter-correlation-file-path) | <code>_edi_fit_parameter_correlation.file_path</code> |

    **[<span class="ed-reference-icon" data-reference-category="pd-block" aria-hidden="true">&#61897;</span> Report block](../physics/parameters.md#pd-block)**

    | Parameter or field | CIF name |
    | --- | --- |
    | [Block](../physics/parameters.md#pd-block-id) | <code>_pd_block.id</code><details><summary>Accepted aliases</summary><code>_pd_block_id</code></details> |

<!-- /parameter-names -->
