# pd-xray-cwl_pbso4-lab_pawley: provenance

## Sources

- **Project:** a copy of `pd-xray-cwl_pbso4-lab/project` with three changes. The structure has no atom sites, its
  calculation method is Pawley and its cell starts at the round-robin structure's cell rounded to three decimals
  (8.486, 5.402, 6.965 Å; `pd-xray-cwl_pbso4-lab_round-robin` has 8.485900, 5.402259, 6.964587). The linked
  structure's scale, 0.001, has no free mark. The name and description in `project.edi` differ.
- **Data:** the laboratory X-ray pattern of `pd-xray-cwl_pbso4-lab`, the same `_data` loop; its sources and checksum
  are in that project's `PROVENANCE.md`.

## The start

The experiment starts as `pd-xray-cwl_pbso4-lab` does: zero shift 0; U, V, W 0.02, -0.02, 0.008; mixing 0.5; the two
asymmetry terms 0; a flat Chebyshev background at 140. No extracted intensities are saved and the structure has no
atoms, so a fit starts every reflection from one common value.

The cell starts closer than the Rietveld project's 8.47, 5.39, 6.95 Å, at the precision of a published cell. From
those rounder values FullProf's Le Bail fit of this pattern was still at R<sub>wp</sub> 27 % after 69 cycles (measured
at authoring time): with the cell 0.015 Å off, the high-angle intensities are shared out to the wrong reflections.

## References

FullProf.2k 8.40 (Feb2026) fitted the same start once at authoring time, 28 November 2026, as a Le Bail fit (`Jbt=2`,
profile matching with a fixed scale, no atoms). `fullprof/le-bail.inp` is the `.pcr` of the `pd-xray-cwl_pbso4-lab`
FullProf reference (`knowledge/fitting/fullprof/pd-xray-cwl_pbso4-lab/fit.pcr`) with its title, `Jbt=2`, no atoms,
the cell above, the atom and scale codes removed and the other codes renumbered; nothing else changed. Its data file
is that reference's `fit.dat`. Run as `printf 'lebail\n\n' | fp2k` with the two saved as `lebail.pcr` and
`lebail.dat`; no test runs FullProf. The fit converged at cycle 114.

| quantity | kind | value | source |
| --- | --- | --- | --- |
| `n_points_fitted` | reference | 5799 | `fullprof/le-bail.out`, `N-P+C = 5783` plus the 16 fitted parameters |
| `rwp` | reference | 0.0748 | `fullprof/le-bail.out`, R<sub>wp</sub> 7.48 % over all non-excluded points; compared within 10 % |
| `param.cell_length_a.value` | reference | 8.4815617 ± 0.0000679 Å | `fullprof/le-bail.out` (`Cell_A_ph1_pat1`); compared within five of FullProf's s.u. |
| `param.cell_length_b.value` | reference | 5.3993139 ± 0.0000484 Å | `Cell_B_ph1_pat1`, the same bound |
| `param.cell_length_c.value` | reference | 6.9610386 ± 0.0000595 Å | `Cell_C_ph1_pat1`, the same bound |

The bounds are wider than the catalogue's (two s.u. and 5 % for a fit of the same model) because the methods differ:
Pawley fits every intensity, Le Bail shares the counts out, so they reach nearly but not exactly the same cell and
profile. Pawley minimises χ² over the intensities as well, so its R<sub>wp</sub> should be at or a little below
Le Bail's. Review both bounds when the fit first runs. `n_free` is not a reference: edi counts the Pawley intensities,
whose number depends on how reflections tie.

FullProf's other fitted values, for comparison (`fullprof/le-bail.out`): zero -0.02442(46)°, U 0.03723(82),
V -0.02842(94), W 0.01607(27), mixing 0.7494(55), Asy1 0.1460(24), Asy2 0.03137(72), Chebyshev 112.90, 25.33,
-19.85, -5.70, -7.50, -21.65. FullProf's Rietveld fit (`pd-xray-cwl_pbso4-lab`) gives 8.48066, 5.39888, 6.96026 Å and
R<sub>wp</sub> 8.42 %. The cells differ by about ten s.u., and the constant background term is 147 there against 113
here: with free intensities, part of the background goes into the peaks.

The project is not executing yet (`projects.yml`): it runs once edi fits a Pawley structure. Then the iterations and
reduced χ² are added as regression pins.

## Files (sha256)

- `fullprof/le-bail.inp` `2cc0fd44e749b96f72d566540f59de3210f7f01eeeb1323d36358d56ab5a2198`
- `fullprof/le-bail.out` `673098828e6f9eb59846ac697d552e2762f13d5ec7146c721e5a5a6f13e82b0e`
- data, `knowledge/fitting/fullprof/pd-xray-cwl_pbso4-lab/fit.dat`
  `09980b23501f5fb23e30fbcf38b9c029f16c3125d35cbd4d2ad0358cf719b39f`
- `fp2k` `b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`
