# Magnetic structure references

`data/collection/structures/cosio-magnetic.cif` is the ISODISTORT 6.12.2
input, not an edi output. Its six sites specify 4a, 4c, 4c, 4c, 4c, 8d,
with displacement forms 0,0,0; Dx,0,Dz (four times); Dx,Dy,Dz.
Those declarations supply the site and coordinate-freedom expectations.

`inputs.py` moves the origin by one quarter of a along x. It adds one
quarter to each site x and applies t' = t + p - R p to every operation.
The transform to standard BNS is a,b,c;1/4,0,0. Both the scalar item and
the BNS-source row of the transforms loop describe this same input.
The operation translations are in Gemmi's exact units of 1/24.

`dictionary.json` is an extraction of item identities from COMCIFS's
magnetic CIF dictionary 1.1.0-dev (2026-10-30); its SHA-256 identifies the
source bytes. Flag items unused by these cases are excluded from this vocabulary.
Regenerate with `export_dictionary.py <cif_mag.dic> dictionary.json`.
The scalar and loop transform definitions establish their meaning and the
canonical loop's source BNS. Crystal system and parent derived are not
defined items. Custom form-factor approximation/coefficient items are edi
extensions (ADR-0078); they do not authorise new items in COMCIFS categories.

Pnma's grey group is BNS 62.442, Pnma1'. Its pure time reversal maps every
axial moment M to -M at the same site, so the invariant moment is zero.
The ordinary Pnma magnetic group is BNS 62.441, as the ISODISTORT input
states. Removing time reversal returns the ordinary space group Pnma.
