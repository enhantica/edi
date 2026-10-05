# BEER ferrite/austenite reference with independent bank scales

The two tutorial expressions `n2_ferrite_scale = s2_ferrite_scale` and
`n2_austenite_scale = s2_austenite_scale` are omitted. Every other physics,
data, structure, free-parameter declaration and joint-fitting statement is
unchanged. Both N2 scales remain free. The original constrained capture remains in this repository's Git history.

The independent source is diffraction-lib commit
`0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf`, easydiffraction 0.19.1 and
CrySPY 0.12.1. The original tutorial digest is
`107c04c39dd0ba4cbdf8030e29194604f6b1709e059f59290159ceb11002662e`.
Measured data come from easyscience/diffraction commit
`35af7e9bf469a1ee4ecc889aff2279440b020c8a`; archive digest
`68bdc067bda10fa07bfa9546375fa1ac85dd575add401c6b813cbd066cdb7d5e`.

One authoring invocation of edi's visible `author_beer.py` executes both
stages in memory with `--without-scale-constraints`. Its pre-fit boundary
requires that exactly the two known expressions were omitted, there are no
active constraints, and all 56 parameters (40 backgrounds plus 16 others)
are free. It performs the initial fit once, fixes only backgrounds, then
performs the second fit once. It omits rendering and reuses the verified
archive. No saved-stage recovery or repeat fit occurred. Tests consume saved
artifacts and never execute diffraction-lib. The precise repository-relative
command, all package versions and raw capture digest are in reference.json.

`capture_beer.py` freezes the raw initial, stage-1 and stage-2 Edi trees.
Its included-window Rwp uses only saved external rows with calc_status=incl:
sqrt(sum(((measured-calculated)/sigma)^2) / sum((measured/sigma)^2)). The
library's reported Rwp uses a different excluded-row basis; both quantities
remain labelled in reference.json. The authoring command and captured outputs are recorded in `reference.json`
and `reference-run/`.

`generate_beer.py` transcribes the saved inputs to schema 3, embeds the
original measured columns at full precision, applies the tutorial's zero-
error-to-one convention, and omits four optional zero-valued size/strain
terms absent from crysta's dictionary. Unused alias declarations stay in the
raw capture; they are omitted from the unconstrained active model.

CrySPY's TOF scale prefactor omits sin(theta_bank); FullProf's convention
carries it. Therefore every phase scale value and its own SU map by
1/sin(theta_bank), using only the fixed scattering angle in the external
capture. Both BEER banks declare 2 theta = 90 degrees, giving sqrt(2). No
factor comes from crysta output. Every other parameter and the raw capture
stay unchanged by the conversion. The mapping gate also exercises a
60-degree scattering-angle witness (factor two).

The initial model has 56 free parameters; the second-stage corpus model
has 16, including separate ferrite and austenite scales in each bank. The
joint gate uses the declared `_fitting_mode.type joint` and `analysis.fit()`.
Every fitted parameter is compared against its own external one-SU bound,
with scale bounds converted consistently. Rwp has no reported uncertainty;
five percent relative permits independent optimizer termination. No
parameter is omitted or given a wider numerical tolerance.

Project id: pd-neut-tof_ferrite-austenite-beer_joint.
