---
title: "Rietveld fit: high-entropy perovskite, P02.1"
description: >-
  Fit the high-entropy perovskite La(Ti,Cr,Mn,Fe,Co,Ni,Cu)O₃, seven cations on one site, to synchrotron X-ray powder data from P02.1 at PETRA III.
---

# Rietveld fit: high-entropy perovskite, P02.1

Fit the high-entropy perovskite La(Ti,Cr,Mn,Fe,Co,Ni,Cu)O₃, seven cations on one site, to synchrotron X-ray powder data from P02.1 at PETRA III.

The app lists it as **La(Ti,Cr,Mn,Fe,Co,Ni,Cu)O₃ [Pnma] · P02.1 @ PETRA III**.

## Three ways to run it

- **Command line:** `python -m edi fit docs/user/cli/pd-xray-cwl_lam7o3-p021/project --dry` (fits
  without writing back; drop `--dry` to save the result into the project).
- **App:** open it from the Examples on the Home page.
- **Python:** the tutorial [pd-xray-cwl_lam7o3-p021](../../tutorials/pd-xray-cwl_lam7o3-p021.ipynb) loads this project and works through it.

All three read the same files, in `docs/user/cli/pd-xray-cwl_lam7o3-p021/project`.

## The start

The project starts the way your own measurement would: zero shift 0, profile terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and the scale to one significant figure. The background is 20 points placed by hand, all starting at 300, and the project selects the fast descent (`_minimizer.descent fast_descent`).

## Sources

Where the data and the model come from, with each data file's checksum and licence:
[`PROVENANCE.md`](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-xray-cwl_lam7o3-p021/PROVENANCE.md).
