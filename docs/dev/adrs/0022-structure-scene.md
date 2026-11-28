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
diffraction-lib's `elements.py` at `c0654956`, the commit crysta's covalent radii come from; its covalent column
equals crysta's `covalent-radii.tsv`. `data/elements/PROVENANCE.md` names the published sources and licences. The
element of a type symbol is its first capital letter and the lower-case letter after it (`Co2+` is Co, `13C` is C):
the rule the app already used for element colours, which differs from diffraction-lib's for a symbol that does not
start with its element. Deuterium is one atom however a file writes it: `D` and `2H` are both element `D`, so they take
one colour and one radius. The element table has no deuterium row, as diffraction-lib has none, so `D` takes
hydrogen's colours and radii, and a polyhedron never centres on it, as on H. What the view says in words (the legend,
an atom's hover text, the note naming atoms with a substituted radius) is the atom as the site writes it: its element
with any mass number and without the charge (`2H`, `D`, `13C`, but `Co` for `Co2+`). A structure writing both `D` and
`2H` has two legend entries of one colour. A declared scattering-length map may name deuterium under either spelling,
or both with one value: two values are refused where the map is read or edited (the `.edi` loop, the Scattering
lengths table, a FullProf import), with crysta's message.
Fallbacks are diffraction-lib's: a missing VESTA colour is the Jmol one, a missing ionic radius the covalent one, an
unknown element pink and 1.0 Angstrom, and a substituted radius is reported.

### 5. Options

The options are diffraction-lib's, with its names, values and defaults: the colour scheme (`jmol`, `vesta`), the atom
view (`covalent`, `vdw`, `ionic`), the atom scale (drawn radius `atom_scale × sqrt(radius)`, default 0.3) and the
features (atoms all, asymmetric unit or none; bonds, cell, axes on; labels off).

### 6. The view in the core

The home view is diffraction-lib's: the longest axis across the screen, the middle one up, the shortest towards the
viewer, seen along `0.37·L + 0.24·M + 0.90·S`, fitted on the projected extent of everything the view draws (the
atoms, the cell, and the axis arrows with their letters, whose size follows the fit; the owner, 2026-10-13) and shown at
0.9 of that (`default_view`'s magnification), so an even margin surrounds the drawing, with a top band kept clear for the
toolbar and legend. The orthographic and perspective projections, the pointer rules (drag
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

### 8. Bond settings and atom types

The Structure page's Extra tab has a Bond settings group (`_geom`): the minimum distance and the increment over the
two sites' covalent radii, each crysta's default until set, and a read-only table of the bonds crysta found with
them, the same `_geom_bond` rows the view draws. A negative or unreadable value leaves the setting as it was. The
generic `_geom_bond` group is not shown, so the bonds appear once.

A site's type is picked from the types crysta's scattering table holds for each experiment linking the structure:
the neutron table of its scattering-length source (elements and isotopes with a length), or the X-ray form-factor
table of its source (elements, ions, and `D` and `2H`, which take hydrogen's form factor). With both probes linked the
list is their union, sorted; with no experiment linked it is the elements a new atom may take, and `D` and `2H`. crysta
lists no X-ray table, so each element and each charge from 1 to 9 is asked for once per source. Every entry carries its
element's colour (§4). A type the list does not hold is taken when typed in the list's search field and Enter is
pressed, if every linked experiment computes with it in its selected source (`atom_type_computes`): any isotope of a
listed element with X-rays (`13C`), a type with a length in the neutron source (found as a calculation finds it, so an
ion by its element). With no experiment linked both default tables must compute with it. An entry spelled as typed
still wins over the typed text. A type outside the list, as a file may state it, is kept and shown as it is.

### 9. Coordination polyhedra

The toolbar's polyhedron button switches coordination polyhedra on; the Appearance group sets their colour, opacity
and extent while they are on (the owner, 2026-11-16). They are drawn round each drawn metal
atom (any element but hydrogen, the noble gases and the non-metals that usually sit at the corners: B, C, N, O, F, Si,
P, S, Cl, As, Se, Br, Te, I) with at least four bonded neighbours among those non-metals, the convex hull of their centres from
the same `_geom_bond` rows (§2: no neighbour search, and the polyhedra follow the bond settings of §8). A flat face of
more than three corners is one fan of triangles, so a see-through face is drawn once; corners all in one plane enclose
no volume and make no polyhedron. Each polyhedron takes its centre atom's colour, or grey; its opacity is 0.5 by
default. Bonds can be hidden while the polyhedra stay. Each structure saves these settings with the rest of its
appearance as `_structure_view.polyhedra`, `polyhedra_colour`, `polyhedra_opacity`, `polyhedra_extent`,
`polyhedra_centres`, `polyhedra_corners` and `polyhedra_max_distance`, each once crysta's dictionary declares it; until
then that setting lasts for the session, and a file without it shows the default. The extent is "inside the cell", the
corners being the drawn atoms, or "complete for atoms in the cell": each pair of sites bonds up to the longest bond the
rows list between them, or the maximum distance when one is set, and a centre takes every atom that near in whichever
cell it sits, so its polyhedron is whole; the corners outside the cell are not drawn as atoms.

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


## One shared-site mesh policy across renderers

The first native wedge implementation, app SharedSiteGeometry::setSites, now delegates its tessellation to structure_scene's shared_site_mesh. That existing scene owner also supplies offline report meshes, replacing the report's separate wedge loop. One function owns fraction finiteness/clamping, segment/ring minima, angular coverage, skipped zero parts, vertex/triangle order, cumulative start angle, native pick ordinal, and bounds. No second geometry controller or scientific calculation is introduced.

Renderer precision remains explicit. Qt supplies the same actual QVector3D float-normalized/cross-product basis and receives the same float intermediates, positions/normals, pick UVs, linear RGB, index layout and bounds. Its QQuick3DGeometry buffer/attributes/update/site-count signal remain the adapter. The report profile preserves the pinned THREE 0.160.0 double normalization, normal accumulation order and SRGBToLinear constants, then its renderer casts through the original Float32BufferAttribute boundary. Original raw report null-to-number conversion is applied before browser-profile arithmetic; derived non-finite values use the report renderer-number codec. These profile choices are fixed representation contracts of the two existing renderers, not user policies or feature fallbacks. The shared kernel refuses an out-of-range site before dereferencing any site, across both public renderer callers. Native/platform/render equivalence checks follow source completion.
