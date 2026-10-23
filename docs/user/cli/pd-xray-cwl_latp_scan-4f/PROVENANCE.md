# pd-xray-cwl_latp_scan-4f — provenance

Built by `tools/cli_projects/build_catalogue_projects.py` (`catalogue_latp_fixture.py`) from the example
`pd-xray-cwl_latp-bm01_scan`.

## Sources

- **Data and model:** `pd-xray-cwl_latp-bm01_scan`'s project, its `.edi` files unchanged except the name and the
  description, and four of its patterns, `latp_312.dat`, `latp_304.dat`, `latp_296.dat` and `latp_288.dat`, copied
  byte for byte. That project's `PROVENANCE.md` names where they come from: provided by the project owner;
  licence not recorded.

## Why these four

The template first and then every 8th pattern, so the four span the start of the scan while each fit can start from
the one before. With every 24th pattern (`latp_288`, `latp_264`, `latp_240`), `latp_240` started from `latp_264`
ended without a convergence verdict, which the checks would read as a failed run.

## Pins

From `python -m edi fit` of a copy (`OMP_NUM_THREADS=1`): 59 free parameters (a reference: the count follows from the
model), and per file the reduced χ² (relative tolerance 10⁻⁵) and the LATP cell c (10⁻⁴ Å), regression pins.

| file | reduced χ² | c (Å) | iterations |
| --- | --- | --- | --- |
| `latp_312.dat` | 1.422321·10⁸ | 20.82674 | 5 |
| `latp_304.dat` | 1.437673·10⁸ | 20.83157 | 17 |
| `latp_296.dat` | 1.476181·10⁸ | 20.83880 | 18 |
| `latp_288.dat` | 1.408974·10⁸ | 20.85007 | 18 |

The project rebuilt here replaced an earlier one made from a summed pattern of a different measurement, with
synthetic frames for negative points and an empty frame; those cases are covered by the scan fixtures under
`tests/fixtures/`.
