# Complete-project loading

How `import edi` loads a whole project — structure, banks, measured data, exclusions, cutoff, bank
geometry and the free set — in **one call**, and what a successful load proves. Delivered; the
binding decision it implements is
[crysta],
whose project-directory contract edi mirrors.

## The one loader

`edi.Project.load(dir)` is the **single** loader (*one loader, project contents
select calculate vs fit* — the former `load_complete` is retired and `load` inherited its
postconditions). A successful return proves the project is **complete**, and the project's own
contents select which contract each experiment satisfies:

- an embedded **`_data` loop** means the experiment is **fit-ready**: the loop is non-empty,
  declares all required columns, and every value is finite with a strictly positive sigma;
- declared **`_data_range.<axis>_min/_max/_step`** values mean a **calculation** experiment: a
  grid is generated, carries no observation, and the fit entry points refuse it;
- declaring **neither, or both**, is a load-time `edi.IoError` naming the offending file — as is
  a project with no experiments at all, or a linked structure that names no structure of the project.

A project may hold several structures, one `structures/<name>.edi` file each; an experiment's
`_linked_structure` loop names the ones its pattern sums, each with its own scale.

Any violation throws **never** a partially-populated `Project`. That is the boundary that makes a
silent partial project unrepresentable: after a fit-ready load, refinement cannot fail for a data
reason, and `fit()` / `fit_joint()` can be called with no arguments.

```python
import edi

project = edi.Project.load('path/to/ncaf')   # everything, or IoError
outcome = project.analysis.fit()             # routes by the declared _fitting_mode.type
print(outcome.rwp, outcome.reduced_chi_square)
```

`project.analysis.fit()` is the one entry point: it reads the declared mode and dispatches. Picking
the entry point by hand — the shape this guide previously showed, `fit_joint() if fitting_mode
== 'joint' else fit()` — is a two-value test against a four-value contract, so a project
declaring a scan mode took the `fit()` branch and fitted the template once instead of the scan.

## Fitting modes

`_fitting_mode.type` in `analysis/analysis.edi` declares which refinement runs. The set is closed:
any other value is refused when the project loads and when the property is assigned.

| value | behaviour |
| --- | --- |
| `sequential` | one after another, each seeded from the previous fit's converged parameters |
| `independent` | one after another, each seeded from the same initial parameters |

Both scan modes execute **serially** — the distinction is the starting point, never the
concurrency. Each fits every data file in the declared `_sequential_fit.data_dir` against the one
template experiment and writes one row per file to `analysis/results.csv`; `single` (one
experiment, one fit) and `joint` (several banks, one simultaneous fit) are the two non-scan values.

## Minimization conditions

The `_minimizer` category in `analysis/analysis.edi` is where a project declares **how** it is
minimized. Every fit path runs these conditions — single, joint, and each file's fit in a scan —
and the command line carries none of them: `python -m edi fit` takes the project and `--dry`.

| Tag | Values | Absent |
| --- | --- | --- |
| `_minimizer.descent` | the descent strategy: `ladder`, `fast_descent`, `fast_descent_linear_snap`, `fast_descent_guarded_linear_snap`, `multistart_prune` | `ladder` |
| `_minimizer.chi_square_tolerance` | a positive number: the relative chi-square improvement below which the fit has converged | `1e-6` |
| `_minimizer.max_iterations` | a positive integer: the iteration budget | `50` |

```text
_minimizer.descent fast_descent
_minimizer.chi_square_tolerance 1e-4
_minimizer.max_iterations 1000
```

The descent ids come from the linked crysta engine's registry, so they are the ids `crysta fit
--list-descents` prints. An unknown descent is refused at load with the registered ids in the
error. A tolerance or budget that is not positive is refused too. A saved project writes back
the conditions it declares, and only those.

A scan (`sequential` or `independent`) records the conditions each file was fitted under in
`analysis/results-provenance.csv`. It has one row per `analysis/results.csv` row, in the same
order, with the columns `file_path`, `descent`, `chi_square_tolerance` and `max_iterations`.
`results.csv` keeps diffraction-lib's column set. You can change a condition and resume a scan:
the new rows record the new conditions and the earlier rows keep theirs.

The scan summary counts the failed files. Look up which files failed in `analysis/results.csv`.

## The embedded `_data` loop

The measured pattern lives inside each experiment block as a `loop_` in the `_data` category:

| Tag | Meaning |
| --- | --- |
| `_data.time_of_flight` | the TOF grid point |
| `_data.intensity_meas` | the measured intensity |
| `_data.intensity_meas_su` | its standard uncertainty (σ) |

Rules the reader enforces, and why each one exists:

- **Column mapping is tag-driven, never positional.** The reference vehicle's header order is
  `(time_of_flight, id, intensity_meas, intensity_meas_su)`, so a positional reader would silently
  take `_data.id` as the intensity.
- **The loop is discovered by the `_data.*` category**, not by one required member. Keying discovery
  on a single tag would make that tag a silent sentinel: a loop omitting or misspelling it would be
  read as "no data at all" rather than as the malformed loop it is.
- **All three required columns must be present in that one loop.** A missing or misspelled one is an
  error naming the column. `_data` columns split across two loops are rejected
  for the same reason the line-segment background is: cells are paired within one loop, so a split
  body would decode into a plausible-but-wrong pattern.
- **Extra `_data.*` columns are tolerated** — the reference treats `_data` as an unmodelled category,
  so rejecting them would refuse projects it happily fits. `_data.id` is read past and ignored; it is
  a row ordinal, not a measurement.
- **An empty loop is rejected**, deliberately stricter than the reference: a header with zero rows
  parses there and yields a zero-point fit that *looks* successful — the single most dangerous
  failure this path exists to remove.
- **Non-positive σ is rejected.** It is an infinite (or negative) weight; it would poison the fit
  silently rather than fail.
- **Numeric parsing is locale-independent.** Values are read through a pinned classic-locale stream,
  so a comma-decimal host locale cannot change what a project means. Every value must be a finite
  whole token.

## Running a fit

`python -m edi` is this path end to end — point it at a project directory and it loads, refines, and
reports:

```bash
pixi run core-build                                                    # once
pixi run -e default python -m edi fit <project-dir>
pixi run -e default python -m edi fit <project-dir> --verbosity full
pixi run -e default python -m edi fit <project-dir> --report machine
```

`--verbosity` selects how much is reported (`off` / `compact` / `full`; `full` adds per-bank
R-factors, every iteration and the refined-parameter table with start, value ± e.s.d. and % change).
`--report` selects the channel: `human` (the default) is the readable view, `machine` the versioned
`key=value` record that is byte-comparable with `crysta fit` apart from timings and engine-only
fields.

[`examples/fit_ncaf.py`](https://github.com/enhantica/edi/blob/main/examples/fit_ncaf.py) is a short
demonstration of the same `import edi` API, not a CLI.

Nothing here recomputes a fit metric: every number printed is one the engine produced and handed
back on the `FitResultBase`.
