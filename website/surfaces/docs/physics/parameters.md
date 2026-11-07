---
icon: fa5/th-list
template: physics.html
---

# Parameter explanations {#parameter-and-category-reference}

Read what each parameter describes, its units and the models that use it. Applicability depends on the experiment and selected model. [Compare names across interfaces](../user-guide/parameters.md#parameter-names).

## <span class="ed-reference-icon" data-reference-category="space-group" aria-hidden="true">&#63423;</span> Space group {#space-group}

The structure&#x27;s space group.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="space-group-name-h-m">

### Hermann-Mauguin symbol {#space-group-name-h-m}

The Hermann-Mauguin symbol of the space group.

[Names across interfaces](../user-guide/parameters.md#names-space-group)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="space-group-coord-system-code">

### Space-group setting {#space-group-coord-system-code}

The setting of the space group, such as an origin choice or axes.

[Names across interfaces](../user-guide/parameters.md#names-space-group)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="space-group-it-number">

### Space-group number {#space-group-it-number}

The number of the space group in International Tables, from 1 to 230.

[Names across interfaces](../user-guide/parameters.md#names-space-group)

</section>

## <span class="ed-reference-icon" data-reference-category="cell" aria-hidden="true">&#61874;</span> Cell {#cell}

The lengths and angles of the unit cell.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="cell-length-a">

### Cell length a {#cell-length-a}

Length of the unit-cell edge along the a axis. Cell geometry determines calculated reflection positions; check the space-group symmetry before freeing cell dimensions.

**Units:** Å.

[Equation and conventions](crystallography.md#eq-cell-metric) · [Names across interfaces](../user-guide/parameters.md#names-cell)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="cell-length-b">

### Cell length b {#cell-length-b}

Length of the unit-cell edge along the b axis. Cell geometry determines calculated reflection positions; check the space-group symmetry before freeing cell dimensions.

**Units:** Å.

[Equation and conventions](crystallography.md#eq-cell-metric) · [Names across interfaces](../user-guide/parameters.md#names-cell)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="cell-length-c">

### Cell length c {#cell-length-c}

Length of the unit-cell edge along the c axis. Cell geometry determines calculated reflection positions; check the space-group symmetry before freeing cell dimensions.

**Units:** Å.

[Equation and conventions](crystallography.md#eq-cell-metric) · [Names across interfaces](../user-guide/parameters.md#names-cell)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="cell-angle-alpha">

### Cell angle α {#cell-angle-alpha}

Unit-cell angle between b and c (degrees; engine converts to radians).

**Units:** deg.

[Equation and conventions](crystallography.md#eq-cell-metric) · [Names across interfaces](../user-guide/parameters.md#names-cell)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="cell-angle-beta">

### Cell angle β {#cell-angle-beta}

Unit-cell angle between a and c (degrees; engine converts to radians).

**Units:** deg.

[Equation and conventions](crystallography.md#eq-cell-metric) · [Names across interfaces](../user-guide/parameters.md#names-cell)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="cell-angle-gamma">

### Cell angle γ {#cell-angle-gamma}

Unit-cell angle between a and b (degrees; engine converts to radians).

**Units:** deg.

[Equation and conventions](crystallography.md#eq-cell-metric) · [Names across interfaces](../user-guide/parameters.md#names-cell)

</section>

## <span class="ed-reference-icon" data-reference-category="atom-site" aria-hidden="true">&#62930;</span> Atom site {#atom-site}

The atom sites of the structure: position, occupancy and isotropic displacement.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-id">

### Atom-site identifier {#atom-site-id}

Unique atom-site identifier.

[Equation and conventions](diffraction.md#eq-nuclear-structure-factor) · [Names across interfaces](../user-guide/parameters.md#names-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-type-symbol">

### Chemical element {#atom-site-type-symbol}

Chemical symbol of the atom at this site.

[Equation and conventions](diffraction.md#eq-nuclear-structure-factor) · [Names across interfaces](../user-guide/parameters.md#names-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-wyckoff-letter">

### Wyckoff position {#atom-site-wyckoff-letter}

Wyckoff letter of the site in its space group.

[Equation and conventions](diffraction.md#eq-nuclear-structure-factor) · [Names across interfaces](../user-guide/parameters.md#names-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-adp-type">

### Displacement parameter type {#atom-site-adp-type}

Atomic displacement parameter type: Biso, Uiso, Bani, Uani or beta; Biso when absent.

| Option | Meaning |
| --- | --- |
| B iso | Isotropic, B in Å². |
| U iso | Isotropic, U in Å². |
| B aniso | Anisotropic, the B tensor in Å². |
| U aniso | Anisotropic, the U tensor in Å². |
| β | Anisotropic, the dimensionless β tensor. |

[Equation and conventions](displacement.md#eq-isotropic-adp) · [Names across interfaces](../user-guide/parameters.md#names-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-fract-x">

### Fractional x-coordinate {#atom-site-fract-x}

Position of the representative atom site along the a lattice vector, expressed as a fraction of the unit cell rather than a Cartesian distance.

**Units:** dimensionless.

[Equation and conventions](diffraction.md#eq-nuclear-structure-factor) · [Names across interfaces](../user-guide/parameters.md#names-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-fract-y">

### Fractional y-coordinate {#atom-site-fract-y}

Position of the representative atom site along the b lattice vector, expressed as a fraction of the unit cell rather than a Cartesian distance.

**Units:** dimensionless.

[Equation and conventions](diffraction.md#eq-nuclear-structure-factor) · [Names across interfaces](../user-guide/parameters.md#names-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-fract-z">

### Fractional z-coordinate {#atom-site-fract-z}

Position of the representative atom site along the c lattice vector, expressed as a fraction of the unit cell rather than a Cartesian distance.

**Units:** dimensionless.

[Equation and conventions](diffraction.md#eq-nuclear-structure-factor) · [Names across interfaces](../user-guide/parameters.md#names-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-occupancy">

### Occupancy {#atom-site-occupancy}

Site occupancy (raw occupancy; m/M multiplicity applied in &#124;F&#124;^2).

**Units:** dimensionless.

[Equation and conventions](diffraction.md#eq-nuclear-structure-factor) · [Names across interfaces](../user-guide/parameters.md#names-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-adp-iso">

### Isotropic or equivalent displacement {#atom-site-adp-iso}

Isotropic atomic displacement parameter in the site&#x27;s declared type: B for Biso, U for Uiso (B = 8 pi^2 U); an anisotropic site&#x27;s equivalent isotropic value, derived.

**Units:** Å².

| Form | Units |
| --- | --- |
| <code>Biso</code> | Å² |
| <code>Uiso</code> | Å² |
| <code>Bani</code> | Å² |
| <code>Uani</code> | Å² |
| <code>beta</code> | Å² |

[Equation and conventions](displacement.md#eq-isotropic-adp) · [Names across interfaces](../user-guide/parameters.md#names-atom-site)

</section>

## <span class="ed-reference-icon" data-reference-category="atom-site-aniso" aria-hidden="true">&#61618;</span> Atomic displacement {#atom-site-aniso}

The anisotropic displacement of each anisotropic atom site.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-aniso-id">

### Anisotropic atom-site identifier {#atom-site-aniso-id}

The id of the anisotropic atom site the row belongs to.

[Equation and conventions](displacement.md#eq-anisotropic-adp) · [Names across interfaces](../user-guide/parameters.md#names-atom-site-aniso)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-aniso-adp-11">

### Displacement tensor component 11 {#atom-site-aniso-adp-11}

Anisotropic displacement tensor component 11 (diagonal 11) in the site&#x27;s declared type: U for Uani, B for Bani (Å²), dimensionless beta for beta.

**Units:** Å² for B/U; dimensionless for β.

| Form | Units |
| --- | --- |
| <code>Uani</code> | Å² |
| <code>Bani</code> | Å² |
| <code>beta</code> | dimensionless |

[Equation and conventions](displacement.md#eq-anisotropic-adp) · [Names across interfaces](../user-guide/parameters.md#names-atom-site-aniso)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-aniso-adp-22">

### Displacement tensor component 22 {#atom-site-aniso-adp-22}

Anisotropic displacement tensor component 22 (diagonal 22) in the site&#x27;s declared type: U for Uani, B for Bani (Å²), dimensionless beta for beta.

**Units:** Å² for B/U; dimensionless for β.

| Form | Units |
| --- | --- |
| <code>Uani</code> | Å² |
| <code>Bani</code> | Å² |
| <code>beta</code> | dimensionless |

[Equation and conventions](displacement.md#eq-anisotropic-adp) · [Names across interfaces](../user-guide/parameters.md#names-atom-site-aniso)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-aniso-adp-33">

### Displacement tensor component 33 {#atom-site-aniso-adp-33}

Anisotropic displacement tensor component 33 (diagonal 33) in the site&#x27;s declared type: U for Uani, B for Bani (Å²), dimensionless beta for beta.

**Units:** Å² for B/U; dimensionless for β.

| Form | Units |
| --- | --- |
| <code>Uani</code> | Å² |
| <code>Bani</code> | Å² |
| <code>beta</code> | dimensionless |

[Equation and conventions](displacement.md#eq-anisotropic-adp) · [Names across interfaces](../user-guide/parameters.md#names-atom-site-aniso)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-aniso-adp-12">

### Displacement tensor component 12 {#atom-site-aniso-adp-12}

Anisotropic displacement tensor component 12 (off-diagonal 12) in the site&#x27;s declared type: U for Uani, B for Bani (Å²), dimensionless beta for beta.

**Units:** Å² for B/U; dimensionless for β.

| Form | Units |
| --- | --- |
| <code>Uani</code> | Å² |
| <code>Bani</code> | Å² |
| <code>beta</code> | dimensionless |

[Equation and conventions](displacement.md#eq-anisotropic-adp) · [Names across interfaces](../user-guide/parameters.md#names-atom-site-aniso)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-aniso-adp-13">

### Displacement tensor component 13 {#atom-site-aniso-adp-13}

Anisotropic displacement tensor component 13 (off-diagonal 13) in the site&#x27;s declared type: U for Uani, B for Bani (Å²), dimensionless beta for beta.

**Units:** Å² for B/U; dimensionless for β.

| Form | Units |
| --- | --- |
| <code>Uani</code> | Å² |
| <code>Bani</code> | Å² |
| <code>beta</code> | dimensionless |

[Equation and conventions](displacement.md#eq-anisotropic-adp) · [Names across interfaces](../user-guide/parameters.md#names-atom-site-aniso)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-site-aniso-adp-23">

### Displacement tensor component 23 {#atom-site-aniso-adp-23}

Anisotropic displacement tensor component 23 (off-diagonal 23) in the site&#x27;s declared type: U for Uani, B for Bani (Å²), dimensionless beta for beta.

**Units:** Å² for B/U; dimensionless for β.

| Form | Units |
| --- | --- |
| <code>Uani</code> | Å² |
| <code>Bani</code> | Å² |
| <code>beta</code> | dimensionless |

[Equation and conventions](displacement.md#eq-anisotropic-adp) · [Names across interfaces](../user-guide/parameters.md#names-atom-site-aniso)

</section>

## <span class="ed-reference-icon" data-reference-category="scattering-length" aria-hidden="true">&#62789;</span> Scattering length {#scattering-length}

Neutron coherent scattering lengths that replace the built-in table for an element or isotope.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="scattering-length-type-symbol">

### Type {#scattering-length-type-symbol}

The element or isotope the scattering length applies to.

[Names across interfaces](../user-guide/parameters.md#names-scattering-length)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="scattering-length-length-fm">

### Neutron scattering length {#scattering-length-length-fm}

The coherent neutron scattering length.

**Units:** fm.

[Names across interfaces](../user-guide/parameters.md#names-scattering-length)

</section>

## <span class="ed-reference-icon" data-reference-category="geom" aria-hidden="true">&#62790;</span> Bond settings {#geom}

How bonds between atoms are found.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="geom-min-bond-distance-cutoff">

### Minimum bond distance {#geom-min-bond-distance-cutoff}

Atoms closer than this are not bonded.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-geom)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="geom-bond-distance-inc">

### Bond-distance tolerance {#geom-bond-distance-inc}

How much longer than the sum of the covalent radii a bond may be.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-geom)

</section>

## <span class="ed-reference-icon" data-reference-category="structure-view" aria-hidden="true">&#62783;</span> Appearance {#structure-view}

How the structure view draws the structure: atoms, colours, labels and what else it shows.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="structure-view-atom-view">

### Atom radius model {#structure-view-atom-view}

What sets the size of each atom.

| Option | Meaning |
| --- | --- |
| Covalent radius | The covalent radius. |
| Van der Waals radius | The van der Waals radius. |
| Ionic radius | The ionic radius. |
| Displacement | The atomic displacement, at the probability set. |

[Names across interfaces](../user-guide/parameters.md#names-structure-view)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="structure-view-colour-scheme">

### Colours {#structure-view-colour-scheme}

The colours the atoms take, by element.

| Option | Meaning |
| --- | --- |
| Jmol | The Jmol colours. |
| VESTA | The VESTA colours. |

[Names across interfaces](../user-guide/parameters.md#names-structure-view)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="structure-view-atom-scale">

### Atom scale {#structure-view-atom-scale}

The atoms&#x27; drawn size as a share of their radius.

[Names across interfaces](../user-guide/parameters.md#names-structure-view)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="structure-view-adp-probability">

### Ellipsoid probability {#structure-view-adp-probability}

The probability the displacement ellipsoids enclose.

[Names across interfaces](../user-guide/parameters.md#names-structure-view)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="structure-view-labels">

### Labels {#structure-view-labels}

Whether each atom is labelled.

[Names across interfaces](../user-guide/parameters.md#names-structure-view)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="structure-view-atoms">

### Atoms shown {#structure-view-atoms}

Which atoms are drawn.

| Option | Meaning |
| --- | --- |
| All | Every atom in the cell. |
| Asymmetric unit | The atoms of the asymmetric unit. |
| None | No atoms. |

[Names across interfaces](../user-guide/parameters.md#names-structure-view)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="structure-view-bonds">

### Bonds {#structure-view-bonds}

Whether bonds are drawn.

[Names across interfaces](../user-guide/parameters.md#names-structure-view)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="structure-view-cell">

### Cell {#structure-view-cell}

Whether the unit cell is drawn.

[Names across interfaces](../user-guide/parameters.md#names-structure-view)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="structure-view-axes">

### Axes {#structure-view-axes}

Whether the cell axes are drawn.

[Names across interfaces](../user-guide/parameters.md#names-structure-view)

</section>

## <span class="ed-reference-icon" data-reference-category="space-group-symop" aria-hidden="true">&#62193;</span> Symmetry operator {#space-group-symop}

The space group&#x27;s symmetry operators, in the order a symmetry code refers to them.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="space-group-symop-operation-xyz">

### Symmetry operation {#space-group-symop-operation-xyz}

A symmetry operator as x, y, z expressions.

[Names across interfaces](../user-guide/parameters.md#names-space-group-symop)

</section>

## <span class="ed-reference-icon" data-reference-category="expanded-atom-site" aria-hidden="true">&#62113;</span> Atom in the cell {#expanded-atom-site}

Every atom of the unit cell, generated from the atom sites by symmetry.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="expanded-atom-site-atom-site-id">

### Source atom site {#expanded-atom-site-atom-site-id}

The atom site this atom is generated from.

[Names across interfaces](../user-guide/parameters.md#names-expanded-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="expanded-atom-site-site-symmetry">

### Generating symmetry operation {#expanded-atom-site-site-symmetry}

The symmetry code that generates this atom from its site.

[Names across interfaces](../user-guide/parameters.md#names-expanded-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="expanded-atom-site-fract-x">

### Fractional x-coordinate {#expanded-atom-site-fract-x}

Position of the symmetry-generated atom along the a lattice vector, expressed as a fraction of the unit cell rather than a Cartesian distance.

[Names across interfaces](../user-guide/parameters.md#names-expanded-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="expanded-atom-site-fract-y">

### Fractional y-coordinate {#expanded-atom-site-fract-y}

Position of the symmetry-generated atom along the b lattice vector, expressed as a fraction of the unit cell rather than a Cartesian distance.

[Names across interfaces](../user-guide/parameters.md#names-expanded-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="expanded-atom-site-fract-z">

### Fractional z-coordinate {#expanded-atom-site-fract-z}

Position of the symmetry-generated atom along the c lattice vector, expressed as a fraction of the unit cell rather than a Cartesian distance.

[Names across interfaces](../user-guide/parameters.md#names-expanded-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="expanded-atom-site-cartn-x">

### Cartesian x-coordinate {#expanded-atom-site-cartn-x}

Cartesian X-coordinate.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-expanded-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="expanded-atom-site-cartn-y">

### Cartesian y-coordinate {#expanded-atom-site-cartn-y}

Cartesian Y-coordinate.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-expanded-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="expanded-atom-site-cartn-z">

### Cartesian z-coordinate {#expanded-atom-site-cartn-z}

Cartesian Z-coordinate.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-expanded-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="expanded-atom-site-occupancy">

### Occupancy {#expanded-atom-site-occupancy}

Occupancy of the atom.

[Names across interfaces](../user-guide/parameters.md#names-expanded-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="expanded-atom-site-u-iso">

### Isotropic displacement U {#expanded-atom-site-u-iso}

Isotropic displacement of the atom, as U.

**Units:** Å².

[Names across interfaces](../user-guide/parameters.md#names-expanded-atom-site)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="expanded-atom-site-cluster-id">

### Coincident-atom cluster {#expanded-atom-site-cluster-id}

Atoms within one shared position carry the same cluster number.

[Names across interfaces](../user-guide/parameters.md#names-expanded-atom-site)

</section>

## <span class="ed-reference-icon" data-reference-category="geom-bond" aria-hidden="true">&#63396;</span> Bond {#geom-bond}

The bonds between the atoms of the cell.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="geom-bond-expanded-atom-site-id-1">

### Atom 1 {#geom-bond-expanded-atom-site-id-1}

The first atom of the bond, in the atoms of the cell.

[Names across interfaces](../user-guide/parameters.md#names-geom-bond)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="geom-bond-expanded-atom-site-id-2">

### Atom 2 {#geom-bond-expanded-atom-site-id-2}

The second atom of the bond, in the atoms of the cell.

[Names across interfaces](../user-guide/parameters.md#names-geom-bond)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="geom-bond-atom-site-label-1">

### Site 1 {#geom-bond-atom-site-label-1}

The atom site of the first atom.

[Names across interfaces](../user-guide/parameters.md#names-geom-bond)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="geom-bond-atom-site-label-2">

### Site 2 {#geom-bond-atom-site-label-2}

The atom site of the second atom.

[Names across interfaces](../user-guide/parameters.md#names-geom-bond)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="geom-bond-site-symmetry-1">

### Symmetry 1 {#geom-bond-site-symmetry-1}

The symmetry code of the first atom.

[Names across interfaces](../user-guide/parameters.md#names-geom-bond)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="geom-bond-site-symmetry-2">

### Symmetry 2 {#geom-bond-site-symmetry-2}

The symmetry code of the second atom.

[Names across interfaces](../user-guide/parameters.md#names-geom-bond)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="geom-bond-distance">

### Distance {#geom-bond-distance}

The length of the bond.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-geom-bond)

</section>

## <span class="ed-reference-icon" data-reference-category="atom-sites-cartn-transform" aria-hidden="true">&#62923;</span> Cartesian frame {#atom-sites-cartn-transform}

The matrix from fractional to Cartesian coordinates.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-sites-cartn-transform-mat-11">

### Coordinate-transform element 11 {#atom-sites-cartn-transform-mat-11}

Element 11 of the fractional-to-Cartesian matrix.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-atom-sites-cartn-transform)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-sites-cartn-transform-mat-12">

### Coordinate-transform element 12 {#atom-sites-cartn-transform-mat-12}

Element 12 of the fractional-to-Cartesian matrix.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-atom-sites-cartn-transform)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-sites-cartn-transform-mat-13">

### Coordinate-transform element 13 {#atom-sites-cartn-transform-mat-13}

Element 13 of the fractional-to-Cartesian matrix.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-atom-sites-cartn-transform)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-sites-cartn-transform-mat-21">

### Coordinate-transform element 21 {#atom-sites-cartn-transform-mat-21}

Element 21 of the fractional-to-Cartesian matrix.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-atom-sites-cartn-transform)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-sites-cartn-transform-mat-22">

### Coordinate-transform element 22 {#atom-sites-cartn-transform-mat-22}

Element 22 of the fractional-to-Cartesian matrix.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-atom-sites-cartn-transform)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-sites-cartn-transform-mat-23">

### Coordinate-transform element 23 {#atom-sites-cartn-transform-mat-23}

Element 23 of the fractional-to-Cartesian matrix.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-atom-sites-cartn-transform)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-sites-cartn-transform-mat-31">

### Coordinate-transform element 31 {#atom-sites-cartn-transform-mat-31}

Element 31 of the fractional-to-Cartesian matrix.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-atom-sites-cartn-transform)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-sites-cartn-transform-mat-32">

### Coordinate-transform element 32 {#atom-sites-cartn-transform-mat-32}

Element 32 of the fractional-to-Cartesian matrix.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-atom-sites-cartn-transform)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-sites-cartn-transform-mat-33">

### Coordinate-transform element 33 {#atom-sites-cartn-transform-mat-33}

Element 33 of the fractional-to-Cartesian matrix.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-atom-sites-cartn-transform)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="atom-sites-cartn-transform-axes">

### Axes {#atom-sites-cartn-transform-axes}

How the Cartesian axes are placed in the cell.

[Names across interfaces](../user-guide/parameters.md#names-atom-sites-cartn-transform)

</section>

## <span class="ed-reference-icon" data-reference-category="experiment-type" aria-hidden="true">&#63417;</span> Experiment type {#experiment-type}

What kind of experiment this is: sample form, beam mode, probe and scattering type.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="experiment-type-beam-mode">

### Beam mode {#experiment-type-beam-mode}

How the pattern is measured.

| Option | Meaning |
| --- | --- |
| Constant wavelength | One wavelength, the pattern measured against the scattering angle 2θ. |
| Time-of-flight | A white beam, the pattern measured against the time of flight. |

[Names across interfaces](../user-guide/parameters.md#names-experiment-type)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="experiment-type-sample-form">

### Sample form {#experiment-type-sample-form}

The form of the sample.

| Option | Meaning |
| --- | --- |
| Powder | A polycrystalline sample. |
| Single crystal | One crystal. |

[Names across interfaces](../user-guide/parameters.md#names-experiment-type)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="experiment-type-radiation-probe">

### Probe {#experiment-type-radiation-probe}

The radiation scattered by the sample.

| Option | Meaning |
| --- | --- |
| Neutron | Neutrons, scattered by the nuclei. |
| X-ray | X-rays, scattered by the electrons. |

[Names across interfaces](../user-guide/parameters.md#names-experiment-type)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="experiment-type-scattering-type">

### Scattering type {#experiment-type-scattering-type}

Which scattering the pattern is modelled with.

| Option | Meaning |
| --- | --- |
| Bragg | Bragg peaks from the average structure. |
| Total | Bragg and diffuse scattering together. |

[Names across interfaces](../user-guide/parameters.md#names-experiment-type)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="experiment-type-dimensionality">

### Dimensionality {#experiment-type-dimensionality}

The dimensionality of the measured pattern.

| Option | Meaning |
| --- | --- |
| 1D | A one-dimensional pattern. |

[Names across interfaces](../user-guide/parameters.md#names-experiment-type)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="experiment-type-polarisation">

### Polarisation {#experiment-type-polarisation}

The polarisation of the incident beam; an X-ray experiment states the inapplicable value.

| Option | Meaning |
| --- | --- |
| Unpolarised | An unpolarised neutron beam. |
| Not applicable | An X-ray experiment, whose beam polarisation is not a setting here. |

[Names across interfaces](../user-guide/parameters.md#names-experiment-type)

</section>

## <span class="ed-reference-icon" data-reference-category="data-range" aria-hidden="true">&#62263;</span> Calculation range {#data-range}

The grid a pattern is calculated on when no data are measured.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-range-two-theta-min">

### Min {#data-range-two-theta-min}

The first 2θ of the calculation grid.

**Units:** deg.

[Names across interfaces](../user-guide/parameters.md#names-data-range)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-range-two-theta-max">

### Max {#data-range-two-theta-max}

The last 2θ of the calculation grid.

**Units:** deg.

[Names across interfaces](../user-guide/parameters.md#names-data-range)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-range-two-theta-step">

### Step {#data-range-two-theta-step}

The 2θ step of the calculation grid.

**Units:** deg.

[Names across interfaces](../user-guide/parameters.md#names-data-range)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-range-two-theta">

### Scattering angle {#data-range-two-theta}

The 2θ points of the calculation grid.

**Units:** deg.

[Names across interfaces](../user-guide/parameters.md#names-data-range)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-range-time-of-flight-min">

### Min {#data-range-time-of-flight-min}

The first time of flight of the calculation grid.

**Units:** µs.

[Names across interfaces](../user-guide/parameters.md#names-data-range)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-range-time-of-flight-max">

### Max {#data-range-time-of-flight-max}

The last time of flight of the calculation grid.

**Units:** µs.

[Names across interfaces](../user-guide/parameters.md#names-data-range)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-range-time-of-flight-step">

### Step {#data-range-time-of-flight-step}

The time-of-flight step of the calculation grid.

**Units:** µs.

[Names across interfaces](../user-guide/parameters.md#names-data-range)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-range-time-of-flight">

### Time of flight {#data-range-time-of-flight}

The time-of-flight points of the calculation grid.

**Units:** µs.

[Names across interfaces](../user-guide/parameters.md#names-data-range)

</section>

## <span class="ed-reference-icon" data-reference-category="background" aria-hidden="true">&#63550;</span> Background {#background}

The background under the diffraction peaks.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-intensity">

### Background anchor intensity {#background-intensity}

Line-segment background intensity anchor (dimensionless in the reduced pattern; linear).

**Units:** intensity units of the pattern.

[Equation and conventions](background.md#eq-line-segment-background) · [Names across interfaces](../user-guide/parameters.md#names-background)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-position">

### Background anchor position {#background-position}

Background anchor position (TOF, us); a fixed node, not a refinable Parameter.

**Units:** µs.

[Equation and conventions](background.md#eq-line-segment-background) · [Names across interfaces](../user-guide/parameters.md#names-background)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-coef">

### Background coefficient {#background-coef}

Polynomial or Chebyshev background coefficient of the row&#x27;s order (dimensionless in the reduced pattern; linear).

**Units:** intensity units of the pattern.

[Equation and conventions](background.md#eq-chebyshev-background) · [Names across interfaces](../user-guide/parameters.md#names-background)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-order">

### Background term order {#background-order}

Order m of a polynomial or Chebyshev background term (a non-negative integer; a fixed node, not a refinable Parameter).

**Units:** dimensionless.

[Equation and conventions](background.md#eq-chebyshev-background) · [Names across interfaces](../user-guide/parameters.md#names-background)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-origin">

### Polynomial background origin {#background-origin}

Origin of the polynomial background, FullProf Bkpos: the terms are powers of x/origin - 1 (in the pattern&#x27;s axis units; non-zero).

**Units:** native pattern-axis units (degrees 2θ or µs).

[Equation and conventions](background.md#eq-polynomial-background) · [Names across interfaces](../user-guide/parameters.md#names-background)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-x-min">

### Chebyshev domain minimum {#background-x-min}

Lower end of the Chebyshev background&#x27;s normalisation domain (in the pattern&#x27;s axis units).

**Units:** native pattern-axis units (degrees 2θ or µs).

[Equation and conventions](background.md#eq-chebyshev-background) · [Names across interfaces](../user-guide/parameters.md#names-background)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-x-max">

### Chebyshev domain maximum {#background-x-max}

Upper end of the Chebyshev background&#x27;s normalisation domain (in the pattern&#x27;s axis units; above x_min).

**Units:** native pattern-axis units (degrees 2θ or µs).

[Equation and conventions](background.md#eq-chebyshev-background) · [Names across interfaces](../user-guide/parameters.md#names-background)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-type">

### Background model {#background-type}

The background function.

| Option | Meaning |
| --- | --- |
| Line segment | Straight lines between background points. |
| Chebyshev | A sum of Chebyshev polynomials. |
| Polynomial | A polynomial in the scattering variable. |

[Names across interfaces](../user-guide/parameters.md#names-background)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-id">

### Background row identifier {#background-id}

The name of a background point or term.

[Names across interfaces](../user-guide/parameters.md#names-background)

</section>

## <span class="ed-reference-icon" data-reference-category="background-estimate" aria-hidden="true">&#61648;</span> Background estimation {#background-estimate}

How the background is estimated from the measured pattern.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-estimate-mode">

### Estimation mode {#background-estimate-mode}

Whether the background is edited by hand or estimated again on every change.

| Option | Meaning |
| --- | --- |
| Manual | The background is edited by hand; Estimate replaces it when asked. |
| Auto | The background is estimated again whenever the data or the settings change. |

[Names across interfaces](../user-guide/parameters.md#names-background-estimate)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-estimate-method">

### Method {#background-estimate-method}

The background estimation method.

| Option | Meaning |
| --- | --- |
| Auto | The default method, arPLS. |
| SNIP | SNIP (Ryan et al. 1988): clips the peaks away. |
| arPLS | arPLS (Baek et al. 2015): asymmetrically reweighted penalized least squares. |
| FABC | FABC (Cobas et al. 2006): finds the baseline points by a wavelet transform. |

[Names across interfaces](../user-guide/parameters.md#names-background-estimate)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-estimate-width">

### Peak width {#background-estimate-width}

The peak width the estimation assumes, in points.

[Names across interfaces](../user-guide/parameters.md#names-background-estimate)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-estimate-smoothness">

### Smoothness {#background-estimate-smoothness}

How smooth the estimated background is.

[Names across interfaces](../user-guide/parameters.md#names-background-estimate)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-estimate-n-points">

### Number of background anchors {#background-estimate-n-points}

How many background points the estimation keeps.

[Names across interfaces](../user-guide/parameters.md#names-background-estimate)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-estimate-tolerance">

### Background thinning tolerance {#background-estimate-tolerance}

How far, in units of the noise, the thinned background may stray.

[Names across interfaces](../user-guide/parameters.md#names-background-estimate)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-estimate-in-peaks">

### Anchors within peaks {#background-estimate-in-peaks}

What happens to a background point that falls in a peak.

| Option | Meaning |
| --- | --- |
| Move | Move it to the nearest allowed point. |
| Drop | Drop it. |

[Names across interfaces](../user-guide/parameters.md#names-background-estimate)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-estimate-use-model">

### Calculated-peak treatment {#background-estimate-use-model}

What the estimation does with the peaks of the calculated pattern.

| Option | Meaning |
| --- | --- |
| Auto | Subtract them when the calculated pattern matches the data. |
| Subtract | Always subtract them when there is a calculated pattern. |
| Ignore | Never subtract them. |

[Names across interfaces](../user-guide/parameters.md#names-background-estimate)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-estimate-max-terms">

### Max terms {#background-estimate-max-terms}

The most terms a Chebyshev or polynomial background may take.

[Names across interfaces](../user-guide/parameters.md#names-background-estimate)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-estimate-inputs-digest">

### Inputs digest {#background-estimate-inputs-digest}

A checksum of what the last estimate was made from.

[Names across interfaces](../user-guide/parameters.md#names-background-estimate)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="background-estimate-points-digest">

### Points digest {#background-estimate-points-digest}

A checksum of the background the last estimate wrote.

[Names across interfaces](../user-guide/parameters.md#names-background-estimate)

</section>

## <span class="ed-reference-icon" data-reference-category="instrument" aria-hidden="true">&#62992;</span> Instrument {#instrument}

The instrument setup and calibration.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-calib-d-to-tof-offset">

### TOF offset {#instrument-calib-d-to-tof-offset}

TOF calibration zero offset (TOF = zero + Dtt1*d + Dtt2*d^2 + recip/d).

**Units:** µs.

[Equation and conventions](calibration.md#eq-tof-calibration) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-calib-d-to-tof-linear">

### TOF linear {#instrument-calib-d-to-tof-linear}

TOF calibration linear coefficient Dtt1 (us/A).

**Units:** µs/Å.

[Equation and conventions](calibration.md#eq-tof-calibration) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-calib-d-to-tof-quadratic">

### TOF quadratic {#instrument-calib-d-to-tof-quadratic}

TOF calibration quadratic coefficient Dtt2 (us/A^2).

**Units:** µs/Å².

[Equation and conventions](calibration.md#eq-tof-calibration) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-calib-d-to-tof-reciprocal">

### TOF reciprocal {#instrument-calib-d-to-tof-reciprocal}

TOF calibration reciprocal (1/d) coefficient (us*A); round-tripped, held fixed in the free set.

**Units:** µs·Å.

**Stored only.** Retained in project input but not applied in this calculation.

[Equation and conventions](calibration.md#eq-tof-calibration) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-calib-twotheta-offset">

### Zero-point angular offset {#instrument-calib-twotheta-offset}

CW zero-point offset in degrees 2theta, subtracted from the observed axis.

**Units:** deg.

[Equation and conventions](calibration.md#eq-cwl-calibration) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-setup-wavelength">

### Wavelength {#instrument-setup-wavelength}

Incident neutron wavelength in angstroms (single wavelength; the doublet tags are X-ray scope).

**Units:** Å.

| Form | Units |
| --- | --- |
| <code>doublet</code> | Å |

[Equation and conventions](calibration.md#eq-cwl-calibration) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-calib-sample-displacement">

### Sample displacement {#instrument-calib-sample-displacement}

CW sample-displacement line shift in degrees 2theta (FullProf SyCos): adds displacement*cos(2theta_B) to each reflection&#x27;s position.

**Units:** deg.

[Equation and conventions](calibration.md#eq-line-shifts) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-calib-sample-transparency">

### Sample transparency {#instrument-calib-sample-transparency}

CW sample-transparency line shift in degrees 2theta (FullProf SySin): adds transparency*sin(2theta_B) to each reflection&#x27;s position.

**Units:** deg.

[Equation and conventions](calibration.md#eq-line-shifts) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-setup-polarization-coefficient">

### Polarization coefficient {#instrument-setup-polarization-coefficient}

X-ray CW polarization coefficient K (FullProf Rpolarz): the intensity carries P = 1 - K + K cos^2(2theta_m) cos^2(2theta); 0 disables the correction.

**Units:** dimensionless.

[Equation and conventions](corrections/intensity.md#eq-xray-polarization) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-setup-monochromator-twotheta">

### Monochromator 2θ {#instrument-setup-monochromator-twotheta}

X-ray CW pre-specimen monochromator angle 2theta_m in degrees (FullProf stores Cthm = cos^2(2theta_m)); 0 means no monochromator.

**Units:** deg.

[Equation and conventions](corrections/intensity.md#eq-xray-polarization) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-setup-wavelength-2">

### Secondary wavelength {#instrument-setup-wavelength-2}

X-ray CW second incident wavelength in angstroms (FullProf Lambda2, e.g. Cu K-alpha2); used when setup_wavelength_2_to_1_ratio is not 0.

**Units:** Å.

[Equation and conventions](corrections/intensity.md#wavelength-doublet) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-setup-wavelength-2-to-1-ratio">

### Secondary-to-primary intensity ratio {#instrument-setup-wavelength-2-to-1-ratio}

X-ray CW intensity of the second wavelength relative to the first (FullProf Ratio); 0 means a single wavelength.

**Units:** dimensionless.

[Equation and conventions](corrections/intensity.md#wavelength-doublet) · [Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-name">

### Instrument {#instrument-name}

The instrument the pattern was measured on, or unknown.

[Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-facility">

### Facility {#instrument-facility}

The facility the instrument belongs to, or unknown.

[Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="instrument-setup-twotheta-bank">

### 2θ bank {#instrument-setup-twotheta-bank}

The scattering angle of the time-of-flight detector bank.

**Units:** deg.

[Names across interfaces](../user-guide/parameters.md#names-instrument)

</section>

## <span class="ed-reference-icon" data-reference-category="peak" aria-hidden="true">&#63007;</span> Peak profile {#peak}

The shape and width of the diffraction peaks.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-rise-alpha-0">

### Exponential rise coefficient α₀ {#peak-rise-alpha-0}

Back-to-back exponential rise-rate coefficient alpha_0 (rate, 1/us; no closed unit code).

**Units:** µs⁻¹.

[Equation and conventions](profiles/tof.md#eq-jorgensen) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-rise-alpha-1">

### Exponential rise coefficient α₁ {#peak-rise-alpha-1}

Back-to-back exponential rise-rate coefficient alpha_1 (alpha(d)=alpha_0+alpha_1/d).

**Units:** Å/µs.

[Equation and conventions](profiles/tof.md#eq-jorgensen) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-decay-beta-0">

### Exponential decay coefficient β₀ {#peak-decay-beta-0}

Back-to-back exponential decay-rate coefficient beta_0 (rate, 1/us; no closed unit code).

**Units:** µs⁻¹.

[Equation and conventions](profiles/tof.md#eq-jorgensen) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-decay-beta-1">

### Exponential decay coefficient β₁ {#peak-decay-beta-1}

Back-to-back exponential decay-rate coefficient beta_1 (beta(d)=beta_0+beta_1/d^4).

**Units:** Å⁴/µs.

[Equation and conventions](profiles/tof.md#eq-jorgensen) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-gauss-sigma-0">

### Gaussian broadening σ₀² {#peak-broad-gauss-sigma-0}

Gaussian VARIANCE coefficient sigma_0^2 (variance domain; TCH consumes FWHM_G=sqrt(sigma^2)*sqrt(8 ln 2)).

**Units:** µs².

[Equation and conventions](profiles/tof.md#eq-tof-widths) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-gauss-sigma-1">

### Gaussian broadening σ₁² {#peak-broad-gauss-sigma-1}

Gaussian VARIANCE coefficient sigma_1^2 (d^2 term; variance domain).

**Units:** µs²/Å².

[Equation and conventions](profiles/tof.md#eq-tof-widths) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-gauss-sigma-2">

### Gaussian broadening σ₂² {#peak-broad-gauss-sigma-2}

Gaussian VARIANCE coefficient sigma_2^2 (d^4 term; us^2/A^4 not in closed vocab -&gt; none).

**Units:** µs²/Å⁴.

[Equation and conventions](profiles/tof.md#eq-tof-widths) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-gauss-size">

### Gaussian broadening size G {#peak-broad-gauss-size}

Gaussian isotropic size broadening (variance contribution).

**Units:** µs²/Å⁴.

[Equation and conventions](profiles/tof.md#eq-tof-widths) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-gauss-strain">

### Gaussian broadening strain G {#peak-broad-gauss-strain}

Gaussian isotropic strain broadening (variance contribution).

**Units:** µs²/Å².

[Equation and conventions](profiles/tof.md#eq-tof-widths) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-lorentz-gamma-0">

### Lorentzian broadening γ₀ {#peak-broad-lorentz-gamma-0}

Lorentzian FWHM coefficient gamma_0 (FWHM domain, H_L; consumed as FWHM directly, no sqrt(8 ln 2)).

**Units:** µs.

[Equation and conventions](profiles/tof.md#eq-tof-widths) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-lorentz-gamma-1">

### Lorentzian broadening γ₁ {#peak-broad-lorentz-gamma-1}

Lorentzian FWHM coefficient gamma_1 (d term; FWHM domain).

**Units:** µs/Å.

[Equation and conventions](profiles/tof.md#eq-tof-widths) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-lorentz-gamma-2">

### Lorentzian broadening γ₂ {#peak-broad-lorentz-gamma-2}

Lorentzian FWHM coefficient gamma_2 (d^2 term; FWHM domain).

**Units:** µs/Å².

[Equation and conventions](profiles/tof.md#eq-tof-widths) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-lorentz-size">

### Lorentzian broadening size L {#peak-broad-lorentz-size}

Lorentzian isotropic size broadening (FWHM).

**Units:** µs/Å².

[Equation and conventions](profiles/tof.md#eq-tof-widths) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-lorentz-strain">

### Lorentzian broadening strain L {#peak-broad-lorentz-strain}

Lorentzian isotropic strain broadening (FWHM).

**Units:** µs/Å.

[Equation and conventions](profiles/tof.md#eq-tof-widths) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-gauss-u">

### Gaussian broadening U {#peak-broad-gauss-u}

Caglioti Gaussian FWHM coefficient U (tan^2(theta) term; H_G^2 in deg^2).

**Units:** deg².

[Equation and conventions](profiles/cw.md#eq-tch) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-gauss-v">

### Gaussian broadening V {#peak-broad-gauss-v}

Caglioti Gaussian FWHM coefficient V (tan(theta) term; H_G^2 in deg^2).

**Units:** deg².

[Equation and conventions](profiles/cw.md#eq-tch) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-gauss-w">

### Gaussian broadening W {#peak-broad-gauss-w}

Caglioti Gaussian FWHM coefficient W (constant term; H_G^2 in deg^2).

**Units:** deg².

[Equation and conventions](profiles/cw.md#eq-tch) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-lorentz-x">

### Lorentzian broadening X {#peak-broad-lorentz-x}

Lorentzian FWHM coefficient X, strain-like (tan(theta) term; H_L in deg).

**Units:** deg.

[Equation and conventions](profiles/cw.md#eq-tch) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-broad-lorentz-y">

### Lorentzian broadening Y {#peak-broad-lorentz-y}

Lorentzian FWHM coefficient Y, size-like (1/cos(theta) term; H_L in deg).

**Units:** deg.

[Equation and conventions](profiles/cw.md#eq-tch) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-mixing-eta-0">

### Pseudo-Voigt mixing intercept {#peak-mixing-eta-0}

Pseudo-Voigt mixing at 2theta = 0: eta = eta_0 + eta_1 2theta (FullProf Eta0).

**Units:** dimensionless.

[Equation and conventions](profiles/cw.md#eq-caglioti) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-mixing-eta-1">

### Pseudo-Voigt mixing slope {#peak-mixing-eta-1}

Pseudo-Voigt mixing slope per degree 2theta: eta = eta_0 + eta_1 2theta (FullProf X of Npr 5).

**Units:** 1/deg.

[Equation and conventions](profiles/cw.md#eq-caglioti) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-asym-fcj-1">

### FCJ asymmetry S/L {#peak-asym-fcj-1}

Finger-Cox-Jephcoat asymmetry parameter 1: S/L, half the sample height over the diffractometer radius.

**Units:** dimensionless.

[Equation and conventions](profiles/cw.md#eq-fcj) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-asym-fcj-2">

### FCJ asymmetry D/L {#peak-asym-fcj-2}

Finger-Cox-Jephcoat asymmetry parameter 2: D/L, half the detector height over the diffractometer radius.

**Units:** dimensionless.

[Equation and conventions](profiles/cw.md#eq-fcj) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-asym-beba-a0">

### Bérar-Baldinozzi asymmetry A₀ {#peak-asym-beba-a0}

Berar-Baldinozzi asymmetry coefficient A0 (Fa/tan theta).

**Units:** dimensionless.

[Equation and conventions](profiles/cw.md#eq-berar-baldinozzi) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-asym-beba-b0">

### Bérar-Baldinozzi asymmetry B₀ {#peak-asym-beba-b0}

Berar-Baldinozzi asymmetry coefficient B0 (Fb/tan theta).

**Units:** dimensionless.

[Equation and conventions](profiles/cw.md#eq-berar-baldinozzi) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-asym-beba-a1">

### Bérar-Baldinozzi asymmetry A₁ {#peak-asym-beba-a1}

Berar-Baldinozzi asymmetry coefficient A1 (Fa/tan 2theta).

**Units:** dimensionless.

[Equation and conventions](profiles/cw.md#eq-berar-baldinozzi) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-asym-beba-b1">

### Bérar-Baldinozzi asymmetry B₁ {#peak-asym-beba-b1}

Berar-Baldinozzi asymmetry coefficient B1 (Fb/tan 2theta).

**Units:** dimensionless.

[Equation and conventions](profiles/cw.md#eq-berar-baldinozzi) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-asym-beba-limit">

### Bérar-Baldinozzi asymmetry AsyLim {#peak-asym-beba-limit}

Berar-Baldinozzi limit angle (deg 2theta): reflections at or above it get no asymmetry correction (FullProf AsyLim); default 180.

**Units:** deg.

[Equation and conventions](profiles/cw.md#eq-berar-baldinozzi) · [Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-type">

### Profile {#peak-type}

The peak-profile function.

| Option | Meaning |
| --- | --- |
| Gaussian | A Gaussian peak with the Caglioti width. |
| Lorentzian | A Lorentzian peak. |
| Pseudo-Voigt | A pseudo-Voigt peak with a refinable mixing. |
| Pseudo-Voigt + Bérar-Baldinozzi asymmetry | A pseudo-Voigt peak with the Bérar-Baldinozzi asymmetry correction. |
| Thompson-Cox-Hastings pseudo-Voigt (TCH) | The Thompson-Cox-Hastings pseudo-Voigt peak. |
| Thompson-Cox-Hastings pseudo-Voigt (TCH) + Finger-Cox-Jephcoat asymmetry (FCJ) | The TCH peak with the Finger-Cox-Jephcoat axial-divergence asymmetry. |
| Jorgensen | The back-to-back exponentials convolved with a Gaussian. |
| Jorgensen-Von Dreele | The back-to-back exponentials convolved with a pseudo-Voigt. |
| Pseudo-Voigt | A time-of-flight pseudo-Voigt peak. |

[Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="peak-cutoff-fwhm">

### Peak calculation cutoff {#peak-cutoff-fwhm}

How far from its centre a peak is calculated, in units of its width.

[Names across interfaces](../user-guide/parameters.md#names-peak)

</section>

## <span class="ed-reference-icon" data-reference-category="excluded-region" aria-hidden="true">&#61741;</span> Excluded region {#excluded-region}

Ranges of the pattern left out of the fit.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="excluded-region-id">

### Id {#excluded-region-id}

The name of the excluded region.

[Names across interfaces](../user-guide/parameters.md#names-excluded-region)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="excluded-region-start">

### Start {#excluded-region-start}

Where the excluded region starts.

**Units:** deg.

| Form | Units |
| --- | --- |
| <code>constant wavelength</code> | deg |
| <code>time-of-flight</code> | µs |

[Names across interfaces](../user-guide/parameters.md#names-excluded-region)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="excluded-region-end">

### End {#excluded-region-end}

Where the excluded region ends.

**Units:** deg.

| Form | Units |
| --- | --- |
| <code>constant wavelength</code> | deg |
| <code>time-of-flight</code> | µs |

[Names across interfaces](../user-guide/parameters.md#names-excluded-region)

</section>

## <span class="ed-reference-icon" data-reference-category="extinction" aria-hidden="true">&#62373;</span> Extinction {#extinction}

A single crystal&#x27;s extinction correction: its type, mosaic distribution and parameters.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-domain-radius">

### Domain radius {#extinction-domain-radius}

Becker-Coppens domain (mosaic block) radius r (micrometres; extinction types II and mixed; single crystal; a fit parameter).

**Units:** μm.

[Equation and conventions](corrections/extinction.md#extinction-units) · [Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-mosaic-spread">

### Mosaic spread {#extinction-mosaic-spread}

Becker-Coppens mosaic spread g of the crystal, the inverse width of its mosaic distribution (larger is narrower; radians to the minus one; extinction types I and mixed; single crystal; a fit parameter).

**Units:** rad⁻¹.

[Equation and conventions](corrections/extinction.md#extinction-units) · [Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-crystal-radius">

### Crystal radius {#extinction-crystal-radius}

Radius of the crystal taken as a sphere, which sets each reflection&#x27;s mean path length through it for the Becker-Coppens secondary extinction (millimetres, as _exptl_crystal.size_rad; every Becker-Coppens type; single crystal; a descriptor, never fitted).

**Units:** mm.

[Equation and conventions](corrections/extinction.md#extinction-units) · [Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-coefficient">

### Extinction coefficient {#extinction-coefficient}

Larson&#x27;s empirical extinction coefficient x, as SHELXL&#x27;s EXTI: F2calc is multiplied by [1 + 0.001 x F2calc lambda^3 / sin 2theta]^(-1/2) (extinction type larson-isotropic; single crystal; a fit parameter).

**Units:** dimensionless.

[Equation and conventions](corrections/extinction.md#eq-larson) · [Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-coefficient-11">

### X11 {#extinction-coefficient-11}

The term of h² in Larson&#x27;s anisotropic extinction tensor x_aniso = x11 h^2 + x22 k^2 + x33 l^2 + x12 hk + x13 hl + x23 kl, which takes the place of 4 x (sin theta/lambda)^2 (FullProf&#x27;s Ext1; extinction type larson-anisotropic; single crystal; a fit parameter).

**Units:** dimensionless.

[Equation and conventions](corrections/extinction.md#eq-larson) · [Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-coefficient-22">

### X22 {#extinction-coefficient-22}

The term of k² in Larson&#x27;s anisotropic extinction tensor x_aniso = x11 h^2 + x22 k^2 + x33 l^2 + x12 hk + x13 hl + x23 kl, which takes the place of 4 x (sin theta/lambda)^2 (FullProf&#x27;s Ext2; extinction type larson-anisotropic; single crystal; a fit parameter).

**Units:** dimensionless.

[Equation and conventions](corrections/extinction.md#eq-larson) · [Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-coefficient-33">

### X33 {#extinction-coefficient-33}

The term of l² in Larson&#x27;s anisotropic extinction tensor x_aniso = x11 h^2 + x22 k^2 + x33 l^2 + x12 hk + x13 hl + x23 kl, which takes the place of 4 x (sin theta/lambda)^2 (FullProf&#x27;s Ext3; extinction type larson-anisotropic; single crystal; a fit parameter).

**Units:** dimensionless.

[Equation and conventions](corrections/extinction.md#eq-larson) · [Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-coefficient-12">

### X12 {#extinction-coefficient-12}

The term of hk in Larson&#x27;s anisotropic extinction tensor x_aniso = x11 h^2 + x22 k^2 + x33 l^2 + x12 hk + x13 hl + x23 kl, which takes the place of 4 x (sin theta/lambda)^2 (FullProf&#x27;s Ext4; extinction type larson-anisotropic; single crystal; a fit parameter).

**Units:** dimensionless.

[Equation and conventions](corrections/extinction.md#eq-larson) · [Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-coefficient-13">

### X13 {#extinction-coefficient-13}

The term of hl in Larson&#x27;s anisotropic extinction tensor x_aniso = x11 h^2 + x22 k^2 + x33 l^2 + x12 hk + x13 hl + x23 kl, which takes the place of 4 x (sin theta/lambda)^2 (FullProf&#x27;s Ext5; extinction type larson-anisotropic; single crystal; a fit parameter).

**Units:** dimensionless.

[Equation and conventions](corrections/extinction.md#eq-larson) · [Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-coefficient-23">

### X23 {#extinction-coefficient-23}

The term of kl in Larson&#x27;s anisotropic extinction tensor x_aniso = x11 h^2 + x22 k^2 + x33 l^2 + x12 hk + x13 hl + x23 kl, which takes the place of 4 x (sin theta/lambda)^2 (FullProf&#x27;s Ext6; extinction type larson-anisotropic; single crystal; a fit parameter).

**Units:** dimensionless.

[Equation and conventions](corrections/extinction.md#eq-larson) · [Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-type">

### Type {#extinction-type}

The extinction correction of a single crystal.

| Option | Meaning |
| --- | --- |
| None | No extinction correction. |
| Isotropic Becker-Coppens type I | Becker-Coppens secondary extinction set by the mosaic spread. |
| Isotropic Becker-Coppens type II | Becker-Coppens secondary extinction set by the domain radius. |
| Isotropic Becker-Coppens mixed | Becker-Coppens secondary extinction set by both the mosaic spread and the domain radius. |
| Isotropic Larson | Larson&#x27;s empirical coefficient, as SHELXL&#x27;s EXTI. |
| Anisotropic Larson | Larson&#x27;s anisotropic extinction tensor. |

[Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="extinction-mosaic-distribution">

### Mosaic distribution {#extinction-mosaic-distribution}

The shape of a Becker-Coppens crystal&#x27;s mosaic distribution.

| Option | Meaning |
| --- | --- |
| Gaussian | A Gaussian mosaic distribution. |
| Lorentzian | A Lorentzian mosaic distribution. |

[Names across interfaces](../user-guide/parameters.md#names-extinction)

</section>

## <span class="ed-reference-icon" data-reference-category="linked-structure" aria-hidden="true">&#62973;</span> Linked structure {#linked-structure}

The structures that contribute to the pattern, each with its scale.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="linked-structure-scale">

### Scale {#linked-structure-scale}

Scale factor of one linked structure&#x27;s (phase&#x27;s) pattern, the overall pattern scale when there is one structure (dimensionless; linear).

**Units:** dimensionless.

[Equation and conventions](diffraction.md#phase-fractions) · [Names across interfaces](../user-guide/parameters.md#names-linked-structure)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="linked-structure-structure-id">

### Structure {#linked-structure-structure-id}

The structure that contributes to the pattern.

[Names across interfaces](../user-guide/parameters.md#names-linked-structure)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="linked-structure-enabled">

### Enabled {#linked-structure-enabled}

Whether the structure contributes to the pattern.

[Names across interfaces](../user-guide/parameters.md#names-linked-structure)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="linked-structure-weight-fraction">

### Phase mass fraction {#linked-structure-weight-fraction}

The structure&#x27;s weight fraction in the sample, from the scales (Hill and Howard); computed, never edited.

[Names across interfaces](../user-guide/parameters.md#names-linked-structure)

</section>

## <span class="ed-reference-icon" data-reference-category="absorption" aria-hidden="true">&#61507;</span> Absorption {#absorption}

The absorption correction.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="absorption-abscor1">

### ABSCOR1 {#absorption-abscor1}

TOF sample absorption coefficient ABSCOR1 (muR = ABSCOR1 * lambda; refinable).

**Units:** Å⁻¹.

[Equation and conventions](corrections/absorption.md#eq-hewat) · [Names across interfaces](../user-guide/parameters.md#names-absorption)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="absorption-abscor2">

### ABSCOR2 {#absorption-abscor2}

TOF sample absorption lambda-power ABSCOR2 (round-tripped, held fixed; freeing it is a hard error).

**Units:** stored-only; no active calculation-unit convention.

**Stored only.** Retained in project input but not applied in this calculation.

[Equation and conventions](corrections/absorption.md#eq-hewat) · [Names across interfaces](../user-guide/parameters.md#names-absorption)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="absorption-mu-r">

### ΜR {#absorption-mu-r}

CW cylinder sample absorption mu*R (mu the linear absorption coefficient, R the cylinder RADIUS; evaluated at each reflection&#x27;s Bragg theta; refinable).

**Units:** dimensionless.

[Equation and conventions](corrections/absorption.md#eq-hewat) · [Names across interfaces](../user-guide/parameters.md#names-absorption)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="absorption-type">

### Type {#absorption-type}

The absorption correction.

| Option | Meaning |
| --- | --- |
| None | No absorption correction. |
| Cylinder (Hewat) | The Hewat (1979) polynomial for a cylindrical sample. |
| Cylinder (Lobanov) | The Lobanov and Alte da Veiga (1998) fit for a cylindrical sample. |

[Names across interfaces](../user-guide/parameters.md#names-absorption)

</section>

## <span class="ed-reference-icon" data-reference-category="preferred-orientation" aria-hidden="true">&#61774;</span> Preferred orientation {#preferred-orientation}

The March-Dollase preferred-orientation correction per structure.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="preferred-orientation-march-r">

### March-Dollase coefficient {#preferred-orientation-march-r}

March-Dollase coefficient r (FullProf Pref1, IUCr _pd_pref_orient_March_Dollase.r; 1 = no texture, &lt;1 platy, &gt;1 needle; must be &gt; 0; a fit parameter).

**Units:** dimensionless.

[Equation and conventions](corrections/orientation.md#eq-march-dollase) · [Names across interfaces](../user-guide/parameters.md#names-preferred-orientation)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="preferred-orientation-march-random-fract">

### Randomly oriented fraction {#preferred-orientation-march-random-fract}

Random (untextured) fraction mixed with the March-Dollase term (FullProf Pref2; a fit parameter).

**Units:** dimensionless.

[Equation and conventions](corrections/orientation.md#eq-march-dollase) · [Names across interfaces](../user-guide/parameters.md#names-preferred-orientation)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="preferred-orientation-structure-id">

### Structure {#preferred-orientation-structure-id}

The structure the correction applies to.

[Names across interfaces](../user-guide/parameters.md#names-preferred-orientation)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="preferred-orientation-index-h">

### Miller index h {#preferred-orientation-index-h}

The h index of the preferred-orientation direction.

[Names across interfaces](../user-guide/parameters.md#names-preferred-orientation)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="preferred-orientation-index-k">

### Miller index k {#preferred-orientation-index-k}

The k index of the preferred-orientation direction.

[Names across interfaces](../user-guide/parameters.md#names-preferred-orientation)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="preferred-orientation-index-l">

### Miller index l {#preferred-orientation-index-l}

The l index of the preferred-orientation direction.

[Names across interfaces](../user-guide/parameters.md#names-preferred-orientation)

</section>

## <span class="ed-reference-icon" data-reference-category="reflns" aria-hidden="true">&#61616;</span> Observed reflections {#reflns}

Which of a single crystal&#x27;s reflections count as observed, for its counts and R factors.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="reflns-threshold-sigma">

### Observed-reflection threshold {#reflns-threshold-sigma}

The multiple n of its su above which a single crystal&#x27;s reflection counts as observed; 2 when absent.

[Names across interfaces](../user-guide/parameters.md#names-reflns)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="reflns-threshold-basis">

### On {#reflns-threshold-basis}

Whether the observed threshold is on the intensity or the amplitude; the intensity when absent.

| Option | Meaning |
| --- | --- |
| I | The intensity: I &gt; n u(I). |
| F | The amplitude: F &gt; n u(F). |

[Names across interfaces](../user-guide/parameters.md#names-reflns)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="reflns-threshold-expression">

### Threshold {#reflns-threshold-expression}

The observed threshold as CIF writes it, such as I&gt;2u(I); a save writes it beside the counts and R factors it gives.

[Names across interfaces](../user-guide/parameters.md#names-reflns)

</section>

## <span class="ed-reference-icon" data-reference-category="scattering-source" aria-hidden="true">&#62930;</span> Scattering source {#scattering-source}

The published tables the scattering factors and lengths come from.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="scattering-source-xray-form-factor">

### X-ray form factors {#scattering-source-xray-form-factor}

The published table the X-ray atomic form factors come from.

| Option | Meaning |
| --- | --- |
| Waasmaier &amp; Kirfel (1995) | Waasmaier and Kirfel, Acta Cryst. A51 (1995) 416. |
| International Tables C (1992) | International Tables for Crystallography, Vol. C (1992). |

[Names across interfaces](../user-guide/parameters.md#names-scattering-source)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="scattering-source-xray-dispersion">

### X-ray dispersion {#scattering-source-xray-dispersion}

The published table the anomalous dispersion corrections come from.

| Option | Meaning |
| --- | --- |
| Cromer &amp; Liberman | Cromer and Liberman, calculated for the wavelength. |
| Sasaki (1989) | Sasaki, KEK Report 88-14 (1989). |
| International Tables C (1992) | International Tables for Crystallography, Vol. C (1992). |
| None | No anomalous dispersion correction. |

[Names across interfaces](../user-guide/parameters.md#names-scattering-source)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="scattering-source-neutron-scattering-length">

### Neutron scattering lengths {#scattering-source-neutron-scattering-length}

The published table the neutron scattering lengths come from.

| Option | Meaning |
| --- | --- |
| Rauch &amp; Waschkowski (2003) | Rauch and Waschkowski (2003), extended with the isotopes it lacks. |
| Sears (1992) | Sears, Neutron News 3 (1992) 26. |

[Names across interfaces](../user-guide/parameters.md#names-scattering-source)

</section>

## <span class="ed-reference-icon" data-reference-category="data-source" aria-hidden="true">&#62831;</span> Data source {#data-source}

The file the measured data were read from.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-source-file-name">

### Measured-data filename {#data-source-file-name}

The file the measured data were read from.

[Names across interfaces](../user-guide/parameters.md#names-data-source)

</section>

## <span class="ed-reference-icon" data-reference-category="data" aria-hidden="true">&#62263;</span> Measured data point {#data}

The measured pattern and the values calculated at each of its points.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-two-theta">

### Scattering angle {#data-two-theta}

The scattering angle of each point.

**Units:** deg.

[Names across interfaces](../user-guide/parameters.md#names-data)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-time-of-flight">

### Time of flight {#data-time-of-flight}

The time of flight of each point.

**Units:** µs.

[Names across interfaces](../user-guide/parameters.md#names-data)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-intensity-meas">

### Measured intensity {#data-intensity-meas}

The measured intensity.

[Names across interfaces](../user-guide/parameters.md#names-data)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-intensity-meas-su">

### Measured intensity uncertainty {#data-intensity-meas-su}

The standard uncertainty of the measured intensity.

[Names across interfaces](../user-guide/parameters.md#names-data)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-d-spacing">

### Interplanar spacing {#data-d-spacing}

The d-spacing of each point.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-data)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-intensity-calc">

### Calculated intensity {#data-intensity-calc}

The calculated intensity, the background included.

[Names across interfaces](../user-guide/parameters.md#names-data)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-intensity-bkg">

### Background intensity {#data-intensity-bkg}

The background at each point.

[Names across interfaces](../user-guide/parameters.md#names-data)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-calc-status">

### Calculation status {#data-calc-status}

Whether the point takes part in the calculation and the fit.

| Option | Meaning |
| --- | --- |
| Included | The point is calculated and fitted. |
| Excluded | The point lies in an excluded region and is not calculated. |

[Names across interfaces](../user-guide/parameters.md#names-data)

</section>

## <span class="ed-reference-icon" data-reference-category="data-calc" aria-hidden="true">&#61950;</span> Calculated point {#data-calc}

The calculated pattern the command line writes.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="data-calc-point-id">

### Point {#data-calc-point-id}

The index of the point in the calculated pattern.

[Names across interfaces](../user-guide/parameters.md#names-data-calc)

</section>

## <span class="ed-reference-icon" data-reference-category="pd-calc-overall" aria-hidden="true">&#61950;</span> Structure curves {#pd-calc-overall}

The structures the per-point curves follow.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="pd-calc-overall-component-presentation-order">

### Structure order {#pd-calc-overall-component-presentation-order}

The structures whose curves the per-point lists hold, in their order.

[Names across interfaces](../user-guide/parameters.md#names-pd-calc-overall)

</section>

## <span class="ed-reference-icon" data-reference-category="pd-calc" aria-hidden="true">&#61950;</span> Structure curve {#pd-calc}

Each structure&#x27;s calculated curve, one value per structure at every point of the pattern.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="pd-calc-component-intensities-net">

### Structure calc {#pd-calc-component-intensities-net}

Each structure&#x27;s calculated intensity at the point, the background excluded, in the order _pd_calc_overall.component_presentation_order gives.

[Names across interfaces](../user-guide/parameters.md#names-pd-calc)

</section>

## <span class="ed-reference-icon" data-reference-category="refln" aria-hidden="true">&#61498;</span> Reflection {#refln}

The Bragg reflections of each linked structure.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-structure-id">

### Structure {#refln-structure-id}

The structure the reflection belongs to.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-d-spacing">

### Interplanar spacing {#refln-d-spacing}

The d-spacing of the reflection.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-sin-theta-over-lambda">

### Sin θ/λ {#refln-sin-theta-over-lambda}

sin θ over λ of the reflection.

**Units:** 1/Å.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-index-h">

### Miller index h {#refln-index-h}

The h index of the reflection.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-index-k">

### Miller index k {#refln-index-k}

The k index of the reflection.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-index-l">

### Miller index l {#refln-index-l}

The l index of the reflection.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-f-calc">

### F calc {#refln-f-calc}

The calculated structure-factor amplitude.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-f-meas">

### F meas {#refln-f-meas}

The measured structure-factor amplitude, the square root of a single crystal&#x27;s measured F², as its chart plots it in F.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-f-squared-calc">

### F² calc {#refln-f-squared-calc}

The calculated squared structure factor.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-intensity-meas">

### Measured intensity {#refln-intensity-meas}

The measured squared structure factor of a single crystal&#x27;s reflection.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-intensity-meas-su">

### Measured intensity uncertainty {#refln-intensity-meas-su}

The standard uncertainty of the measured squared structure factor.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-intensity-calc">

### Calculated intensity {#refln-intensity-calc}

The calculated squared structure factor of a single crystal&#x27;s reflection.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-wavelength">

### Λ {#refln-wavelength}

The wavelength a time-of-flight single crystal&#x27;s reflection was measured at.

**Units:** Å.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-two-theta">

### Scattering angle {#refln-two-theta}

The Bragg angle of the reflection.

**Units:** deg.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refln-time-of-flight">

### Time of flight {#refln-time-of-flight}

The time of flight of the reflection.

**Units:** µs.

[Names across interfaces](../user-guide/parameters.md#names-refln)

</section>

## <span class="ed-reference-icon" data-reference-category="metadata" aria-hidden="true">&#61831;</span> Project {#metadata}

The project&#x27;s name, title, description and authors.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="metadata-name">

### Name {#metadata-name}

The project&#x27;s short name, which names its folder.

[Names across interfaces](../user-guide/parameters.md#names-metadata)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="metadata-title">

### Title {#metadata-title}

The project&#x27;s title.

[Names across interfaces](../user-guide/parameters.md#names-metadata)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="metadata-description">

### Description {#metadata-description}

What the project is about.

[Names across interfaces](../user-guide/parameters.md#names-metadata)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="metadata-authors">

### Authors {#metadata-authors}

The people the project and its report credit, separated by semicolons.

[Names across interfaces](../user-guide/parameters.md#names-metadata)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="metadata-path">

### Location {#metadata-path}

The project&#x27;s folder.

[Names across interfaces](../user-guide/parameters.md#names-metadata)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="metadata-created">

### Created {#metadata-created}

When the project was created.

[Names across interfaces](../user-guide/parameters.md#names-metadata)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="metadata-last-modified">

### Last modified {#metadata-last-modified}

When the project was last saved.

[Names across interfaces](../user-guide/parameters.md#names-metadata)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="metadata-timestamp">

### Timestamp {#metadata-timestamp}

A machine-readable time of the last save.

[Names across interfaces](../user-guide/parameters.md#names-metadata)

</section>

## <span class="ed-reference-icon" data-reference-category="su-format" aria-hidden="true">&#62030;</span> Standard uncertainties {#su-format}

How values with a standard uncertainty are written and shown.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="su-format-rule">

### Uncertainty rounding rule {#su-format-rule}

How a value with a standard uncertainty is rounded when it is written and shown.

| Option | Meaning |
| --- | --- |
| IUCr recommendation: 1 digit, or 2 from 10 to 19 | The IUCr recommendation 12: one significant digit in the uncertainty, two from 10 to 19. |
| Always 2 digits, 10 to 99 | Always two significant digits in the uncertainty, the practice the IUCr also admits. |

[Names across interfaces](../user-guide/parameters.md#names-su-format)

</section>

## <span class="ed-reference-icon" data-reference-category="report" aria-hidden="true">&#61788;</span> Report {#report}

Which report formats are saved, and what they leave out.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="report-html">

### HTML {#report-html}

Whether Save report writes the HTML report.

[Names across interfaces](../user-guide/parameters.md#names-report)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="report-pdf">

### PDF {#report-pdf}

Whether Save report writes the PDF report.

[Names across interfaces](../user-guide/parameters.md#names-report)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="report-cif">

### CIF {#report-cif}

Whether Save report writes the CIF report.

[Names across interfaces](../user-guide/parameters.md#names-report)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="report-html-offline">

### Embed chart libraries {#report-html-offline}

Whether the HTML report carries its chart libraries, so it opens offline.

[Names across interfaces](../user-guide/parameters.md#names-report)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="report-excluded">

### Excluded {#report-excluded}

The report sections left out.

[Names across interfaces](../user-guide/parameters.md#names-report)

</section>

## <span class="ed-reference-icon" data-reference-category="correlation-chart" aria-hidden="true">&#61450;</span> Correlation chart {#correlation-chart}

Settings of the parameter-correlation chart.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="correlation-chart-threshold">

### Threshold {#correlation-chart-threshold}

The smallest absolute correlation the chart shows.

[Names across interfaces](../user-guide/parameters.md#names-correlation-chart)

</section>

## <span class="ed-reference-icon" data-reference-category="pattern-chart" aria-hidden="true">&#61953;</span> Pattern chart {#pattern-chart}

Settings of the diffraction pattern chart.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="pattern-chart-x-axis">

### X-axis {#pattern-chart-x-axis}

The pattern chart&#x27;s horizontal axis.

| Option | Meaning |
| --- | --- |
| Measured axis | The experiment&#x27;s own axis: 2θ or time of flight. |
| d-spacing | The d-spacing of each point. |

[Names across interfaces](../user-guide/parameters.md#names-pattern-chart)

</section>

## <span class="ed-reference-icon" data-reference-category="calculator" aria-hidden="true">&#61932;</span> Calculator {#calculator}

The calculation engine an experiment names.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="calculator-type">

### Calculator {#calculator-type}

The calculation engine.

| Option | Meaning |
| --- | --- |
| crysta | The crysta engine. |

[Names across interfaces](../user-guide/parameters.md#names-calculator)

</section>

## <span class="ed-reference-icon" data-reference-category="minimizer" aria-hidden="true">&#62398;</span> Minimizer {#minimizer}

The minimizer and its settings.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="minimizer-type">

### Minimizer {#minimizer-type}

The minimizer.

| Option | Meaning |
| --- | --- |
| crysta | crysta&#x27;s own least-squares minimizer. |

[Names across interfaces](../user-guide/parameters.md#names-minimizer)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="minimizer-max-iterations">

### Max iterations {#minimizer-max-iterations}

The most iterations a fit may take.

[Names across interfaces](../user-guide/parameters.md#names-minimizer)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="minimizer-descent">

### Descent {#minimizer-descent}

The descent strategy of the minimizer.

| Option | Meaning |
| --- | --- |
| Ladder | The default descent. |
| Fast descent | A faster descent that takes fewer steps. |
| Fast descent with linear snap | The fast descent, solving the linear parameters exactly at each step. |
| Fast descent with guarded linear snap | The fast descent, keeping a linear snap only when it lowers χ². |
| Multi-start with pruning | Several starts, the worse ones dropped as the fit goes on. |

[Names across interfaces](../user-guide/parameters.md#names-minimizer)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="minimizer-chi-square-tolerance">

### Tolerance {#minimizer-chi-square-tolerance}

The relative change of χ² at which a fit stops.

[Names across interfaces](../user-guide/parameters.md#names-minimizer)

</section>

## <span class="ed-reference-icon" data-reference-category="fitting-mode" aria-hidden="true">&#61918;</span> Fitting mode {#fitting-mode}

How the experiments of a project are fitted.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fitting-mode-type">

### Fitting mode {#fitting-mode-type}

How the experiments of the project are fitted.

| Option | Meaning |
| --- | --- |
| Single experiment | The one experiment is fitted on its own. |
| Joint: all experiments at once | All experiments are fitted together. |
| Sequential: each from the previous | Each data file is fitted, starting from the previous result. |
| Independent: each from the same start | Each data file is fitted from the same start. |

[Names across interfaces](../user-guide/parameters.md#names-fitting-mode)

</section>

## <span class="ed-reference-icon" data-reference-category="refine-ls" aria-hidden="true">&#61636;</span> Fitted reflections {#refine-ls}

Which of a single crystal&#x27;s reflections a fit uses.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="refine-ls-threshold-sigma">

### Fitted-reflection threshold {#refine-ls-threshold-sigma}

The multiple n of its su above which a single crystal&#x27;s reflection is fitted; every reflection when absent.

[Names across interfaces](../user-guide/parameters.md#names-refine-ls)

</section>

## <span class="ed-reference-icon" data-reference-category="alias" aria-hidden="true">&#61483;</span> Alias {#alias}

Short names for parameters, used in constraints.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="alias-id">

### Alias {#alias-id}

The short name.

[Names across interfaces](../user-guide/parameters.md#names-alias)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="alias-parameter-unique-name">

### Parameter {#alias-parameter-unique-name}

The parameter the short name stands for.

[Names across interfaces](../user-guide/parameters.md#names-alias)

</section>

## <span class="ed-reference-icon" data-reference-category="constraint" aria-hidden="true">&#62764;</span> Constraint {#constraint}

Expressions that compute a parameter from others.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="constraint-id">

### Id {#constraint-id}

The name of the constraint.

[Names across interfaces](../user-guide/parameters.md#names-constraint)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="constraint-expression">

### Expression {#constraint-expression}

The expression, such as occ_Ba = 1 - occ_La.

[Names across interfaces](../user-guide/parameters.md#names-constraint)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="constraint-enabled">

### Enabled {#constraint-enabled}

Whether the constraint applies.

[Names across interfaces](../user-guide/parameters.md#names-constraint)

</section>

## <span class="ed-reference-icon" data-reference-category="joint-fit" aria-hidden="true">&#61633;</span> Joint-fit weights {#joint-fit}

Each experiment&#x27;s weight in a joint fit.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="joint-fit-weight">

### Weight {#joint-fit-weight}

The experiment&#x27;s weight in a joint fit.

[Names across interfaces](../user-guide/parameters.md#names-joint-fit)

</section>

## <span class="ed-reference-icon" data-reference-category="sequential-fit" aria-hidden="true">&#61643;</span> Sequential fit {#sequential-fit}

Which data files a sequential fit runs over.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="sequential-fit-data-dir">

### Data directory {#sequential-fit-data-dir}

The folder of the data files.

[Names across interfaces](../user-guide/parameters.md#names-sequential-fit)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="sequential-fit-file-pattern">

### Files {#sequential-fit-file-pattern}

Which files of the folder are fitted.

[Names across interfaces](../user-guide/parameters.md#names-sequential-fit)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="sequential-fit-reverse">

### Reverse {#sequential-fit-reverse}

Whether the files are fitted in reverse order.

[Names across interfaces](../user-guide/parameters.md#names-sequential-fit)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="sequential-fit-template-file">

### Template {#sequential-fit-template-file}

The experiment every file is fitted with.

[Names across interfaces](../user-guide/parameters.md#names-sequential-fit)

</section>

## <span class="ed-reference-icon" data-reference-category="sequential-fit-extract" aria-hidden="true">&#61616;</span> Scan extraction rule {#sequential-fit-extract}

Rules that read a value, such as a temperature, from each data file name.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="sequential-fit-extract-id">

### Id {#sequential-fit-extract-id}

The name of the value read from each file name.

[Names across interfaces](../user-guide/parameters.md#names-sequential-fit-extract)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="sequential-fit-extract-target">

### Extracted value name {#sequential-fit-extract-target}

What the value is stored as.

[Names across interfaces](../user-guide/parameters.md#names-sequential-fit-extract)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="sequential-fit-extract-pattern">

### Pattern {#sequential-fit-extract-pattern}

The pattern that finds the value in the file name.

[Names across interfaces](../user-guide/parameters.md#names-sequential-fit-extract)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="sequential-fit-extract-required">

### Required {#sequential-fit-extract-required}

Whether a file whose name does not match fails.

[Names across interfaces](../user-guide/parameters.md#names-sequential-fit-extract)

</section>

## <span class="ed-reference-icon" data-reference-category="edi" aria-hidden="true">&#61897;</span> File header {#edi}

The header every .edi file starts with.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="edi-schema-version">

### Schema version {#edi-schema-version}

The version of the .edi format the file follows.

[Names across interfaces](../user-guide/parameters.md#names-edi)

</section>

## <span class="ed-reference-icon" data-reference-category="report-file" aria-hidden="true">&#61787;</span> Saved report {#report-file}

The report files saved from this project.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="report-file-format">

### Format {#report-file-format}

The format of a saved report file.

| Option | Meaning |
| --- | --- |
| HTML | An HTML page with interactive charts. |
| PDF | A PDF document on A4 pages. |
| CIF | A CIF file with the official CIF names. |

[Names across interfaces](../user-guide/parameters.md#names-report-file)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="report-file-name">

### File {#report-file-name}

The saved report file, in the reports folder.

[Names across interfaces](../user-guide/parameters.md#names-report-file)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="report-file-saved">

### Saved {#report-file-saved}

When the report file was saved.

[Names across interfaces](../user-guide/parameters.md#names-report-file)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="report-file-project-last-modified">

### Project saved {#report-file-project-last-modified}

When the project was last saved before the report was.

[Names across interfaces](../user-guide/parameters.md#names-report-file)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="report-file-digest">

### Digest {#report-file-digest}

A checksum of the saved report file.

[Names across interfaces](../user-guide/parameters.md#names-report-file)

</section>

## <span class="ed-reference-icon" data-reference-category="fit-parameter" aria-hidden="true">&#61914;</span> Fit start value {#fit-parameter}

The values the last fit started from, kept so the fit can be undone.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-parameter-id">

### Parameter {#fit-parameter-id}

The parameter the start value belongs to.

[Names across interfaces](../user-guide/parameters.md#names-fit-parameter)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-parameter-start-value">

### Start value {#fit-parameter-start-value}

The value the last fit started from.

[Names across interfaces](../user-guide/parameters.md#names-fit-parameter)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-parameter-start-uncertainty">

### Start error {#fit-parameter-start-uncertainty}

The uncertainty the parameter had when the last fit started.

[Names across interfaces](../user-guide/parameters.md#names-fit-parameter)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-parameter-start-tied">

### Start tied {#fit-parameter-start-tied}

Whether the parameter was tied when the last fit started.

[Names across interfaces](../user-guide/parameters.md#names-fit-parameter)

</section>

## <span class="ed-reference-icon" data-reference-category="fit-result" aria-hidden="true">&#61528;</span> Fit result {#fit-result}

The outcome of the last fit.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-result-kind">

### Kind {#fit-result-result-kind}

What kind of fit gave the result.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-success">

### Success {#fit-result-success}

Whether the fit converged.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-message">

### Message {#fit-result-message}

The minimizer&#x27;s message.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-iterations">

### Iterations {#fit-result-iterations}

How many iterations the fit took.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-fitting-time">

### Time {#fit-result-fitting-time}

How long the fit took.

**Units:** s.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-reduced-chi-square">

### Reduced χ² {#fit-result-reduced-chi-square}

χ² divided by the degrees of freedom.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-objective-name">

### Objective {#fit-result-objective-name}

The quantity the fit minimized.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-objective-value">

### Objective value {#fit-result-objective-value}

The value of the objective at the end of the fit.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-n-data-points">

### Number of fitted observations {#fit-result-n-data-points}

How many data points the fit used.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-n-parameters">

### Parameters {#fit-result-n-parameters}

How many parameters the project has.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-n-free-parameters">

### Free parameters {#fit-result-n-free-parameters}

How many parameters the fit refined.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-degrees-of-freedom">

### Degrees of freedom {#fit-result-degrees-of-freedom}

The points minus the free parameters.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-covariance-available">

### Covariance {#fit-result-covariance-available}

Whether the fit gave a covariance matrix.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-exit-reason">

### Exit reason {#fit-result-exit-reason}

Why the fit stopped.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-prof-wr-factor">

### Rwp {#fit-result-prof-wr-factor}

The weighted profile R factor.

**Units:** %.

| Form | Units |
| --- | --- |
| <code>single crystal</code> | % |

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-prof-r-factor">

### Rp {#fit-result-prof-r-factor}

The profile R factor.

**Units:** %.

| Form | Units |
| --- | --- |
| <code>single crystal</code> | % |

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-prof-wr-expected">

### Rexp {#fit-result-prof-wr-expected}

The expected weighted profile R factor.

**Units:** %.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-prof-cr-factor">

### CRp {#fit-result-prof-cr-factor}

The background-corrected profile R factor.

**Units:** %.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-prof-cwr-factor">

### CRwp {#fit-result-prof-cwr-factor}

The background-corrected weighted profile R factor.

**Units:** %.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-profile-function">

### Profile {#fit-result-profile-function}

The peak profile the fit used.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-background-function">

### Background {#fit-result-background-function}

The background the fit used.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-descent">

### Descent {#fit-result-descent}

The descent strategy the fit used.

[Names across interfaces](../user-guide/parameters.md#names-fit-result)

</section>

## <span class="ed-reference-icon" data-reference-category="fit-result-bank" aria-hidden="true">&#61452;</span> Experiment fit result {#fit-result-bank}

The agreement factors of each experiment in the last fit.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-bank-n-data-points">

### Number of fitted observations {#fit-result-bank-n-data-points}

How many data points of the experiment the fit used.

[Names across interfaces](../user-guide/parameters.md#names-fit-result-bank)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-bank-prof-r-factor">

### Rp {#fit-result-bank-prof-r-factor}

The experiment&#x27;s profile R factor.

**Units:** %.

| Form | Units |
| --- | --- |
| <code>single crystal</code> | % |

[Names across interfaces](../user-guide/parameters.md#names-fit-result-bank)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-bank-prof-wr-factor">

### Rwp {#fit-result-bank-prof-wr-factor}

The experiment&#x27;s weighted profile R factor.

**Units:** %.

| Form | Units |
| --- | --- |
| <code>single crystal</code> | % |

[Names across interfaces](../user-guide/parameters.md#names-fit-result-bank)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-bank-prof-wr-expected">

### Rexp {#fit-result-bank-prof-wr-expected}

The experiment&#x27;s expected weighted profile R factor.

**Units:** %.

[Names across interfaces](../user-guide/parameters.md#names-fit-result-bank)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-bank-prof-cr-factor">

### CRp {#fit-result-bank-prof-cr-factor}

The experiment&#x27;s background-corrected profile R factor.

**Units:** %.

[Names across interfaces](../user-guide/parameters.md#names-fit-result-bank)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-bank-prof-cwr-factor">

### CRwp {#fit-result-bank-prof-cwr-factor}

The experiment&#x27;s background-corrected weighted profile R factor.

**Units:** %.

[Names across interfaces](../user-guide/parameters.md#names-fit-result-bank)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-bank-chi-square">

### Reduced χ² {#fit-result-bank-chi-square}

The experiment&#x27;s reduced χ².

[Names across interfaces](../user-guide/parameters.md#names-fit-result-bank)

</section>

## <span class="ed-reference-icon" data-reference-category="fit-result-phase" aria-hidden="true">&#61452;</span> Structure fit result {#fit-result-phase}

The agreement factors of each structure in each experiment.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-phase-bragg-r-factor">

### R Bragg {#fit-result-phase-bragg-r-factor}

The structure&#x27;s Bragg R factor in the experiment.

**Units:** %.

[Names across interfaces](../user-guide/parameters.md#names-fit-result-phase)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-result-phase-f-r-factor">

### R F {#fit-result-phase-f-r-factor}

The structure&#x27;s structure-factor R factor in the experiment.

**Units:** %.

[Names across interfaces](../user-guide/parameters.md#names-fit-result-phase)

</section>

## <span class="ed-reference-icon" data-reference-category="fit-parameter-correlation" aria-hidden="true">&#61449;</span> Correlation {#fit-parameter-correlation}

The correlations between the fitted parameters.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-parameter-correlation-id">

### Id {#fit-parameter-correlation-id}

The name of the correlation.

[Names across interfaces](../user-guide/parameters.md#names-fit-parameter-correlation)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-parameter-correlation-source-kind">

### Source {#fit-parameter-correlation-source-kind}

What kind of fit the correlation comes from.

[Names across interfaces](../user-guide/parameters.md#names-fit-parameter-correlation)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-parameter-correlation-parameter-unique-name-i">

### Parameter 1 {#fit-parameter-correlation-parameter-unique-name-i}

The first parameter.

[Names across interfaces](../user-guide/parameters.md#names-fit-parameter-correlation)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-parameter-correlation-parameter-unique-name-j">

### Parameter 2 {#fit-parameter-correlation-parameter-unique-name-j}

The second parameter.

[Names across interfaces](../user-guide/parameters.md#names-fit-parameter-correlation)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-parameter-correlation-correlation">

### Correlation {#fit-parameter-correlation-correlation}

The correlation coefficient between the two parameters.

[Names across interfaces](../user-guide/parameters.md#names-fit-parameter-correlation)

</section>

<section class="ed-parameter-entry" markdown="1" aria-labelledby="fit-parameter-correlation-file-path">

### File {#fit-parameter-correlation-file-path}

The data file of a sequential fit the correlation belongs to.

[Names across interfaces](../user-guide/parameters.md#names-fit-parameter-correlation)

</section>

## <span class="ed-reference-icon" data-reference-category="pd-block" aria-hidden="true">&#61897;</span> Report block {#pd-block}

The name each data block of the CIF report gives itself.

<section class="ed-parameter-entry" markdown="1" aria-labelledby="pd-block-id">

### Block {#pd-block-id}

The name of a data block of the CIF report, which a phase link refers to.

[Names across interfaces](../user-guide/parameters.md#names-pd-block)

</section>
