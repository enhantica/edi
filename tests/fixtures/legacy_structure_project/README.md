# Saved project references

These are saved-file regression pins produced by [generate.py](generate.py) with the app before the Type column change.
Their file hashes are in `reference.json` and `compact-reference.json`.

`project/` retains the original cobalt project's complete data for the save/load gate. `compact-project/` uses the
geometry in [ui_input.js](ui_input.js): two cobalt sites and one oxygen site. The smaller input keeps UI actions focused
while retaining sites of the same element and a site without a magnetic moment.
