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
