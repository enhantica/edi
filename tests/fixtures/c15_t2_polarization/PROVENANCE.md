#  independent polarization references

The root `lif_single_polarized.*` files are byte-identical to diffraction-lib
`0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf`, under
`docs/docs/verification/fullprof/pd-xray-cwl_lif/`. `manifest.json` pins every byte.
`reference.tsv` extracts the calculated column, never the dummy observations.
`lif.edi` transcribes that fixed input using chemical occupancies (one). Its scale is converted analytically as explained below, without fitting.

`generate.py` is author-time only. FullProf 8.40 (Feb2026-ILL JRC) was run on those
unmodified inputs; `author-run/` retains its calculated profile, summary and log.
The manifest records the executable hash and invocation. Three newline characters
are needed here: the data-file prompt consumes one in addition to the final continue prompt.
No test executes FullProf. The separately preserved upstream outputs own the page's oracle.

The closed form is FullProf manual section 3.4:
https://www.ill.eu/sites/fullprof/downloads/Docs/FullProf_Manual.pdf
and diffraction-lib's independently committed convention in
`src/easydiffraction/analysis/corrections/polarization.py` at the revision above:
P = 1 - K + K cos²(2θ_m) cos²(2θ), with both angles in degrees.
The public Python members and .edi tags carry the prefix `setup_`:
`setup_polarization_coefficient` and `setup_monochromator_twotheta`.
The upstream page uses K=0.5, Cthm=0.8 and 2θ_m=26.5650511771 degrees.

`isolated.edi` is an analytical witness: a cubic cell with one Li site, narrow
Gaussian peaks, and no dispersion. At its isolated Bragg centres the corrected /
baseline intensity ratio must equal P. It is not a product-generated golden.
The 1 percent relative L2 FullProf bound retains 's fixed-parameter physical
acceptance criterion; measured page pins are authored only after implementation.

The page's reference directory follows 's three-part naming rule:
`knowledge/verification/fullprof/pd-xray-cwl_lif_single-polarization/`.
The CLI project remains `pd-xray-cwl_lif_single`, as the task packet declares.

## Characteristic X-ray scale convention

FullProf manual section 3.4 distinguishes characteristic radiation (Ilo=0) from
its general K formula: characteristic radiation uses `(1 + Cthm cos²(2θ)) L`,
which is twice the normalized K=0.5 formula. The vendored PCRs have Ilo=0;
Rpolarz does not control that characteristic-radiation branch. With Cthm=0,
 therefore agrees with L. With Cthm=0.8, the polarized reference is twice
`P L` at K=0.5. The fixed `lif.edi` witness consequently uses scale 0.02 for the
PCR's 0.01. This is a published normalization conversion, not a fitted or
product-generated value. The general nonidentity K gates retain `P L` and
the exact K=0 compatibility contract separately.

The upstream polarization page fits the scale before comparing. The executable
page gate permits that method (or the explicit scale conversion); disabling P
must still fail its real agreement assertion because scale cannot absorb the
angle-dependent shape. A method difference is documented by the implementation
under the task packet's existing obligation.

The  LiF CLI/corpus inputs did not exist before .
`generate_regression_pins.py` captures only these new inputs and their save
outputs as separately labelled post-feature regression pins in
`regression-pins.json`; it compares every input byte to the named Git commit
before capturing. The immutable pre-move pins remain unchanged. The crysta
file also pins the new corpus expected.json inventory entry. These values
claim serialization stability only; FullProf and closed form gates continue
to own physical correctness. Generate with the matching package and source,
with the repository on PYTHONPATH.
