---
title: Ferrite and austenite on BEER, joint
description: >-
  Two Fe phases, ferrite and austenite, against two BEER (ESS) time-of-flight neutron banks, fitted jointly with
  each phase's scale tied across the banks.
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

`expected.json` holds CrySPY's result for the first fit, an independent reference
([PROVENANCE.md](PROVENANCE.md)). CI and `pixi run verify` run this project through `python -m edi` and compare
its Rwp with CrySPY's (`tools/checks/cli_projects.py`).
