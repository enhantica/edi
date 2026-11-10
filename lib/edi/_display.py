# SPDX-License-Identifier: BSD-3-Clause
"""``project.display``: notebook views of the report model (edi ADR-0079).

Each call writes one part of the report with the report's own writer and ``report.js``
(``report_view_html`` in the core), so a notebook chart or table is the one the HTML report
shows. Delegation only (ADR-0009).
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass as _dataclass
from pathlib import Path as _Path
from typing import TYPE_CHECKING

from edi._edi import _report_view_html

if TYPE_CHECKING:
    from edi._edi import Project

# edi's data folder, beside the package in a source checkout, as the report facade finds it.
_DATA_DIR = _Path(__file__).resolve().parent.parent.parent / 'data'

# The frame's height for each kind of view, in pixels: a pattern as the report's figure, a
# structure as its view, a table by its rows.
_HEIGHTS = {'pattern': 480, 'structure': 660, 'correlations': 560, 'evolution': 640}
_ROW_HEIGHT = 28
# The frame's onload handler: its height is its content's (the body, as the document is never
# shorter than the frame), now and whenever the content resizes.
_FIT_FRAME = (
    '(f=&gt;{const d=f.contentDocument;if(!d)return;'
    "const r=()=&gt;{f.style.height=Math.ceil(d.body.getBoundingClientRect().height)+'px'};"
    'r();new ResizeObserver(r).observe(d.body)})(this)'
)
_TABLE_EXTRA = 96


@_dataclass(frozen=True, slots=True)
class View:
    """One view of the report: ``html`` is its document; a notebook shows it in a frame."""

    html: str
    height: int

    def _repr_html_(self) -> str:  # noqa: PLW3201 - IPython's rich display hook
        # A frame of its own keeps the report's styles and scripts inside it. It takes its
        # content's height once loaded and follows it, so no view is cut or leaves a gap; the
        # fixed height stands where scripts do not run.
        return (
            f'<iframe style="width: 100%; height: {self.height}px; border: none" '
            f'onload="{_FIT_FRAME}" srcdoc="' + _html.escape(self.html, quote=True) + '"></iframe>'
        )


def _shown(view: View) -> View | None:
    """In IPython the view is shown at once, as diffraction-lib's display calls are.

    Elsewhere it is returned.
    """
    try:
        from IPython import get_ipython  # noqa: PLC0415 - optional, only in a notebook
        from IPython.display import display  # noqa: PLC0415
    except ImportError:
        return view
    if get_ipython() is None:
        return view
    display(view)
    return None


def _index(names: list[str], name: str | None, what: str) -> int:
    """The place of ``name`` among ``names``; without a name, the only one."""
    if name is None:
        if len(names) == 1:
            return 0
        if not names:
            msg = f'the project has no {what}'
            raise ValueError(msg)
        msg = f'the project has several {what}s ({", ".join(names)}); name one'
        raise ValueError(msg)
    if name not in names:
        msg = f"the project has no {what} '{name}' ({', '.join(names) or 'none'})"
        raise ValueError(msg)
    return names.index(name)


def _view(
    project: Project, kind: str, *, index: int = 0, rows: int = 0, **options: object
) -> View | None:
    # The report's own model, every group but the data and the reflections included, so a view
    # shows its part whatever the report leaves out.
    model = project.report.model(excluded=['data', 'reflections'])
    offline = project.report.html_offline
    text = _report_view_html(model, _DATA_DIR, offline, kind, index, **options)
    height = _HEIGHTS.get(kind, _TABLE_EXTRA + _ROW_HEIGHT * rows)
    return _shown(View(text, height))


class FitDisplay:
    """The fit's views: ``results``, ``correlations`` and, for a scan, ``series``."""

    __slots__ = ('_project',)

    def __init__(self, project: Project) -> None:
        self._project = project

    def results(self) -> View | None:
        """The fit result: status, iterations, χ² and R factors (diffraction-lib)."""
        return _view(self._project, 'fit_results', rows=10)

    def correlations(self) -> View | None:
        """The correlation chart (diffraction-lib ``fit.correlations``)."""
        return _view(self._project, 'correlations')

    def series(self) -> View | None:
        """Each fitted parameter across a scan's datasets (diffraction-lib ``fit.series``)."""
        return _view(self._project, 'evolution')


class ParametersDisplay:
    """The parameter tables: ``free``, ``fittable`` and ``all``."""

    __slots__ = ('_project',)

    def __init__(self, project: Project) -> None:
        self._project = project

    def _table(self, which: str, rows: int) -> View | None:
        return _view(self._project, 'parameters', parameters=which, rows=rows)

    def free(self) -> View | None:
        """The free parameters with their values and s.u. (diffraction-lib ``parameters.free``)."""
        return self._table('free', len(self._project.free_parameters))

    def fittable(self) -> View | None:
        """The parameters a fit can free (diffraction-lib ``parameters.fittable``)."""
        return self._table('fittable', len(self._project.parameters))

    def all(self) -> View | None:
        """Every parameter (diffraction-lib ``parameters.all``)."""
        return self._table('all', len(self._project.parameters))


class Display:
    """Charts and tables after each step of an analysis (diffraction-lib ``project.display``).

    Each is a part of the project's report, drawn by the report's own code. In IPython it is
    shown at once; elsewhere the call returns a :class:`View`.
    """

    __slots__ = ('_project',)

    def __init__(self, project: Project) -> None:
        self._project = project

    @property
    def fit(self) -> FitDisplay:
        """The fit's views."""
        return FitDisplay(self._project)

    @property
    def parameters(self) -> ParametersDisplay:
        """The parameter tables."""
        return ParametersDisplay(self._project)

    def pattern(
        self,
        expt_name: str | None = None,
        x_min: float | None = None,
        x_max: float | None = None,
    ) -> View | None:
        """The experiment's chart: measured, calculated, difference and Bragg ticks.

        ``x_min`` and ``x_max`` zoom the x axis. Without ``expt_name``, the only experiment.
        """
        names = [experiment.name for experiment in self._project.experiments]
        index = _index(names, expt_name, 'experiment')
        return _view(self._project, 'pattern', index=index, x_min=x_min, x_max=x_max)

    def structure(self, struct_name: str | None = None) -> View | None:
        """The structure view. Without ``struct_name``, the only structure."""
        names = [structure.name for structure in self._project.structures]
        index = _index(names, struct_name, 'structure')
        return _view(self._project, 'structure', index=index)

    def constraints(self) -> View | None:
        """The aliases and constraints (diffraction-lib ``analysis.display.constraints``)."""
        project = self._project
        return _view(project, 'relations', rows=len(project._aliases) + len(project._constraints))
