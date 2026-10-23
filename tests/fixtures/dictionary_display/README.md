# Independent display and CIF references

`upstream-names.json` contains diffraction-lib's name lists, read directly from
its committed handler inventory. `generate.py <diffraction-lib-checkout>` repeats
that read; neither crysta's dictionary nor its extraction scripts participate.
The inventory path, upstream anchor and source bytes' SHA-256 are in the file.

Display numbers use Python's `format`, with the exponent spelling specified by
ADR-0092's successor. Uncertainty witnesses are recommendation 12's worked
examples in https://www.iucr.org/resources/commissions/crystallographic-nomenclature/statdes/recomm.html.
Fraction witnesses are International Tables A: P63/mmc 2c (1/3,2/3,1/4),
Fm-3m 8c (1/4,1/4,1/4), and Pnma 4c (x,1/4,z).

The published structure is the unchanged COD 1000236 revision 130149 fixture in
`../c11_t48_real_cif/`. Its embedded publication and COD public-domain notice
remain the provenance. Dotted input is a notation-only transcription using the
vendored IUCr definitions; it preserves the published values and atom rows.

The second published structure is [COD 1000041](https://www.crystallography.net/cod/1000041.cif),
revision 130149: Abrahams and Bernstein, *Acta Crystallographica* 18 (1965),
926–932, DOI 10.1107/S0365110X65002244. Its cell is 5.62 Å in Fm-3m, with
Na1 at (0,0,0) and Cl1 at (1/2,1/2,1/2). Both downloaded COD files retain their
public-domain notices. `requirements.txt` pins the independent CIF parser.

`generate_structure_names.py <crysta-source>` reads the vendored dictionaries
itself and combines their aliases with the separately frozen upstream inventory.
It records the source digests in `structure_names.json`. Neither production
extraction is called. The import gate exercises each resulting name in both
notations at nontrivial values, and independently reads the published CIF with gemmi.
