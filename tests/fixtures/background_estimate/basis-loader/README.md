These bounded loader inputs use the committed CoSiO configuration and the public
CeO2 PEARL CLI configuration from the public
[edi repository](https://github.com/enhantica/edi), input commit
78f7297b09e408fd5732e2857d7a6ad95515caf7. Model parameters are inputs, not a fit
accuracy reference. Both products consume the same fixture bytes.

Authoring command, run from the example repository root:

```
python tests/fixtures/background_estimate/generate_basis_loader_inputs.py
```

The generator writes 65 measured samples of the stated closed form, excludes the
first and last two samples, and records the grid and independently expected
midpoint/endpoints in inputs.json. Tests omit actual file tags before loading;
no product-generated estimate is frozen as a correctness oracle. Coefficient
comparisons against a complete explicit-basis calculation test a lifecycle seam.
