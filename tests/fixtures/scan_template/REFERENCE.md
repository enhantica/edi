# Measured-data reference

The D20 input files are retained verbatim from the saved scan fixture. Their
parsed measured columns follow the independent ASCII import convention in
[easyscience diffraction-lib](https://github.com/easyscience/diffraction-lib/blob/0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf/src/easydiffraction/datablocks/experiment/item/bragg_pd.py),
`Experiment._load_ascii_data_to_experiment`: round the axis to four decimals;
replace uncertainties below 0.0001 with 1.0. The two zero-uncertainty trailing
points therefore have uncertainty 1.0. This expectation is taken from the
reference loader, rather than from either library under test.

Template selection must retain the resulting parsed measured double values
exactly, including through serialization and reopen. Parameter invariants use
the saved model and immediate before/after state; no fitted result supplies an
expected value.
