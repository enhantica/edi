# 0048. One example catalogue

- **Status:** Accepted
- **Date:** 2026-10-22
- **Implementation:** ✅ Implemented — the catalogue, its three forms, its check, the FullProf references and the
  comparison page
- **Priority:** High

Amends [Example metadata and filters](0031-example-metadata-and-filters.md): the app bundles the registry's
user-facing projects, in registry order, and its own LiF example is retired.

## Context

edi showed its examples in three places that did not agree. The app bundled 27 entries, several of them the same
measurement from different starts. The CLI projects under `docs/user/cli/` were regression cases copied from the
engine's fitting corpus, most started next to their answer. The five tutorials built their own models in code and
matched neither. A user could not tell which example showed a technique, and a fix to one copy left the others behind.

## Decision

1. **One registry.** `docs/user/cli/projects.yml` lists every project. A row with `user-facing: true` is a catalogue
   case; every other row is a test fixture. A case's title is its project's `_metadata.title`, its data sources and
   licences are its `PROVENANCE.md` `## Sources`, and its tutorial follows from its id. Nothing restates them.
2. **One spelling.** A case's folder, CLI id, `_metadata.name`, app entry and tutorial file stem are the same string:
   `<technique>_<sample>[-<instrument>][_<variant>]`, two or three parts, a variant only when it tells the user
   something (`simulation`, `scan`).
3. **Three forms of one project.** The CLI fits `docs/user/cli/<id>/project`, the app bundles that folder, and the
   tutorial `docs/user/tutorials/<id>.py` (with its notebook) loads it with `edi.Project.load('../cli/<id>/project')`
   and teaches from there. There is one project, so the forms cannot drift apart. A tutorial does not rebuild the
   model in code: the Python API cannot yet create every category the cases use.
4. **The order.** The app's list, the catalogue page and the tutorials index show the cases in registry order, in six
   groups from simplest to most involved: calculations without data, constant-wavelength neutron, time-of-flight
   neutron, X-ray, the joint neutron and X-ray fit, and the scans.
5. **Starts a user would have.** A fitted case starts the way a user's own measurement would: zero shift 0, profile
   terms to one significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background at the
   10th percentile of the counts and the scale to one significant figure. A case that needs another start, because
   the fit cannot reach its minimum from this one, says so in its `PROVENANCE.md` and on its page, with the measured
   reason.
6. **Fixtures stay.** Every project that was in the registry before the catalogue keeps its id, its project files and
   its `expected.json`, and keeps running in the checks. Its page is a `README.md` outside the user navigation. The
   one exception is the four-pattern LATP scan, rebuilt from the catalogue's LATP measurement.
7. **Authors.** Every catalogue project writes `_metadata.authors .`, the CIF empty value. The report shows no authors
   line for `.` or `?`.
8. **Datasets.** Every data file a case commits is named in its `PROVENANCE.md` with where it came from, its sha256
   and its licence. A case that reuses another project's pattern names that project and the original source.
9. **The check.** `tools/checks/example_catalogue.py` runs first in the `cli-projects` task (local and CI). It is red
   when the registry reads differently as YAML and as the app's CMake reads it, when a case lacks its project, page,
   provenance, tutorial, notebook or execution-exclusion entry, when a tutorial loads anything but its own project or
   loads more than one, when a notebook's load differs from its source's, when a data file is not in the provenance,
   and when a tutorial, page or exclusion names a project that is not a case. A tutorial and each of its notebook's
   code cells load in one form only: a top-level statement of its own, `project = edi.Project.load('<path>')`, with
   a literal path. Any other mention of `Project.load`, in an expression, a branch, a function, a lambda, a target
   or an alias, fails the check, so whether a load runs never has to be inferred.
10. **References.** Each fitted case has a FullProf fit from the same start, committed with its inputs and outputs, and
    the catalogue's comparison page sets edi beside FullProf and diffraction-lib with the agreement factors recomputed
    from the committed curves. Rows whose models differ are marked as such, never presented as agreement. A case's
    `expected.json` holds FullProf's number of free parameters, its R<sub>wp</sub> within 5 % and its shared values
    within two of edi's standard uncertainties. A scan is compared on its template file's single fit, as its FullProf
    fit is (`"template": true`). The two programs' Bérar-Baldinozzi asymmetry differs in form and no mapping of the
    coefficients removes the difference, so a case using it is compared on R<sub>wp</sub> and the number of free
    parameters only, and every shared value on a second FullProf fit with the four coefficients fixed at 0 against
    edi's fit of the same (the record's `asymmetry-off` variant). FullProf runs once, when a reference is written,
    never in a check.

## Consequences

- A new example is one registry row, one project, one tutorial and one page, and the check refuses a partial one.
- The app, the docs and the tutorials show the same 20 cases, so a fix to a case reaches all three.
- Fits from realistic starts take more iterations than the old corpus starts, and a few cases needed a stated
  departure; their pages say which and why.
- The tutorials run only once a tutorial runner can provide their project outside the repository; until then they
  are listed in `docs/user/tutorials/execution-exclusions.yml`.
- The app's demo and its test observers open catalogue cases; the demo's captured images change with them.

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| Tutorials that build the model in code, as diffraction-lib's do | Rejected for now: the Python API cannot create background points or excluded regions yet, and the sameness of two models could only be shown by running both. |
| A second file listing the catalogue | Rejected: two lists drift; one row flag keeps one list. |
| Removing the old projects | Rejected: they are regression cases with their own pinned results and keep catching changes. |
