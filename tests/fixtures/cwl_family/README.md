The retained `tch-regression-*` and `tch-dispatch-*` captures keep their original
source, physical inputs and dispatch rounding guards. They are regression pins.

`fcj-adr0110.json` is a separate FCJ-only regression pin for crysta's continuous
axial-offset integral (algorithm b2022d22), which intentionally differs from
FullProf's Prof_Val model. It replaces the older Prof_Val-based FCJ value expectation, without
changing any physical input or comparison tolerance. Sample 3 changes from
14.287119662628045 to 14.940566878127138. TCH retains its earlier pin.

Generate it with the qualified edi extension and its linked SDK:

```
python -m tests.fixtures.cwl_family.capture_fcj_pin --engine-source /path/to/crysta
```

After a description-only edit, refresh the cause and generator digest with
`python -m tests.fixtures.cwl_family.capture_fcj_pin --refresh-description`.
This first verifies the existing seal and preserves every captured sample and
the execution provenance. Recompute the canonical JSON seal afterward.

The generated record binds the SDK, module, source, generator and all input hashes.
Its canonical JSON digest is sealed by `FCJ_MODEL_SEAL` in the comparison helper.
The recorded platform is the actual Linux capture. A different build or platform
uses the existing ADR-0057 bound (relative 5e-9, absolute 5e-10); the same captured
build remains byte-exact. This pin makes no independent physics-correctness claim.
