# 0078. Magnetic structures in edi

- **Status:** Accepted
- **Date:** 2026-11-03
- **Implementation:** 🟡 Partially implemented — the model, the `.edi` reading, the moment ties, the Structure page's
  categories and the viewer's arrows; pending: the dedicated Main groups, the Extra groups, the Analysis filter and the
  magCIF import from the app
- **Priority:** High

## Context

crysta describes a commensurate magnetic structure by its magnetic space group, its signed operators, the parent group
and propagation vectors, a moment per magnetic site and a magnetic form factor per atom type, and it calculates the
moments of every atom in the cell and the magnetic intensity of a neutron pattern. edi has to hold, show and draw these
without computing any of them itself.

## Decision

- **Core ownership.** A structure holds its moments as a keyed loop of rows (`atom_site_moment`, one per magnetic
  site, three parameters each), its form factors as another (`magnetic_form_factor`, one per declared type, three
  coefficients each) and the rest of the magnetic description as one value, held as written. crysta reads,
  checks, calculates and writes all of it: the ties a site's symmetry imposes on its moment, the moments in the cell
  and the magnetic intensity come from crysta through the adapter, never from edi code.
- **Structure page.** Main holds the magnetic space group, the propagation vectors and the moments; Extra holds the
  operators, the parent group, the form factors and the moments in the cell. They appear as soon as the structure is
  Magnetic, before any site has an ion. A moment component the site symmetry fixes or ties is shown and not fittable, as a
  symmetry-fixed coordinate is. The moments table's ion choices follow the site's element: a new element drops a moment
  it has no magnetic ion for, and a form factor row for an element no site has goes. Add vector appends k = 0,0,0 for
  the user to edit. A change the structure cannot take (a k its cell cannot carry, a magnetic group or Setting crysta
  refuses) is not made: the field keeps its value and the reason shows in plain words in the app's error popup and the
  Messages center, never as a lasting label. Setting shows the dictionary default `a,b,c;0,0,0` when a file gives no
  transform.
- **Viewer.** The structure view draws each magnetic atom's moment as an arrow, from the moments in the cell crysta
  computed. The toolbar shows or hides them (`_structure_view.show_moments`, saved with the structure only when
  stated). Appearance sets the arrow length per Bohr magneton and where the arrow sits (`_structure_view.moment_view`:
  through the atom, from its centre or from its surface). The shaft has one thickness at every length; the head is
  the standard one (0.6 Å long, 0.3 Å wide) shortened to at most 35 % of the arrow and narrowed with it, never below
  1.6 times the shaft, so a 1 μB arrow at the default scale keeps a visible shaft and a long arrow the standard head.
  The toolbar's Atoms choice draws every atom, the crystal's asymmetric unit (for a magnetic structure, its parent
  group's, as crysta decides), the
  magnetic one, the magnetic atoms or none; moments follow the drawn atoms, and with none stay at every magnetic site.
- **Moment forms.** The moments table shows a moment in crystal-axis, Cartesian or spherical form, with |M|, each
  derived value with its s.u. After a fit the s.u. come from the fit's covariance (correlations, and the cell where it
  was fitted, included); before one they are propagated as if the components were uncorrelated, and the tooltip says
  which. An angle the moment does not fix shows a dash, with the reason in its tooltip. Every form takes its s.u.
  from crysta's one function: a free component whose fitted s.u. is undefined is never shown or used as 0, so any value
  that depends on it shows an undefined s.u., and a missing correlation withholds the s.u. it would need rather than
  falling back to uncorrelated propagation. A component no fitted parameter moves contributes nothing; a component
  tied by symmetry or set by a constraint takes its s.u. from the parameters it follows, whatever its free flag says.
- **Form factors.** The moments table chooses each site's ion, shared by its atom type. The Magnetic form factors group
  on Extra has one row per magnetic atom type: the type and its ion, read only; the
  approximation, ⟨j0⟩ alone, the dipole ⟨j0⟩ + C₂⟨j2⟩ or beyond the dipole up to ⟨j6⟩; and the coefficients it uses,
  edited and fitted like any other parameter. A coefficient the approximation does not use, or whose term the ion's
  table lacks, is greyed out. C₂'s tooltip gives the Landé g it stands for, C₂ = 2/g − 1. The core holds a type's
  form factor as a keyed row (`magnetic_form_factor`) only once an edit or a file declares it; a row back at the
  defaults (its own ion, ⟨j0⟩, every coefficient 0 and fixed) is removed, so the file says nothing it does not need.
- **Crystal or Magnetic.** The Structures table has a column after Type: Crystal or Magnetic, for an atom-based
  structure. Create makes Crystal, and a Crystal
  structure shows no magnetic group, the moments included. Switching to Magnetic sets the grey group of the current
  space group (Pnma → Pnma1′, BNS 62.442): every moment is zero by symmetry until a magnetic subgroup is chosen (CoSiO:
  Pnma, 62.441). Switching back to Crystal sets the magnetic group's own space group (time reversal ignored) and drops
  the moments after a confirmation. A magnetic CIF opens as Magnetic.
- **Magnetic space group** replaces Space group for a Magnetic structure, built like it: Number BNS and Name BNS as two
  linked, searchable fields (`_space_group_magn.number_BNS`, `.name_BNS`), and Setting as the transform to the BNS
  standard, `a,b,c;0,0,0` by default, in place of the IT code. It is read from either
  `_space_group_magn.transform_BNS_Pp_abc` or the `_space_group_magn_transforms` loop and written as the loop, as
  ISODISTORT writes it. Crystal system is shown read only and not saved (the dictionary has no item for it). On Extra,
  a separate read-only group shows the derived symbols, saved as the dictionary's `_space_group_magn` items: the UNI
  symbol, the OG number and name and the UNI point-group symbol. A Litvin point-group number supplied by a file is
  kept and written back unchanged; it is not derived. Extra shows only that supplied value, blank when absent.
  The parent space group is always present on Extra for a Magnetic structure, under its own heading
  (`_parent_space_group`); a file without one gets the magnetic group's
  own space group. Magnetic space group takes Space group's place, above Cell, in the sidebar and in the saved file's
  category order, and Propagation vectors follow it on Main: the vectors the file gives, else the one the magnetic group
  gives (k = 0 for a group in its parent's cell), never blank.
- **Site symmetry from the magnetic group.** For types I–III the family group (the operations
  with time reversal ignored) is the ordinary space group whose IT number is the BNS number's first part, in the
  setting the BNS transform gives. edi derives that table setting when it reads the structure and gives it to crysta
  as the structure's space group, so Wyckoff letters, multiplicities and coordinate ties come from the table and the
  cell and positions stay fittable. No `_space_group` is written for a Magnetic structure. A type
  IV group (its anti-translation makes the family a different lattice) and a setting the table does not hold keep the
  operators-only mode below.
  Legacy files that also declare `_space_group` follow the same family resolution when they give a BNS number;
  that older declaration must not select different tensor ties. Resolve the magnetic family before completing
  displacement tensors, including when a tensor row is missing. Without a BNS number, a matching declared family
  identifies the magnetic group before a save drops the declaration.
  Bundled magnetic CLI inputs retain an explicit matching family declaration for compatibility with readers that
  do not infer the family from BNS metadata, including the independently loaded engine references. The canonical
  writer still omits it; both input forms must load with the same ties and intensities.
- **Files.** Each sidebar group maps to one magnetic CIF category, as the crystal groups map to theirs (COMCIFS
  magnetic CIF dictionary 1.1.0-dev). `_parent_space_group.derived`, which the dictionary does not define, is an edi
  extension; the magnetic form factors keep the dictionary's `_atom_type_scat.neutron_magnetic_j0`…`_j6` coefficients
  where they apply, with the approximation and C₂ as edi's extension.
- **Symmetry from the operators** (2026-11-08). When a structure's magnetic operators form no table setting (a type IV
  group, a setting the table does not hold), crysta
  decides it once and edi reads that decision: no position, cell or displacement ties, the cell and positions not
  fittable, no Wyckoff letter (the site table shows none, and the multiplicity is the operators' orbit), and an
  anisotropic site refused, with the reason, at load, at the type change and at the group selector, which then keeps
  the prior model.
- **The magnetic popup** (2026-11-26). Crystal → Magnetic on an atom-based Crystal structure opens a popup instead of
  setting the grey group; Cancel changes nothing. It takes a propagation vector (crysta's presets, k = 0 first, or
  three exact fractions), the magnetic sites (ticked by default where the element has a magnetic form factor), and
  whether to add non-zero starting moments. crysta finds the magnetic groups k allows (crysta ADR-0137) off the GUI
  thread; the popup draws them as rows of maximal groups and their subgroups with the covering edges, each node with
  its BNS symbol and number, `#n` for a second embedding, its type, FM when a net moment is allowed, and the allowed
  moment components of each split site. Greyed nodes (groups without moments, unidentified classes) cannot be
  selected. **Add** makes one structure per selected group, named `<parent>_<BNS>` (a second embedding `_2`), and, as
  one undoable change, links each to every powder experiment linking the parent at scale S/N² (N parent cells), only
  the first enabled, keeps the parent's link disabled, and carries a March-Dollase texture row with its axis in the
  child's basis. A texture axis component above 1000, a child that cannot be built, or a link to a single-crystal
  experiment refuses the whole Add, naming the reason.
- **Find k from data.** Beside the k list, Find k from data offers each powder experiment linking the parent whose
  kept fit still matches its inputs (recorded when a fit is kept, compared again before a row is chosen; Calculate
  records nothing). It lists the peaks the fit leaves unexplained, ticked by default, and ranks propagation vectors
  for the ticked ones by crysta's search (crysta ADR-0137 A11). Only a buildable row can be chosen; it sets k. A row
  that needs more than 24 parent cells, is underdetermined or incommensurate at this resolution says so.
- **Picking a BNS group in place.** The Number BNS and Name BNS fields of a Magnetic structure take another group
  only within the structure's cell, its propagation vectors and its atoms (crysta's `admit_magnetic_space_group`);
  otherwise the refusal points to Crystal → Magnetic.
- **Identity.** The magnetic description and the moments are inputs of the structure's geometry and of every
  calculation it takes part in; a structure without them keeps its identity and its saved bytes.

## Consequences

- A magnetic structure loads, saves and calculates through the same paths as any other structure.
- The moments are fitted like any other parameter, with crysta's derivatives.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Drawing moments from the site rows with edi's own symmetry | Rejected: edi computes no positions or symmetry images; crysta's moments in the cell are the one source |
| The arrow length saved in the project | Rejected: how the app looks is an app setting, not project data |
