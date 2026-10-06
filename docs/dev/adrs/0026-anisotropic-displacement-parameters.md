# ADR-0026 — Anisotropic displacement parameters

- **Status:** Proposed
- **Date:** 2026-10-06
- **Implementation:** 🟡 Partially implemented — the model, files, Python views, the app's Atomic displacement group
  and the ellipsoids are built; the Y2O3 beta page and its CLI project agree with FullProf
- **Priority:** High
- **Forward constraint (binding on new features):** a site's displacement stays in the type its file or its user
  declared, and every conversion between types is crysta's (its ADR-0081). edi computes no conversion, no
  site-symmetry tie and no equivalent value of its own.

## Context

diffraction-lib offers five displacement types (`Biso`, `Uiso`, `Bani`, `Uani`, `beta`) and an `atom_site_aniso`
category with one row per anisotropic site. Until now edi stored every site's displacement as B: it converted a
declared `Uiso` at load, so a saved file lost the type, and it refused the anisotropic types. crysta now holds all
five types and the tensor (crysta ADR-0081): it converts between them, ties the components a site's symmetry
fixes, and calculates and fits with them. edi has to carry the same model in its core, files, Python library and
app.

## Decision

1. **Model and files.** `AtomSite.adp_type` holds the declared type, `Biso` when a file declares none, and
   `adp_iso` holds the value in that type. An anisotropic site has a row of the structure's `atom_site_aniso`
   collection, keyed by the site id, with `adp_11` … `adp_23` in its type. Rows exist exactly for the anisotropic
   sites: a load refuses a row for any other site and an anisotropic site without one. A site's rename renames its
   row; removing a site removes it; duplicating one copies it.
2. **One conversion, crysta's.** Changing a site's type (`AtomSite.adp_type` from Python, the app's type cell)
   converts its values through crysta at the structure's symmetry-completed cell. A site not yet held by a structure
   is being declared, so it takes the type with its values as given. Whenever the sites change, the rows follow
   their types (`sync_atom_site_aniso`): a missing row is the tensor of the site's isotropic value, and an
   anisotropic site's `adp_iso` is its tensor's equivalent value, both computed by crysta.
3. **Ties.** Which tensor components a site's symmetry leaves free is crysta's `adp_ties`, reported through
   `structure_ties` like the cell and coordinate ties, so the app shows a tied component disabled and a fit refines
   only the free ones.
4. **App.** The Atomic displacement group edits the model: the type, the isotropic value of an isotropic site,
   and the tensor components of an anisotropic one, with the equivalent value shown read only. The structure view
   draws each anisotropic site's ellipsoid from its tensor, turned Cartesian with the cell's orthogonalisation
   matrix, U = M U\* Mᵀ.

## Consequences

- A declared `Uiso` round-trips as `Uiso`, as every other type does.
- The app's draft previews are gone: what the group shows is what is calculated and saved.
- An edit of a tensor component reaches the equivalent value at the next calculation, or when the sites change.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Convert in edi, with its own copy of the metric arithmetic | Rejected: two copies of one conversion drift, and crysta ADR-0081 makes U\* the only hub. |
| Keep storing B and convert at save | Rejected: the owner's rule is to stay in the type read until the user changes it. |
| Six tensor columns on `AtomSite` | Rejected: diffraction-lib and CIF keep the tensor in its own loop, keyed by site. |
