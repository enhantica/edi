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

`fetch_published.py` reproduces both CIF fixtures from their pinned COD sources.
`published_sources.json` records the downloaded and normalized digests. The only
normalization replaces COD's local SVN URL comment with its public COD URL;
all data and the public-domain notice remain. `--check` checks the committed
fixtures without network access.

## Coordinate-derived Wyckoff letters

The expected letters in `wyckoff_sources.json` are transcribed from International
Tables for Crystallography (2006), volume A: groups 194 (pp. 600–601),
199 (pp. 612–613), 225 (pp. 688–689), and 227 origin choice 2 (pp. 700–701).
The consulted volume is [available here](https://ncm.unn.ru/files/2021/01/International-Tables-for-crystallography.pdf).
No engine Wyckoff table or classifier generates this reference. In particular
227:2 has 16d (1/2,1/2,1/2), 16c (0,0,0), 48f (x,1/8,1/8),
and 8b (3/8,3/8,3/8); group 199 includes the general position 24c.

`fetch_wyckoff.py` fetches the pinned external diffraction data CIF for
Tb2Ti2O7 and COD 9008506 (Wyckoff, Crystal Structures 1, 1963) for magnesium.
It keeps public source URLs in COD headers. `--check` verifies the local pins
without fetching. Published NaCl and elpasolite witnesses use the COD fixtures
already described above. Hidden gates remove any letter and multiplicity
columns before import; the publication supplies coordinates, not expected letters.

The owner supplied `owner_tbti.cif` on 2026-10-23 after the dev web app
saved missing Wyckoff letters as `.` and could not reopen its own `.edi`.
`capture_owner.py SOURCE` reproduces this byte-pinned capture; without an
argument it checks the pin. Its expected letters use the same independent
International Tables 227:2 representatives, not the owner app output.
The save/reload gate covers every published witness and this exact file, in
both notations and through each Python import entrance.

## Display and report references

`generate_formats.py` (crysta) applies Python formatting to the reviewed
per-category numeric witnesses; `reference.py` normalizes signed zero and
exponents as I4 specifies. `generate_metadata.py DICTIONARY_YAML` reads names,
units, categories and options directly from YAML, independently of the
production generated tables. The edi `adapt_display.py DICTIONARY_YAML`
keeps the existing frozen input oracle and derives only its new displayed
spellings, reading measured scan intervals from the original input parser.
`generate_experiment_names.py CRYSTA_SOURCE` reads the official dictionaries
and the frozen upstream inventory for the existing experiment CIF importer
(instrument and peak); other experiment categories are exercised through
their external EDI names, without expanding the pdCIF importer scope.

IUCr recommendation 12 supplies 1.54249 ± 0.01532 → 1.542(16) and
2.16352 ± 0.00481 → 2.164(5); the admitted alternative gives 2.1635(49).
See [IUCr recommendations](https://www.iucr.org/resources/commissions/crystallographic-nomenclature/statdes/recomm).
International Tables special-position representatives supply exact fractions.
CIF reports are parsed by gemmi; its small-structure convenience converter
is DDL1-only, so DDLm values are read through its notation-neutral CIF parser.
Expected tensor values are hand-written in their native convention.
