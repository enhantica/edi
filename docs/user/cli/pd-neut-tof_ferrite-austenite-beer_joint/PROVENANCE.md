# pd-neut-tof_ferrite-austenite-beer_joint — provenance

Ferrite and austenite (two Fe phases) against the two BEER (ESS) time-of-flight banks `expt_s2` and `expt_n2`,
fitted jointly, from the diffraction-lib tutorial `calibrate-beer-ess.py`.

`project/` is a byte-identical copy of `tests/fixtures/multiphase/beer/projects/initial/`, the tutorial's starting
point transcribed into the current schema. The fixture's `PROVENANCE.md` and `reference.json` record the source
commit, the data archive and every digest.

The tutorial ties each phase's scale across the two banks with constraints; this project and its reference leave
all four scales free instead, so the comparison covers what edi fits today.

`expected.json` holds the first-stage result as computed by CrySPY: an independent **reference**, not a crysta
regression pin. Its Rwp is taken over the included points of both banks (time of flight between 40 500
and 130 000 µs). crysta's time-of-flight intensity carries sin θ of the bank, CrySPY's does not, so crysta's
phase scales are CrySPY's divided by sin 45° when they describe the same pattern; the Rwp is unaffected.

