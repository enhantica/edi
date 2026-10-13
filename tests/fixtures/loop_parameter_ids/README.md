# Loop parameter ids

The three input projects retain nonordinal ids for line-segment points and for
polynomial/Chebyshev terms, with one linked structure, preferred orientation and
two atom sites. `reference.json` captures diffraction-lib's names for the exact
hashed inputs at the recorded external revision. The hidden tests project those
names onto the numeric fields owned by the native model; text and integer
reference descriptors are not native fit parameters.

Regenerate in diffraction-lib's environment:

```
python generate_reference.py /path/to/diffraction-lib
python generate_action.py
```

The generator adapts schema/backend/profile tokens to the reference reader. It
views polynomial coefficients as Chebyshev coefficient storage solely to read
identities: it never fits, calculates, changes ids or converts a basis.

`name-by-position` is the owner-action witness made by `generate_action.py`.
Its expected names follow decimal rounding, independently of the product:
10.011/10.019 require two decimals, 24.873/25.111 require one, and isolated
30.87 and 72.321 require whole units. Its aliases, constraint, start values and
correlation endpoints distinguish a complete rename from a display-only change.
