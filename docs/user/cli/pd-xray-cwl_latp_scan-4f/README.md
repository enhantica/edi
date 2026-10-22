---
title: LATP with two AlPO4 phases, four synchrotron X-ray patterns
description: >-
  A test project: the LATP scan example's model and values fitted in sequence on four of its 73 patterns, so the
  checks run a three-phase sequential fit with a declared template file in seconds.
---

# LATP with two AlPO4 phases, four synchrotron X-ray patterns

A test project, not one of the examples. It is the example
[`pd-xray-cwl_latp-bm01_scan`](../pd-xray-cwl_latp-bm01_scan/index.md) on four of its 73 patterns: the same
structures, experiment, constraints, free set and values, and `latp_312.dat` as the template file
(`_sequential_fit.template_file`). The patterns are `latp_312.dat`, `latp_304.dat`, `latp_296.dat` and
`latp_288.dat`, copied byte for byte, and the scan fits them in that order, each from the previous one's result.

## Run it

```bash
python -m edi fit docs/user/cli/pd-xray-cwl_latp_scan-4f/project --dry
```

`--dry` leaves the project unchanged; drop it to write the fitted values back.

## What is checked

`expected.json` holds the number of free parameters, a reference, and for each of the four files its reduced χ² and
LATP c from `analysis/results.csv`, regression pins that catch a change in the sequential fit. The project is built
by `tools/cli_projects/build_catalogue_projects.py pd-xray-cwl_latp_scan-4f` from the example's project.
