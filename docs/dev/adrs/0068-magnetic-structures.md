# 0068. Magnetic structures in edi

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
  site, three parameters each) and the rest of the magnetic description as one value, held as written. crysta reads,
  checks, calculates and writes all of it: the ties a site's symmetry imposes on its moment, the moments in the cell
  and the magnetic intensity come from crysta through the adapter, never from edi code.
- **Structure page.** Main holds the magnetic space group, the propagation vectors and the moments; Extra holds the
  operators, the parent group, the form factors and the moments in the cell. A moment component the site symmetry
  fixes or ties is shown and not fittable, as a symmetry-fixed coordinate is.
- **Viewer.** The structure view draws each magnetic atom's moment as an arrow, from the moments in the cell crysta
  computed. The toolbar shows or hides them (`_structure_view.show_moments`, saved with the structure only when
  stated). Appearance sets the arrow length per Bohr magneton and where the arrow sits (`_structure_view.moment_view`:
  through the atom, from its centre or from its surface). The toolbar's Atoms choice draws every atom, the crystal's
  asymmetric unit (for a magnetic structure, its parent group's, as crysta decides), the magnetic one, the magnetic
  atoms or none; moments follow the drawn atoms, and with none stay at every magnetic site.
- **Moment forms.** The moments table shows a moment in crystal-axis, Cartesian or spherical form, with |M|, each
  derived value with its s.u. After a fit the s.u. come from the fit's covariance (correlations, and the cell where it
  was fitted, included); before one they are propagated as if the components were uncorrelated, and the tooltip says
  which. An angle the moment does not fix shows a dash, with the reason in its tooltip.
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
