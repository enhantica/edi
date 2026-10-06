# Native Darwin regression pins

Captured on Darwin arm64 in the retained cpp-ci toolchain by
[run 37536237373](https://github.com/enhantica/crysta/actions/runs/37536237373),
using harness `9481a808c7a2f0116ab09ec529248a07a61c873f`.
The native extensions were freshly built from each artifact's immutable source
commit and imported by their explicit physical paths. These are regression pins.
The original Linux pins remain unchanged; same-platform comparisons remain exact.

The JSON seals all four retained pre-rename project files and the original Linux
capture. Both TCH and FCJ pins retain their original sample populations. Edi also
records its separately built original engine source. The declared cross-platform
rounding bound remains a separate diagnostic; native byte identity is unchanged.
