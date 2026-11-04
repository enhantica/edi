# 0070. Magnetic structures in edi

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
  operators, the parent group, the form factors and the moments in the cell. A moment component the site symmetry
  fixes or ties is shown and not fittable, as a symmetry-fixed coordinate is.
- **Viewer.** The structure view draws each magnetic atom's moment as an arrow, from the moments in the cell crysta
  computed. The toolbar shows or hides them (`_structure_view.show_moments`, saved with the structure only when
  stated). Appearance sets the arrow length per Bohr magneton and where the arrow sits (`_structure_view.moment_view`:
  through the atom, from its centre or from its surface). The shaft has one thickness at every length; the head is
  the standard one (0.6 Å long, 0.3 Å wide) shortened to at most 35 % of the arrow and narrowed with it, never below
  1.6 times the shaft, so a 1 μB arrow at the default scale keeps a visible shaft and a long arrow the standard head
  (the owner, 2026-11-03; the fraction read from captures of 1, 3 and 10 μB arrows). The toolbar's Atoms choice draws
  every atom, the crystal's asymmetric unit (for a magnetic structure, its parent group's, as crysta decides), the
  magnetic one, the magnetic atoms or none; moments follow the drawn atoms, and with none stay at every magnetic site.
- **Moment forms.** The moments table shows a moment in crystal-axis, Cartesian or spherical form, with |M|, each
  derived value with its s.u. After a fit the s.u. come from the fit's covariance (correlations, and the cell where it
  was fitted, included); before one they are propagated as if the components were uncorrelated, and the tooltip says
  which. An angle the moment does not fix shows a dash, with the reason in its tooltip.
- **Form factors** (the owner, 2026-11-03). The moments table chooses each site's ion, shared by its atom type. The
  Magnetic form factors group on Extra has one row per magnetic atom type: the type and its ion, read only; the
  approximation, ⟨j0⟩ alone, the dipole ⟨j0⟩ + C₂⟨j2⟩ or beyond the dipole up to ⟨j6⟩; and the coefficients it uses,
  edited and fitted like any other parameter. A coefficient the approximation does not use, or whose term the ion's
  table lacks, is greyed out. C₂'s tooltip gives the Landé g it stands for, C₂ = 2/g − 1. The core holds a type's
  form factor as a keyed row (`magnetic_form_factor`) only once an edit or a file declares it; a row back at the
  defaults (its own ion, ⟨j0⟩, every coefficient 0 and fixed) is removed, so the file says nothing it does not need.
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
