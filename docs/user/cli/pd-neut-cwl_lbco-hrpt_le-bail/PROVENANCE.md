# pd-neut-cwl_lbco-hrpt_le-bail: provenance

## Sources

- **Project:** a copy of `pd-neut-cwl_lbco-hrpt/project`, its data, model and start unchanged. Two lines differ:
  `_structure.calc_method le_bail` in `structures/lbco.edi`, and the name and description in `project.edi`.
- **Data:** the HRPT (PSI) pattern of `pd-neut-cwl_lbco-hrpt`, the same `_data` loop; its sources and checksum are in
  that project's `PROVENANCE.md`.

## The start

The start of `pd-neut-cwl_lbco-hrpt`: cell 3.88 Å, 2θ zero 0.3°, U, V, W, Y 0.08, -0.1, 0.1, 0.08, a flat background
at 160. The atoms keep their Biso 0.5 and free marks, and the scale its value 9 and free mark; under Le Bail the fit
leaves them out. No extracted intensities are saved, so a fit starts each reflection from the |F|² the atoms give.

## References

FullProf.2k 8.40 (Feb2026) fitted the same start once at authoring time, 28 November 2026, as a Le Bail fit
(`Jbt=2`, profile matching with a fixed scale). `fullprof/le-bail.inp` is the `.pcr` of the `pd-neut-cwl_lbco-hrpt`
FullProf reference (`knowledge/fitting/fullprof/pd-neut-cwl_lbco-hrpt/fit.pcr`) with its title, `Jbt=2`, the atom and
scale codes removed and the other codes renumbered; nothing else changed. Its data file is that reference's `fit.dat`.
Run as `printf 'lebail\n\n' | fp2k` with the two saved as `lebail.pcr` and `lebail.dat`; no test runs FullProf. The
fit converged at cycle 120.

| quantity | kind | value | source |
| --- | --- | --- | --- |
| `n_free` | reference | 11 | `fullprof/le-bail.out`, the final parameter list |
| `rwp` | reference | 0.0750 | `fullprof/le-bail.out`, R<sub>wp</sub> 7.50 % over all non-excluded points; compared within 5 % |
| `param.cell_length_a.value` | reference | 3.8907781 ± 0.0000192 Å | `fullprof/le-bail.out` (`Cell_A_ph1_pat1`); compared within two of FullProf's s.u. |

FullProf's other fitted values, for comparison (`fullprof/le-bail.out`): zero 0.62047(105)°, U 0.07698(308),
V -0.11505(667), W 0.11203(321), Y 0.10289(177), background 171.1, 162.1, 164.7, 172.1, 173.1. Its Rietveld fit of
the same start (`pd-neut-cwl_lbco-hrpt`) gives the cell 3.8907845 Å and R<sub>wp</sub> 7.21 %.

The project is not executing yet (`projects.yml`): it runs once edi fits a Le Bail structure. Then the two-s.u. cell
bound becomes two of edi's s.u., as `tools/cli_projects/catalogue_expected.py` sets it, and the iterations and reduced
χ² are added as regression pins.

## Files (sha256)

- `fullprof/le-bail.inp` `188f9c5eacf44c6e23813b39b5ee9eb455cc142c32b80e3fd35c81807aa10074`
- `fullprof/le-bail.out` `74789de51b0d6190b4a12bed5a95b4f6bedcbef203196428847538c3d2036ea7`
- data, `knowledge/fitting/fullprof/pd-neut-cwl_lbco-hrpt/fit.dat`
  `431fef11bd67feec091ec51e43b3c7011b8145f46cf9c135195dfaf1976aba13`
- `fp2k` `b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f`
