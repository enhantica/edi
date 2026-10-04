# `pd-neut-tof_fe_pseudo-voigt` -- FullProf verification project

Origin: diffraction-lib (<https://github.com/easyscience/diffraction-lib>, BSD-3-Clause; licence copy at `tests/fixtures/diffraction-lib-LICENSE`), upstream folder `pd-neut-tof_fe_pseudo-voigt`, pin `0d9f10e4`. Mirrors the upstream page **`pd-neut-tof_Fe_pseudo-voigt`**. The `.pcr` title names BEER (ESS) for the data; the id follows the packet's CLI project id, which carries no instrument.

Every parameter is fixed (a forward calculation), with the non-convoluted pseudo-Voigt TOF profile (`Npr` = 7, `Uni` = 1; physics book §4.4). Its occupancies already follow the convention (k = 1), so it is **not re-fit**: its inputs and outputs are its source bytes, and every output replays under FullProf 8.40 apart from the run-date lines (checked at vendoring). The profile file keeps FullProf's pattern-numbered stem `fe_1`.

## Occupancy convention

Every `Occ` is **site occupancy x site multiplicity / general multiplicity**, multiplicities from the cctbx Wyckoff tables (`tests/fixtures/c34_t25_fullprof/wyckoff.json`, cctbx-base 2026.8).

| phase | group | site | m / M (cctbx) | site occupancy | `.pcr` Occ |
| --- | --- | --- | --- | --- | --- |
| 1 | `I m -3 m` | `Fe` | 2 / 96 | 1 | 0.02083 |

## Scale

| phase | old scale | new scale | Occ factor k | scale_new x k^2 / scale_old - 1 |
| --- | --- | --- | --- | --- |
| 1 | 401.463 | 401.463 | 1 | +0.00e+00 |

## Reproduce

FullProf.2k 8.40 (Feb2026-ILL): `printf 'fe\n\n' | fp2k` in a copy of this folder (the hub skill `fullprof-fp2k`). Result line: `=> Rp: 52.1 Rwp: 76.5 Rexp: 2.03 Chi2: 0.143E+04`.

## Files (sha256)

- `fe.dat` `cfa0e32227587856d96e1d0936783be310cdf756a6f09aacd9da72a82612ebc4`
- `fe.pcr` `f6190f4c930ac5bae6411152b3196617e7a85654b6294bbab51b0a3ef5688779`
- `fe.sum` `5286353543b3d81b82d682d3cc95da8a12b850620b0d65f12237148b41b3c489`
- `fe_1.bac` `16a34bda1efbf25220b4625eed1a779163c14084689141182a7eba6c8d4609ec`
- `fe_1.prf` `fd3761ea0c11dcb8e82571341bfa3b4045bf218e74df7e0a073d200c83a8012f`

## Evidence

```json
{
  "schema": "fullprof-evidence-1",
  "site_occupancies": {
    "1:Fe": 1.0
  },
  "start_site_occupancies": {
    "1:Fe": 1.0
  },
  "old_scales": [
    401.4629
  ],
  "new_scales": [
    401.4629
  ]
}
```
