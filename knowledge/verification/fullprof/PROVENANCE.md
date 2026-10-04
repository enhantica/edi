# FullProf reference projects — layout and provenance

edi keeps every FullProf reference project in **one of two homes**, one project per folder:

| home | what a project is | output |
| --- | --- | --- |
| `knowledge/verification/fullprof/<id>/` (here) | a **forward calculation**: every parameter fixed (0 free); where changed its occupancies, and for every twin, the scale fitted alone once and then fixed | `Prf = 2` profile (`.prf`), background (`.bac`), summary (`.sum`) — what the verification pages read |
| [`knowledge/fitting/fullprof/<id>/`](../../fitting/fullprof/PROVENANCE.md) | a **fit**: some parameters free, `Pcr = 2` (FullProf writes `.new`, never over the `.pcr`) | the converged `.pcr`, its `.prf`/`.sum`, and the run that reached it (`full-fit.out` / `.inp`) |

Each fitting project has a **verification twin** here under the same id: its fitted state with every
parameter fixed.

**Names.** A folder is named `<technique>_<sample>[-<instrument>]_<variant>` — the CLI project id rule.
The instrument appears whenever a source names it and is omitted otherwise, never guessed. A folder
derived from a diffraction-lib page records, in its `PROVENANCE.md`, the upstream folder and page it
mirrors.

**Occupancies.** Every `.pcr` states `Occ` as **site occupancy × site multiplicity ÷ general multiplicity** (site
occupancy 1 for a fully occupied site), multiplicities from the cctbx Wyckoff tables. Where restated a file into
this convention, the factor moved into the scale (and, for a TOF phase, into `Extinc`, since FullProf's extinction
term scales with |F|²), and the project was fitted again: see each folder's `PROVENANCE.md` for the old and new
scale. A project whose occupancies already followed the convention (k = 1) was not re-fit: its inputs are its
source bytes, and so is every output that replays under FullProf 8.40 -- the two that did not
(`pd-neut-cwl_y2o3_isotropic-adp`'s
`.sum`, `pd-neut-tof_ncaf-wish_jorgensen-von-dreele`'s `.prf`) are regenerated from those inputs (conductor
decision 2026-09-25 and its amendment, the design records).

**Matched pairs.** Within a folder the `.prf`/`.sum`/`.bac` are the output of FullProf.2k **8.40
(Feb2026-ILL)** run over the committed `.pcr` and data, `printf '<stem>\n\n' | fp2k` (the hub skill
`fullprof-fp2k`); a rerun reproduces them apart from the run-date and CPU-time lines. The data file
carries the `.pcr` stem because `fp2k` reads `<stem>.dat` by default.

**Per-project provenance** — origin, instrument source, occupancy table, scale, file digests and the
fenced JSON evidence block — lives in each folder's own `PROVENANCE.md`. The earlier single-file
record is in git history.

**The CW corpus manifest** (`cw-corpus-manifest.json`) binds two things: (i) the **identity of the
full upstream CW corpus** at diffraction-lib pin `39ada82c` — its 7 `pd-neut-cwl_*` and 2
`pd-xray-cwl_*` project directories and 16 page names (11 neutron, 5 X-ray; the X-ray entries joined
with first X-ray page), spelled as upstream spells them; and (ii) the **sha256 of every file in the CW
folders the pages read**, keyed by edi folder. Those folders' occupancies already followed the
convention, so their FullProf files are the upstream bytes (`y2o3.dat` renamed to its `.pcr` stem)
except Y2O3's regenerated `.sum`; each folder's `PROVENANCE.md` is the only file added. The LBCO
preferred-orientation folder is copied at `0d9f10e4`, whose `.prf`/`.sum` are a later FullProf 8.40 run
of the same inputs than the corpus pin carries (its own `PROVENANCE.md`).

License: the diffraction-lib-derived folders originate in the diffraction-lib repository
(BSD-3-Clause); see `tests/fixtures/diffraction-lib-LICENSE`.
