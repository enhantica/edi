# BEER behavior inputs and archived authoring capture

Only two-phase/two-bank load, joint fit, independent phase scales and exact
save/reopen behavior are tested here. No parameter, Rwp, profile, scale or
offset is compared with CrySPY. The historical CrySPY capture is retained as
input provenance only; it is no longer an agreement oracle. Its offset
expectation and convention artifact were removed.

The owner's replacement FullProf project and authoring outputs are archived
in edi's `knowledge/fitting/fullprof/pd-neut-tof_duplex-beer_pseudo-voigt/`;
its all-fixed twin is under `knowledge/verification/fullprof/` with the same
id. Those artifacts are not used by these tests. Activation is deferred until
shared site-parameter constraints are available. Both owner data files are
byte-identical to the measured BEER files already retained in `data/`.

The existing `projects/initial` vehicle has two Fe structures and two TOF
banks, with four independent free phase scales. Values merely initialize the
model; no captured result supplies a correctness expectation. Forty background
points are free in its first fit and fixed in its second. The remaining free
parameter count is derived from the model's declarations. The gates require
convergence, finite scales, improved residuals and exact persistence.

Measured source: easyscience/diffraction commit
`35af7e9bf469a1ee4ecc889aff2279440b020c8a`, archive SHA256
`68bdc067bda10fa07bfa9546375fa1ac85dd575add401c6b813cbd066cdb7d5e`.
