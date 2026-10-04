#  independent neutron witnesses

The public contract is `_scattering_source.neutron_scattering_length`, with
`sears1992` and `rauch2003ext`. Omitting it preserves the same default table as
`rauch2003ext`; declared presence remains faithful on save. This supersedes the
unnamed-default assertion under development hub owner decision 894c6a30f (2026-09-27).
The bare `rauch2003` proposal remains withdrawn: `ext` names the mixed table.

Numerical correctness comes from published values, never crysta output:

- Sears (1992), Neutron News 3(3), 26–37, natural Gd: Re(b) = 6.5 fm.
  NIST's transcription explicitly identifies this publication:
  https://ncnr.nist.gov/resources/n-lengths/list.html (Gd row; checked 2026-09-27).
  The full table value is 6.5 - 13.82i fm; the FullProf convention projects
  to the real component. This fixture exercises that real-only convention.
- Rauch & Waschkowski, Neutron Data Booklet, second edition (2003),
  chapter 1.1, natural Gd: Re(b) = 9.5 fm. Independent cross-check:
  the authors' TU Wien compilation, Gd page 85 (zero-index page 84),
  64-Gd row, 9.5 +/- 0.2 fm (75Wat3/75Wat2):
  https://www.tuwien.at/index.php?eID=dumpFile&f=106873&t=f&token=675a921c36f75850b2a9ed180277c3d7599b5ac7
  Booklet: https://www.ill.eu/documents/1013/NeutronDataBooklet.pdf.
  This tests the existing neutron diffraction real projection, not an
  energy-dependent complex-b model. The ADR must state the served convention.

The closed-form witness has one Gd atom in P m -3 m, a=2 Angstrom,
occupancy 0.7, Biso=0.8 Angstrom squared, wavelength 1.54 Angstrom,
scale 1, Gaussian FWHM 0.1 degrees. At the six {100} reflections,
F = 0.7*b*exp(-0.8/16), integrated intensity in barns = 6*F^2 /100 /
(sin(theta)*sin(2*theta)), theta=asin(1.54/4). The normalized Gaussian
is evaluated at offsets -0.01, 0, +0.01 degrees. These values deliberately
exercise non-unit occupancy, ADP, wavelength and width. No engine generates
the expected pattern. A second-site B witness tests the SIGN of Gd as well:
B at (1/2,1/2,1/2), occupancy 0.7, Biso 0.8, b=5.30 fm (Sears/NIST B row),
so F100 = 0.7*(b_Gd - 5.30)\*exp(-0.8/16).

## Named default reference (gate 6)

`rauch2003ext.json` is an independent numerical extract, not engine output.
Booklet real values were read from the held ILL Table 2 images, physical PDF
pages 14–23 (printed 1.1-8–1.1-17), whose SHA-256 is in the fixture.
The raw `nsftable` literal of the study-only periodictable 2.1.0 checkout
(commit 57d1cf5f, byte hash in the fixture) cross-checks every booklet value
except the publication-specific updates recorded per row. It supplies the
absorption cross sections for Im(b) = -sigma_a / (2000 * 1.798), in fm,
rounded to four decimal places like the declared table format. No product
module, generator, table or output supplies an expected value.

The extension citations are the publications in periodictable's module
bibliography: Haun (2020), Gehlhaar (2025/2026), and Snow (2020); exact DOIs
are in the fixture. Its C/O/Sn/Pb natural-element carrier assignments follow
periodictable's published compilation, not an independently recomputed
isotopic average. The reference covers every held element and 157Gd;
radioelements without a natural mixture follow the carrier's first isotope.

**Evidence distinction:** the superseded owner list included Sm, Eu, Gd, Er, Yb and
Lu, but their static b_c values equal Table 2. periodictable's docstring also
cites Lynn & Seeger (1990), doi:10.1016/0092-640X(90)90013-A, for separate
energy-dependent tables; `energy_dependent_init` does not replace static
b_c_complex. Those static values therefore retain Rauch & Waschkowski
provenance; attributing their static real values solely to Lynn would be
incorrect. Their individual publication links are tested just like the
changed elements. This feature does not enable energy-dependent scattering.

The all-element witness uses both a single site and interference with a
5.30 fm boron site to constrain magnitude AND sign. Each omitted calculation
and each declared calculation is checked against the closed form, then
against each other exactly. A common wrong table cannot pass this comparison.

The corrected `extended_elements` set is derived from the real-value difference
against Table 2 at the served four-decimal precision. This yields the nine
updated elements; Si rounding does not add an extension. The unchanged six
resonance entries retain their publication checks independently of that set.
