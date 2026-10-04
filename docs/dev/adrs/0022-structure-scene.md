# ADR-0022 — The structure scene: one description every structure renderer draws

- **Status:** Proposed (plan accepted 2026-10-02)
- **Date:** 2026-10-02
- **Implementation:** 🟡 Partially implemented — the core description and the app's Qt Quick 3D view are built; the
  notebook and terminal renderers land with, the ADP ellipsoids with
- **Priority:** High
- **Forward constraint (binding on new features):** a structure renderer draws only what `edi::present_structure`
  and `edi::scene_drawing` return and the values of `edi::structure_style_table()`. It computes no position, bond or
  distance, chooses no element colour or radius and keeps no atom, bond or cell data of its own. A new primitive,
  option or style is added to the description, never to one renderer.

## Context

The owner's visualisation decisions (2026-09-29): crysta computes every number a viewer shows; edi's core describes
the view; renderers only draw. crysta computes the structure categories: the symmetry-expanded atoms with their
copies at 0 and 1, their Cartesian coordinates and positions (`cluster_id`), the bonds with their distances and the
Cartesian transform. Three renderers draw the structure: the app (Qt Quick 3D), notebooks (three.js) and the
terminal. adds ADP ellipsoids.

diffraction-lib's structure view (`display/structure/`, at `cb2cda7b`) is the functional base (owner, 2026-10-02):
its scene primitives, features, atom views, colour schemes, sizing, shared-site wedges, bond drawing, home view and
options. ADR-0021 is the form this description follows: capture on the owner thread, a pure function, one style
table, renderers that only draw.

## Decision

### 1. A pure function of immutable input

`edi::capture_scene(structure)` takes, on the owner thread, the structure's stored geometry: crysta's own immutable
column buffers, shared and never copied, and each site's id and type symbol (`SceneSource`). It reads the geometry
only while `Structure::geometry_current()` is true and never calls a calculation; otherwise the source is not
current and carries no column. `edi::present_structure(source, options)` is a pure function that returns the atoms,
bonds, cell edges, axes, labels, legend and home frame (`edi/structure_scene.hpp`). It is Qt-free and holds no crysta
type.

### 2. edi computes no geometry

Every atom centre, bond end and bond distance is crysta's value, bit for bit: an atom's centre is its row's
`cartn_x/y/z`, a bond's ends are the two named rows' coordinates and its distance is `_geom_bond.distance`. The core
applies no symmetry operation, converts no fractional coordinate and searches no neighbour. The cell's basis is the
columns of crysta's row-major Cartesian matrix; the corners, the 12 edges, the drawn radius and the home frame are the
only arithmetic on crysta's numbers.

### 3. Atoms are positions

The scene has one atom per `cluster_id`, in the order of each position's first row, with one part per site at the
position. A shared site (lbco's La/Ba) is drawn as a sphere cut into wedges by relative occupancy, as diffraction-lib's
`OccupancyWedgeSphere`. When a position's occupancies sum to zero, its parts take equal shares, so every share is
finite and the shares sum to 1. The atom's colour and radius are its major part's.

### 4. One element table, with its source

`data/elements/element-styles.tsv` (118 elements, H to Og) is the only source of element colours and radii in edi,
embedded in the core at build time and read through `element_style_table()`. Its values are copied from
diffraction-lib's `elements.py` at `c0654956`, the commit crysta's covalent radii come from; its covalent column equals
crysta's `covalent-radii.tsv`. `data/elements/PROVENANCE.md` names the published sources and licences. The element of
a type symbol is its first capital letter and the lower-case letter after it (`Co2+` is Co, `2H` is H): the rule the
app already used for element colours, which differs from diffraction-lib's for a symbol that does not start with its
element. Fallbacks are diffraction-lib's: a missing VESTA colour is the Jmol one, a missing ionic radius the covalent
one, an unknown element pink and 1.0 Angstrom, and a substituted radius is reported.

### 5. Options

The options are diffraction-lib's, with its names, values and defaults: the colour scheme (`jmol`, `vesta`), the atom
view (`covalent`, `vdw`, `ionic`), the atom scale (drawn radius `atom_scale × sqrt(radius)`, default 0.3) and the
features (atoms all, asymmetric unit or none; bonds, cell, axes on; labels off).

### 6. The view in the core

The home view is diffraction-lib's: the longest axis across the screen, the middle one up, the shortest towards the
viewer, seen along `0.37·L + 0.24·M + 0.90·S`, fitted on the projected extent with diffraction-lib's margin and a top
band kept clear for the toolbar and legend. The orthographic and perspective projections, the pointer rules (drag
rotates, wheel zooms about the pointer, right drag pans) and the views along a, b and c are pure functions of the
core (`default_view`, `view_along`, `fitted_scale`, `project`, `rotated`, `zoomed`, `panned`), so the terminal
renderer and the app share them and the core tier tests them.

### 7. What a renderer places

`scene_drawing(scene, viewport)` returns, in bulk and in scene units, every instance a renderer places: one unit
sphere per drawn single-part atom, two half cylinders per bond in their ends' colours, one cylinder per cell edge, the
drawn shared sites by ordinal and the axis triad's arrows. It is the one place where the viewport enters the drawing's
dimensions (the cell edge's radius and the triad scale with the fitted half height). A hit names its atom by the hit
surface's own identity: a sphere by its instance index, a shared-site wedge by the ordinal its texture coordinate
carries; no distance to a centre is used. `hover_text` describes the atom as crysta gave it.

## Consequences

- The app's view is one renderer of this description (ADR-0017 §16): Qt Quick 3D instancing fed from C++, two draw
  calls for atoms and bonds whatever their number.
- Calls `present_structure` and draws the same atoms, bonds, cell and triad in three.js and in the terminal;
  binding it to Python is that task's.
- Extends `SceneAtom` with the ellipsoid axes and `AtomView` with the ADP view.

**Recorded gaps.**

- The view options are view state of the open project and are not read from or saved to the project file's
  `_structure_style` and `_structure_view` categories, which edi does not read.
- The view shows the unit cell only, crysta's stored unit. A wider window needs a calculation off the owner thread
  and a publication of its own; crysta and edi's core already take a window (`window_geometry`).

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
| --- | --- |
| Expand and bond in edi from the asymmetric unit, as diffraction-lib's `builder.py` does | Rejected: crysta computes every number; a second expansion would drift from crysta's. |
| One atom per expanded row | Rejected: a shared site would draw two coincident spheres and misreport the structure. |
| Keep the app's QML dictionary of element colours beside the new table | Rejected: two copies of one table agree only until one is edited (AGENTS.md principle 3). |
| The camera and pointer rules in QML | Rejected: the core tier runs on CI while the app tests are off, and the terminal renderer needs the same projection. |
