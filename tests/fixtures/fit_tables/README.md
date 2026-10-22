# Saved-curve agreement reference

`generate.py` runs crysta on the committed five-bank NCAF input and saves its
curves. `reference.json` records the engine revision and the input path.
The generator then computes the profile factors directly from the saved
included rows, with weights `1 / sigma²`:

- Rp: `sum(abs(y - calc)) / sum(abs(y))`.
- Rwp: `sqrt(sum(w * (y - calc)²) / sum(w * y²))`.
- Rexp: `sqrt((N - P) / sum(w * y²))`.
- cRp and cRwp: the same numerators, using `y - background` in the denominators.

`P` counts the free numeric tokens in the input structures and experiments.
The global row pools the observations before computing a factor. It does not
average the bank percentages. A separate test recomputes all five definitions
from the saved files.

The displayed duration of 1.3 seconds, iteration count and phase factors are
explicit display inputs. They are not measurements of the reference fit.
The `one` project keeps only bank 1 to test omission of the duplicate global row.
The brief's bank-1 percentages are checked with a 0.02 percentage-point bound;
the independently fitted Rwp is 4.65 rather than the brief's rounded 4.66.
