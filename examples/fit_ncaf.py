#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Refine a complete NCAF powder project through the public ``import edi`` surface.

    pixi run core-build                                       # build `edi._edi` once
    pixi run -e default python examples/fit_ncaf.py           # the corpus NCAF case
    pixi run -e default python examples/fit_ncaf.py <project> # any project directory

This is an **example**, not the CLI. To run a fit from the command line, use the supported entry
point, which has the flags and the stability contract this file deliberately does not:

    pixi run -e default python -m edi fit <project-dir> --verbosity full
    pixi run -e default python -m edi fit <project-dir> --report machine

What it shows: the whole-fit path as an ordinary user reaches it. Point at a project directory, let
edi load **everything** from it — structure, every experiment bank, each bank's embedded measured
data, exclusions, cutoff, bank geometry and the free set — and refine in one call. The fit
itself is delegated to crysta's Levenberg-Marquardt minimizer inside the core; nothing here
reimplements refinement, and nothing here recomputes a fit metric. Every number below is one the
engine produced and handed back on the ``FitResultBase``.

Note what is *absent*: no separate pattern file, no ``numpy``, no hand-rolled array parsing —
and no formatting code. Rendering belongs to ``edi::core`` (the streaming formatters /
``edi.machine_report``), so this example, ``python -m edi``, and the later desktop surfaces all
share one implementation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import edi

# The NCAF project lives in the crysta fitting corpus, which is the ONE home for fitting data —
# edi is a consumer and ships none of its own. Resolution order matches
# tests/conftest.py::corpus_case_dir: the cross-build override first, then the pinned checkout.
# Pass a project directory as argv[1] to point this at anything else.
CASE_ID = 'ncaf-wish-2bank-s3'


def corpus_case(case_id: str) -> Path | None:
    """Resolve a corpus case directory, or None when no corpus is reachable."""
    override = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
    root = (
        Path(override)
        if override
        else Path(__file__).resolve().parents[1] / 'build' / 'crysta-src' / 'tests' / 'fitting'
    )
    case = root / case_id / 'project'
    return case if case.is_dir() else None


def main() -> int:
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1])
    else:
        resolved = corpus_case(CASE_ID)
        if resolved is None:
            print(
                f"no project given and corpus case '{CASE_ID}' is not reachable.\n"
                f'Either pass a project directory:\n'
                f'    python examples/fit_ncaf.py <project-dir>\n'
                f'or make the corpus available (`pixi run core-build` populates the pinned\n'
                f'checkout, or set EDI_CRYSTA_CORPUS_ROOT to a crysta tests/fitting tree).',
                file=sys.stderr,
            )
            return 1
        project_dir = resolved
    if not project_dir.is_dir():
        print(f'not a project directory: {project_dir}', file=sys.stderr)
        return 1
    # One call. `load` either returns a complete project or raises `edi.IoError` naming what is
    # wrong — it never returns a partially loaded one (the one loader: the project's own contents
    # select calculate vs fit, and this fit-ready project declares its data).
    project = edi.Project.load(str(project_dir))

    # A progress subscriber is optional. Passing one costs a call per accepted step; passing none
    # costs nothing at all, and the same records are still on the outcome afterwards.
    def show(record: edi.IterationRecord) -> None:
        print(f'  iteration {record.iteration:2d}  Rwp {record.rwp:.4f}')

    outcome = project.fit(on_iteration=show)

    # The library itself printed nothing above; presentation is the caller's decision. Here we ask
    # the core for the human view.
    print()
    print(edi.summary_line(outcome))
    print(edi.parameter_table(outcome), end='')

    # A few results read straight off the outcome, keyed by edi identity path.
    print(f'\n  scale = {outcome.values["experiment.linked_structure.scale"]:.6g}')
    print(
        f'  {outcome.iterations} iteration(s), Rwp {outcome.rwp:.4f}, status {outcome.status.name}'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
