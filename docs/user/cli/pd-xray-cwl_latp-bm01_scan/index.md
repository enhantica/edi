---
title: "Sequential fit: LATP, BM01"
description: >-
  Fit three phases, LATP and two AlPO₄ forms, to 73 synchrotron X-ray patterns from BM01 at SNBL, one after another, with linked displacement parameters.
---

# Sequential fit: LATP, BM01

Fit three phases, LATP and two AlPO₄ forms, to 73 synchrotron X-ray patterns from BM01 at SNBL, one after another, with linked displacement parameters.

The app lists it as **LATP [R-3c] / AlPO₄ [C222₁] / AlPO₄ [P6₃mc] · BM01 @ SNBL**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-xray-cwl_latp-bm01_scan/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-xray-cwl_latp-bm01_scan](../../tutorials/pd-xray-cwl_latp-bm01_scan.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-xray-cwl_latp-bm01_scan/project`.

## The start

The template pattern, latp_312, starts from an earlier fit of that pattern; each later pattern starts from the fit before it.

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-xray-cwl_latp-bm01_scan/PROVENANCE.md).
