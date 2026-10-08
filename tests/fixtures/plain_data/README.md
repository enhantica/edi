Numeric cases are hand-constructed; each case documents its independent expected rows.

`default.cif` copies `_DEFAULT_CIF_BLOCK` verbatim from easydiffractionbeta
`easyDiffractionApp/Logic/Model.py`; content SHA-256 3c253b92eb89fe6630a545602fc7ce9e10e78e1cae6daf678c660d9c340d1a0f.
Upstream repositories: https://github.com/easyscience/easydiffractionbeta and
https://github.com/easyscience/diffraction-lib. Shared loader rules come from
`src/easydiffraction/io/ascii.py:load_numeric_block` and
`src/easydiffraction/datablocks/experiment/item/bragg_pd.py:_load_ascii_data_to_experiment`.
Named differences: clamped two-column sigma, Bragg nonpositive filtering,
comma separators, sorted first-duplicate selection. Header/malformed skipping
and tiny supplied sigma replacement follow upstream.

The lifecycle host seeds an instrument offset (CWL 0.125, TOF 7), peak width
0.0625, background intensity 4.25, dataset weight 2.5 and exclusions
[CWL 60, 61] / [TOF 9000, 9100]. Loads, Undo and reopen must retain them.
The lifecycle observer's positive control is hand-constructed from these
settings and the documented numeric rows. It tests the observer itself;
the separate native workflow gates exercise actual product actions.
