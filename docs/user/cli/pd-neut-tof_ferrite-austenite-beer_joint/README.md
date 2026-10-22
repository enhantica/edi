---
title: Ferrite and austenite on BEER, joint
description: >-
  Two Fe phases, ferrite and austenite, against two BEER (ESS) time-of-flight neutron banks, fitted jointly from
  the starting values of a FullProf project, each phase's scale free in each bank.
---

# Ferrite and austenite on BEER, joint

Two Fe phases, ferrite (body-centred) and austenite (face-centred), against two BEER (ESS) time-of-flight neutron
banks, `expt_s2` and `expt_n2`, fitted jointly. Each bank sums both phases' patterns, each with its own scale.

## Run it

```bash
python -m edi fit docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back. The app opens the same project
from its Examples list.

## What is checked

The starting values are those of the owner's FullProf project for these data ([PROVENANCE.md](PROVENANCE.md)).
CI and `pixi run verify` run this project through `python -m edi` (`tools/checks/cli_projects.py`) and check its
number of free parameters against FullProf's, and its Rwp, reduced chi-square and iteration count against
regression pins. FullProf shares one B iso between the two Fe sites; the project declares the same tie as a
constraint, and every fitted value is within FullProf's standard uncertainty of FullProf's own.
