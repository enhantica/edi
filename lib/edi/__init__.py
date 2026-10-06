# SPDX-License-Identifier: BSD-3-Clause
"""edi — the user-facing diffraction-analysis API (dist: easydiffraction).

Thin Python surface over the C++ product core (ADR-0009): the compiled ``_edi`` nanobind module
plus a small pure-Python sugar layer (factories, presentation only). Product logic lives in the
C++ core, consumed 1:1 by the bindings.

edi-py carries crysta-py's public surface: every name crysta declares public, and every member of
a declared class, EXISTS here under the same spelling with the same meaning; edi adds output and
visualisation under edi-only names. That direction is a standing constraint on edi, and what is
PROVEN of it is existence only — ``tools/checks/python_surface_superset.py`` reads the declaration
crysta's C++ package installs and resolves each name by attribute lookup (no signature, default or
type is compared): today at crysta's pull-request gate (the consumer prefix), and by edi's own
verify against the fetched crysta main, which carries the declaration. Whether a script works
under ``s/crysta/edi/`` is demonstrated, not described: crysta's ``tools/substitution/`` scripts
run against both libraries at that consumer job and must agree, for the paths they cover. edi
never imports crysta-py.
"""

import os as _os
import subprocess as _subprocess  # aliased: a bare name stays off the surface (I1)
from collections.abc import (
    Callable as _Callable,  # aliased: a bare name stays off the surface (I1)
)
from importlib import util as _importlib_util
from pathlib import Path as _Path
from typing import ClassVar as _ClassVar  # aliased: a bare name would join the public surface (I1)


def _visible_cpu_count() -> int:
    """Cores this process may run on — the affinity mask on Linux, else the machine count.

    Mirrors crysta::threading::visible_concurrency; this preamble computes the team size in
    Python because it runs before the compiled extension (and libgomp) load.
    """
    try:
        return len(_os.sched_getaffinity(0))
    except AttributeError:
        return _os.cpu_count() or 1


# The engine's shipped threading policy must be in the environment BEFORE the compiled extension
# — and with it the OpenMP runtime — loads: libgomp reads OMP_WAIT_POLICY/OMP_NUM_THREADS in its
# ELF constructor at load time (measured), so this preamble, ahead of every native import below
# (numpy included, so the OpenBLAS timeout default is planted before its pool spins up), is the
# only in-process seam. Presence, not value: a wait variable PRESENT with ANY value — empty
# included, hence `in _os.environ`, not a truthiness test — stands the WHOLE policy down (wait
# AND team), keeping the old behaviour (spin at a full-occupancy team) measurable. A caller
# OMP_NUM_THREADS still wins over the max(1, cores - 2) rule.
if not (
    'OMP_WAIT_POLICY' in _os.environ
    or 'GOMP_SPINCOUNT' in _os.environ
    or 'KMP_BLOCKTIME' in _os.environ
):
    _os.environ['OMP_WAIT_POLICY'] = 'passive'
    if 'OMP_NUM_THREADS' not in _os.environ:
        _os.environ['OMP_NUM_THREADS'] = str(max(1, _visible_cpu_count() - 2))
    # The same passive-wait default for the OTHER pool in an edi process: neither crysta nor
    # edi links a BLAS, but numpy's OpenBLAS rides along, and its idle workers busy-wait ~2^26
    # cycles after every wake — measured burning a process-CPU/wall ratio of ~3 through the
    # serial gaps the wait policy exists to quiet. The timeout exponent (clamped to 4..30 by
    # OpenBLAS) only shortens the idle spin before the worker sleeps; numpy's parallelism and
    # results are untouched, and a caller-set value — or any wait knob above — wins.
    _os.environ.setdefault('OPENBLAS_THREAD_TIMEOUT', '4')

# Imported after the preamble so the OpenBLAS timeout default is in place before its pool spins.
import numpy as _np  # noqa: E402, ICN001 - see the preamble above; a bare `np` would be public (I1)

# The compiled extension is emitted PER BUILD CONFIGURATION into <build-dir>/python/edi, never
# into this source package — six build configurations sharing one source-tree artifact silently
# relinked stale objects over one another, so runtime evidence could not name the configuration
# it came from. A packaged install carries `_edi` inside the package and none of this runs; a
# source tree (identified by the repo's pyproject.toml two levels up) resolves the configuration
# explicitly: EDI_EXTENSION_DIR when set, else the same selection tools/ci/core-build.sh makes as
# the producer (CRYSTA_CONSUMER_SRC -> build/ci-consumer, else build/ci — keep the two selections
# in lockstep). Every edge fails closed, naming the contract.
_here = _Path(__file__).resolve().parent
if (_here.parent.parent / 'pyproject.toml').exists():
    _stray = sorted(str(stray) for stray in _here.glob('_edi.*'))
    if _stray:
        raise ImportError(
            f'stale source-tree extension artifact(s) {_stray}: the extension is emitted per '
            'build configuration into <build-dir>/python/edi and a shared source-tree '
            'artifact is refused by design; delete the stray file(s) and rebuild '
            '(pixi run core-build).'
        )
    # CRYSTA_CONSUMER_SRC used to be a PATH at build time and a bare truthy FLAG at import — and
    # only the build validated it, so a typo'd, wrongly-relative or stale-exported value
    # silently redirected the import to a possibly stale build/ci-consumer. Now the consumer
    # artifact is selected only by (a) the explicit selector
    # EDI_USE_CONSUMER_BUILD (any non-empty value), (b) the repo's hidden control — the exact
    # 'hidden-surface-control' literal, exempt BY NAME so no accidental value reaches it — or
    # (c) a CRYSTA_CONSUMER_SRC carrying the source-tree witness CMakeLists.txt — exactly the
    # check tools/ci/build-crysta.sh applies at build time. A value that fails the validation
    # selects nothing. ONE definition, shared verbatim by all four selection sites: here,
    # verification._consumer_source_selects, python_surface_superset.resolve_prefix and
    # crysta-consumer.sh. When the consumer artifact is selected and the source path names a
    # real tree, the tree's current commit is compared against the sha the artifact was linked
    # with (.crysta-linked-sha), refusing a stale artifact by naming both — results are never
    # silently attributed to a crysta that was never built.
    _consumer_src = _os.environ.get('CRYSTA_CONSUMER_SRC')
    _consumer_src_is_tree = (
        bool(_consumer_src) and (_Path(_consumer_src) / 'CMakeLists.txt').is_file()
    )
    _consumer_selected = (
        bool(_os.environ.get('EDI_USE_CONSUMER_BUILD'))
        or _consumer_src == 'hidden-surface-control'
        or _consumer_src_is_tree
    )
    if not _os.environ.get('EDI_EXTENSION_DIR') and _consumer_selected and _consumer_src_is_tree:
        _artifact = _here.parent.parent / 'build' / 'ci-consumer'
        try:
            _linked_sha = (_artifact / '.crysta-linked-sha').read_text('utf-8').strip()
        except OSError as _error:
            raise ImportError(
                f'EDI_USE_CONSUMER_BUILD selects the consumer artifact at {_artifact}, but it '
                f'carries no linked-source record ({_error}) — rebuild it '
                '(CRYSTA_CONSUMER_SRC=... pixi run core-build)'
            ) from None
        try:
            _live = _subprocess.run(
                ['git', '-C', _consumer_src, 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=False,
            )
            _live_head = _live.stdout.strip() if _live.returncode == 0 else ''
        except OSError:
            _live_head = ''
        if _live_head and _live_head != _linked_sha:
            raise ImportError(
                f'the consumer artifact at {_artifact} was linked with stale crysta source '
                f'{_linked_sha} but the live source {_consumer_src!r} is now at {_live_head} — '
                'refusing to attribute results to a crysta that was never built; rebuild the '
                'artifact (CRYSTA_CONSUMER_SRC=... pixi run core-build)'
            )
    _ext_dir = _os.environ.get('EDI_EXTENSION_DIR') or str(
        _here.parent.parent
        / 'build'
        / ('ci-consumer' if _consumer_selected else 'ci')
        / 'python'
        / 'edi'
    )
    __path__.append(str(_Path(_ext_dir).resolve()))
if _importlib_util.find_spec('edi._edi') is None:
    raise ImportError(
        "edi's compiled extension `edi._edi` is not importable: build it per configuration "
        '(pixi run core-build) and, for a non-default location, set EDI_EXTENSION_DIR to the '
        '<build-dir>/python/edi directory that configuration emitted.'
    )

from edi._edi import (  # noqa: E402 - the __path__ resolution above must run first
    AbsorptionBase,
    AbsorptionFactory,
    Alias,
    Aliases,
    AtomSite,
    AtomSiteAniso,
    AtomSiteAnisoCollection,
    AtomSites,
    AtomSitesCartnTransform,
    BankMetric,
    BeamModeEnum,
    BraggPdExperiment,
    Cell,
    Constraint,
    Constraints,
    CwlInstrumentBase,
    CwlPdInstrumentBase,
    CwlPdNeutronInstrument,
    CwlPdXrayInstrument,
    CwlPseudoVoigt,
    CwlPseudoVoigtBerarBaldinozziAsymmetry,
    CwlThompsonCoxHastings,
    CylinderHewatAbsorption,
    Diagnostic,
    DomainValidationError,
    ExpandedAtomSites,
    ExperimentBase,
    Experiments,
    ExperimentType,
    FitPreamble,
    FitResultBase,
    FitStatus,
    Geom,
    GeomBond,
    InstrumentBase,
    InstrumentFactory,
    IoError,
    IterationRecord,
    LeastSquaresFitResult,
    LineSegment,
    LinkedStructure,
    LinkedStructures,
    NoAbsorption,
    Parameter,
    PdCwlData,
    PdDataBase,
    PdExperimentBase,
    PdTofData,
    PeakBase,
    PeakFactory,
    PeakProfileTypeEnum,
    PolynomialTerm,
    PowderCwlReflnData,
    PowderReflnDataBase,
    PowderTofReflnData,
    PrefOrient,
    PrefOrients,
    Project,
    ProjectMetadata,
    RadiationProbeEnum,
    SampleFormEnum,
    ScanFileRecord,
    ScanPreamble,
    ScatteringTypeEnum,
    ScExperimentBase,
    SchemaValidationError,
    Severity,
    SpaceGroup,
    SpaceGroupSymop,
    Structure,
    StructureGeometry,
    Structures,
    SyntaxValidationError,
    TofJorgensen,
    TofJorgensenVonDreele,
    TofPdInstrument,
    TofPseudoVoigt,
    ValidationError,
    VerbosityEnum,
    error_report,
    iteration_line,
    machine_report,
    parameter_table,
    progress_report,
    scan_progress_line,
    scan_summary,
    stream_header,
    summary_line,
)
from edi._edi import (  # noqa: E402 - the __path__ resolution above must run first
    __build_commit__ as __build_commit__,
)
from edi._edi import (  # noqa: E402 - after the __path__ resolution
    _calc_report as _calc_report,
)
from edi._edi import (  # noqa: E402 - after the __path__ resolution
    _default_descent as _default_descent,
)
from edi._edi import (  # noqa: E402 - after the __path__ resolution
    _descent_ids as _descent_ids,
)
from edi._edi import (  # noqa: E402 - after the __path__ resolution
    _entity_path as _entity_path,  # Crysta's one name -> path decision
)
from edi._edi import (  # noqa: E402 - after the __path__ resolution
    _experiment_from_edi_text as _experiment_from_edi_text,
)
from edi._edi import (  # noqa: E402 -: the crysta-vs-edi parity hooks
    _folds_reflections as _folds_reflections,
)
from edi._edi import (  # noqa: E402 -
    _model_dump as _model_dump,
)
from edi._edi import (  # noqa: E402 -
    _structure_factor_evaluations as _structure_factor_evaluations,
)
from edi._edi import (  # noqa: E402 - after the __path__ resolution
    _structure_from_edi_text as _structure_from_edi_text,
)

__all__ = [
    'AbsorptionBase',
    'AbsorptionFactory',
    'Alias',
    'Aliases',
    'Analysis',
    'AtomSite',
    'AtomSiteAniso',
    'AtomSiteAnisoCollection',
    'AtomSites',
    'AtomSitesCartnTransform',
    'BankMetric',
    'BeamModeEnum',
    'BraggPdExperiment',
    'Cell',
    'Constraint',
    'Constraints',
    'CwlInstrumentBase',
    'CwlPdInstrumentBase',
    'CwlPdNeutronInstrument',
    'CwlPdXrayInstrument',
    'CwlPseudoVoigt',
    'CwlPseudoVoigtBerarBaldinozziAsymmetry',
    'CwlThompsonCoxHastings',
    'CylinderHewatAbsorption',
    'Diagnostic',
    'DomainValidationError',
    'ExpandedAtomSites',
    'ExperimentBase',
    'ExperimentFactory',
    'ExperimentType',
    'Experiments',
    'FitPreamble',
    'FitResultBase',
    'FitStatus',
    'Geom',
    'GeomBond',
    'InstrumentBase',
    'InstrumentFactory',
    'IoError',
    'IterationRecord',
    'LeastSquaresFitResult',
    'LineSegment',
    'LinkedStructure',
    'LinkedStructures',
    'NoAbsorption',
    'Parameter',
    'PdCwlData',
    'PdDataBase',
    'PdExperimentBase',
    'PdTofData',
    'PeakBase',
    'PeakFactory',
    'PeakProfileTypeEnum',
    'PolynomialTerm',
    'PowderCwlReflnData',
    'PowderReflnDataBase',
    'PowderTofReflnData',
    'PrefOrient',
    'PrefOrients',
    'Project',
    'ProjectMetadata',
    'RadiationProbeEnum',
    'SampleFormEnum',
    'ScExperimentBase',
    'ScanFileRecord',
    'ScanPreamble',
    'ScatteringTypeEnum',
    'SchemaValidationError',
    'Severity',
    'SpaceGroup',
    'SpaceGroupSymop',
    'Structure',
    'StructureFactory',
    'StructureGeometry',
    'Structures',
    'SyntaxValidationError',
    'TofJorgensen',
    'TofJorgensenVonDreele',
    'TofPdInstrument',
    'TofPseudoVoigt',
    'ValidationError',
    'VerbosityEnum',
    'error_report',
    'iteration_line',
    'machine_report',
    'parameter_table',
    'progress_report',
    'scan_progress_line',
    'scan_summary',
    'stream_header',
    'summary_line',
]


# The scan modes, underscored so the constant does not join the public surface. It mirrors the
# engine's closed set (edi/model.hpp `is_scan_fitting_mode`, which mirrors crysta's): the routing
# below must not be able to know about one scan mode and not the other. An unknown token never
# reaches this dispatch — the loader and the `fitting_mode` setter refuse it — so this set decides
# routing only, never validity.
_SCAN_FITTING_MODES = frozenset({'sequential', 'independent'})


class Analysis:
    """The analysis facade (ruled C) — delegation only, no product logic (ADR-0009).

    Mirrors ``project.analysis`` in diffraction-lib: ``fit()`` runs the refinement the project's
    fitting mode selects (``'sequential'`` -> ``fit_sequential``, ``'joint'`` ->
    ``fit_joint``, else ``fit``), ``calculate()`` is the
    model-only forward pattern (no arguments, results land in each experiment's
    ``data.intensity_calc``), and ``fitting_mode`` lives here in the diffraction-lib spelling
    (the engine ``Project.fitting_mode`` is public too - crysta parity). The direct
    ``project.fit()/fit_joint()/calculate()`` shortcuts remain, per the ruling; the
    calculator/minimiser selection will land on this facade as it arrives.
    """

    def __init__(self, project: Project) -> None:
        self._project = project

    @property
    def fitting_mode(self) -> str:
        return self._project.fitting_mode

    @fitting_mode.setter
    def fitting_mode(self, value: str) -> None:
        self._project.fitting_mode = value

    @property
    def descent(self) -> str:
        # The descent-strategy selection is MODEL STATE on this facade (like fitting_mode),
        # never a fit-call argument. The id set is crysta's own registry, resolved from the
        # linked engine — `crysta fit --list-descents` prints the same listing. Reading it
        # gives the EFFECTIVE id (the engine default when nothing was selected); assigning an
        # unknown id raises ValueError naming the registered set; assigning None restores the
        # default selection. The engine
        # `Project.descent` is public too — the `fitting_mode` shape exactly.
        return self._project.descent

    @descent.setter
    def descent(self, value: str | None) -> None:
        self._project.descent = value

    def fit(
        self,
        *,
        on_iteration: _Callable[[IterationRecord], None] | None = None,
        on_start: _Callable[[FitPreamble], None] | None = None,
        on_scan_start: _Callable[[ScanPreamble], None] | None = None,
        on_file_complete: _Callable[[ScanFileRecord], None] | None = None,
        should_cancel: _Callable[[], bool] | None = None,
    ) -> FitResultBase:
        """Fit per the declared ``_fitting_mode.type``, the closed four-value set.

        ``single`` fits one experiment; ``joint`` fits several banks at once; the two scan modes
        fit every file in the declared ``_sequential_fit`` block, one after another and serially,
        writing one ``analysis/results.csv`` row per file — ``sequential`` seeding each file from
        the previous fit's converged parameters, ``independent`` seeding each from the same
        initial parameters. Any other value is refused when the project loads and when
        ``fitting_mode`` is assigned, so this dispatch never sees one.

        ``should_cancel`` is polled between iterations; once it answers true the fit stops
        cleanly and returns a ``CANCELLED`` result — a scan records no row for the unfinished
        file, writes nothing back, and its ``analysis/results.csv`` is the resume point. A
        ``KeyboardInterrupt`` raised inside any of these callbacks (Ctrl+C) is the same clean
        cancel.
        """
        # Review-1 F1: only genuine call-time options cross this seam — the fit's
        # inputs (grid, observed, sigma, patterns) come from the model alone, so no data
        # argument exists to forward. The descent selection is model state too (the `descent`
        # property above), so it crosses no signature either. ONE named native entry per
        # declared mode, each reached by its own exact token. Routing on `sequential` alone and
        # letting everything else fall through to
        # `fit()` is what made an `independent` project perform a plausible single fit of the
        # template and write no results.csv. Validity is not decided here — the loader and the
        # `fitting_mode` setter refuse anything outside the closed set, so a lookalike never
        # reaches this dispatch; these four branches only choose the entry point. The two
        # scan-event subscribers are meaningful only for the scan modes — a single/joint fit
        # has no file walk to report, so passing one there is a caller error and refuses
        # rather than being silently dropped.
        if self._project.fitting_mode == 'sequential':
            return self._project.fit_sequential(
                on_iteration=on_iteration,
                on_start=on_start,
                on_scan_start=on_scan_start,
                on_file_complete=on_file_complete,
                should_cancel=should_cancel,
            )
        if self._project.fitting_mode == 'independent':
            return self._project.fit_independent(
                on_iteration=on_iteration,
                on_start=on_start,
                on_scan_start=on_scan_start,
                on_file_complete=on_file_complete,
                should_cancel=should_cancel,
            )
        if on_scan_start is not None or on_file_complete is not None:
            raise ValueError(
                'on_scan_start/on_file_complete are scan-mode subscribers - this project '
                f"declares _fitting_mode.type '{self._project.fitting_mode}'"
            )
        if self._project.fitting_mode == 'joint':
            return self._project.fit_joint(
                on_iteration=on_iteration, on_start=on_start, should_cancel=should_cancel
            )
        return self._project.fit(
            on_iteration=on_iteration, on_start=on_start, should_cancel=should_cancel
        )

    def calculate(self) -> None:
        # The model is the single source of truth — no grid/bank/cutoff/scattering argument
        # exists; results land in each experiment's data.intensity_calc.
        self._project.calculate()

    @property
    def aliases(self) -> Aliases:
        """The project's parameter aliases (diffraction-lib ``analysis.aliases``)."""
        return self._project._aliases

    @property
    def constraints(self) -> Constraints:
        """The project's constraints (diffraction-lib ``analysis.constraints``)."""
        return self._project._constraints


def _analysis(self: Project) -> Analysis:
    """The analysis facade over this project (see :class:`Analysis`)."""
    return Analysis(self)


Project.analysis = property(_analysis)


# The TOF profile coefficient keys.
_TOF_PEAK_PARAM_KEYS = frozenset({
    'rise_alpha_0',
    'rise_alpha_1',
    'decay_beta_0',
    'decay_beta_1',
    'broad_gauss_sigma_0',
    'broad_gauss_sigma_1',
    'broad_gauss_sigma_2',
    'broad_gauss_size',
    'broad_gauss_strain',
    'broad_lorentz_gamma_0',
    'broad_lorentz_gamma_1',
    'broad_lorentz_gamma_2',
    'broad_lorentz_size',
    'broad_lorentz_strain',
})


def _reject_unknown(spec, allowed, where):
    """Fail on a misspelled/unsupported model key rather than silently ignoring it."""
    unknown = set(spec) - allowed
    if unknown:
        raise KeyError(
            f'{where}: unrecognized key(s) {sorted(unknown)}; allowed {sorted(allowed)}'
        )


# Allowlists at every accepted dict boundary — a typo raises instead of silently defaulting.
# (Scattering element symbols are intentionally open map keys and are not validated here.)
_PARAMETER_KEYS = frozenset({'value', 'uncertainty', 'free'})
_CELL_KEYS = frozenset({
    'length_a',
    'length_b',
    'length_c',
    'angle_alpha',
    'angle_beta',
    'angle_gamma',
})
_ATOM_SITE_KEYS = frozenset({
    'id',
    'type_symbol',
    'wyckoff_letter',
    'adp_type',
    'fract',  # composite (x, y, z) shorthand
    'fract_x',
    'fract_y',
    'fract_z',
    'occupancy',
    'adp_iso',
})
_ATOM_SITE_ANISO_KEYS = frozenset({
    'id',
    'adp_11',
    'adp_22',
    'adp_33',
    'adp_12',
    'adp_13',
    'adp_23',
})
_SPACE_GROUP_KEYS = frozenset({'name_h_m', 'coord_system_code', 'it_number'})
_STRUCTURE_KEYS = frozenset({
    'name',
    'space_group',
    'cell',
    'atom_sites',
    'atom_site_aniso',
    'scattering_lengths_fm',
})
# The categorised experiment dict grammar: the dict mirrors the object tree exactly.
_EXPERIMENT_KEYS = frozenset({
    'name',
    'experiment_type',
    'peak',
    'instrument',
    'linked_structure',
    'background',
    'excluded_regions',
})
_EXPERIMENT_TYPE_KEYS = frozenset({
    'sample_form',
    'beam_mode',
    'radiation_probe',
    'scattering_type',
})
_TOF_PEAK_KEYS = _TOF_PEAK_PARAM_KEYS | {'type', 'cutoff_fwhm'}
_TOF_INSTRUMENT_KEYS = frozenset({
    'calib_d_to_tof_offset',
    'calib_d_to_tof_linear',
    'calib_d_to_tof_quadratic',
    'calib_d_to_tof_reciprocal',
    'setup_twotheta_bank',
})
_LINKED_STRUCTURE_KEYS = frozenset({'structure_id', 'scale'})

# The constant-wavelength key family, mirroring the shipped crysta grammar at b9aee906: the
# rung-0 token is 'cwl-pseudo-voigt'; the two reserved rung tokens are recognised-but-refused BY
# NAME (Fork 3 (a) — accepting them would build a model edi's engine cannot compute); the beam
# modes are exactly 'time-of-flight' and 'constant wavelength' (WITH a space), cross-checked
# against the peak-type family per the four-case matrix. The CW peak/instrument key sets replace
# (never extend) the TOF ones when the peak type selects CW — a TOF key on a CW spec is rejected
# exactly as any other unknown key, and vice versa.
_TOF_PEAK_TYPES = frozenset({'tof-jorgensen', 'tof-jorgensen-von-dreele', 'tof-pseudo-voigt'})
_CW_PEAK_TYPES = frozenset({
    'cwl-pseudo-voigt',
    'cwl-thompson-cox-hastings',  # Finger-Cox-Jephcoat
    'cwl-pseudo-voigt-berar-baldinozzi-asymmetry',  # Berar-Baldinozzi
})
_RESERVED_CW_PEAK_TYPES = frozenset()
# The asymmetry keys a CW rung carries (the typed-family rule), and their defaults.
_CW_ASYMMETRY_KEYS = {
    'cwl-thompson-cox-hastings': {'asym_fcj_1': 0.0, 'asym_fcj_2': 0.0},
    'cwl-pseudo-voigt-berar-baldinozzi-asymmetry': {
        'asym_beba_a0': 0.0,
        'asym_beba_b0': 0.0,
        'asym_beba_a1': 0.0,
        'asym_beba_b1': 0.0,
        'asym_beba_limit': 180.0,
    },
}
_BEAM_MODE_TOF = 'time-of-flight'
_BEAM_MODE_CW = 'constant wavelength'
_CW_PEAK_KEYS = frozenset({
    'type',
    'cutoff_fwhm',
    'broad_gauss_u',
    'broad_gauss_v',
    'broad_gauss_w',
    'broad_lorentz_x',
    'broad_lorentz_y',
})
_CW_INSTRUMENT_KEYS = frozenset({'setup_wavelength', 'calib_twotheta_offset'})
# The optional CW line shifts — accepted from a spec, never engaged by default.
_CW_LINE_SHIFT_KEYS = frozenset({'calib_sample_displacement', 'calib_sample_transparency'})
# The X-ray CW monochromator polarization — accepted from an X-ray spec only.
_XRAY_POLARIZATION_KEYS = frozenset({
    'setup_polarization_coefficient',
    'setup_monochromator_twotheta',
})

_PEAK_PROFILE_BY_TOKEN = {
    'tof-jorgensen': PeakProfileTypeEnum.TOF_JORGENSEN,
    'tof-jorgensen-von-dreele': PeakProfileTypeEnum.TOF_JORGENSEN_VON_DREELE,
    'cwl-pseudo-voigt': PeakProfileTypeEnum.CWL_PSEUDO_VOIGT,
    'cwl-thompson-cox-hastings': PeakProfileTypeEnum.CWL_THOMPSON_COX_HASTINGS,
    'cwl-pseudo-voigt-berar-baldinozzi-asymmetry': (
        PeakProfileTypeEnum.CWL_PSEUDO_VOIGT_BERAR_BALDINOZZI_ASYMMETRY
    ),
    'tof-pseudo-voigt': PeakProfileTypeEnum.TOF_PSEUDO_VOIGT,
}
_BEAM_MODE_BY_TOKEN = {
    _BEAM_MODE_TOF: BeamModeEnum.TIME_OF_FLIGHT,
    _BEAM_MODE_CW: BeamModeEnum.CONSTANT_WAVELENGTH,
}
_SAMPLE_FORM_BY_TOKEN = {
    'powder': SampleFormEnum.POWDER,
    'single crystal': SampleFormEnum.SINGLE_CRYSTAL,
}
_RADIATION_PROBE_BY_TOKEN = {
    'neutron': RadiationProbeEnum.NEUTRON,
    'xray': RadiationProbeEnum.XRAY,
}
_SCATTERING_TYPE_BY_TOKEN = {'bragg': ScatteringTypeEnum.BRAGG, 'total': ScatteringTypeEnum.TOTAL}


def _parameter(spec):
    """Map a ``{value, uncertainty, free}`` dict *or* a bare scalar to a core ``Parameter``.

    Refinable quantities are written as the full dict; fixed conveniences (fractional
    coordinates, occupancies, ADPs) may be a plain number, taken as a fixed value (uncertainty
    0, not free). An omitted ``uncertainty`` key defaults to present ``0.0`` (compat); an
    explicit ``'uncertainty': None`` marks a refinable parameter with no prior uncertainty (the
    ``value()`` state), not a zero uncertainty.
    """
    if isinstance(spec, dict):
        _reject_unknown(spec, _PARAMETER_KEYS, 'parameter spec')
        return Parameter(spec['value'], spec.get('uncertainty', 0.0), spec.get('free', False))
    return Parameter(float(spec))


class StructureFactory:
    """Build a Structure datablock from a plain dict — sugar over the core ``Structure``.

    Presentation-only (ADR-0009): a notebook constructor mirroring diffraction-lib. The dict is the
    in-memory model shape, not a persisted format.
    """

    @classmethod
    def from_scratch(cls, *, name) -> 'Structure':
        """Create a minimal default structure with the given name.

        diffraction-lib ``StructureFactory.from_scratch``.
        """
        structure = Structure()
        structure.name = name
        return structure

    @classmethod
    def from_cif_str(cls, cif_str) -> 'Structure':
        """Create a structure by parsing CIF/.edi text.

        diffraction-lib ``StructureFactory.from_cif_str``.
        """
        return _structure_from_edi_text(cif_str)

    @classmethod
    def from_cif_path(cls, cif_path) -> 'Structure':
        """Create a structure by reading and parsing a CIF/.edi file.

        diffraction-lib ``StructureFactory.from_cif_path``.
        """
        return _structure_from_edi_text(_Path(cif_path).read_text(encoding='utf-8'))

    @staticmethod
    def from_dict(spec):
        _reject_unknown(spec, _STRUCTURE_KEYS, 'StructureFactory.from_dict')
        structure = Structure()
        if 'name' in spec:
            structure.name = spec['name']
        if 'space_group' in spec:
            # The space-group category — a dict {name_h_m, coord_system_code}. The old
            # plain-string form is a retired spelling and refuses rather than half-loading.
            group_spec = spec['space_group']
            if not isinstance(group_spec, dict):
                raise KeyError(
                    "StructureFactory.from_dict: unrecognized bare-string 'space_group' — the "
                    "space-group CATEGORY is a dict {'name_h_m': ..., 'coord_system_code': ...}"
                )
            _reject_unknown(
                group_spec, _SPACE_GROUP_KEYS, 'StructureFactory.from_dict space_group'
            )
            if 'name_h_m' in group_spec:
                structure.space_group.name_h_m = group_spec['name_h_m']
            if 'coord_system_code' in group_spec:
                structure.space_group.coord_system_code = group_spec['coord_system_code']
            if 'it_number' in group_spec:
                structure.space_group.it_number = int(group_spec['it_number'])

        cell = Cell()
        cell_spec = spec.get('cell', {})
        _reject_unknown(cell_spec, _CELL_KEYS, 'StructureFactory.from_dict cell')
        for edge in sorted(_CELL_KEYS):
            if edge in cell_spec:
                setattr(cell, edge, _parameter(cell_spec[edge]))
        structure.cell = cell

        sites = []
        for site_spec in spec.get('atom_sites', ()):
            _reject_unknown(site_spec, _ATOM_SITE_KEYS, 'StructureFactory.from_dict atom_site')
            site = AtomSite()
            site.id = site_spec.get('id', '')
            site.type_symbol = site_spec.get('type_symbol', '')
            site.wyckoff_letter = site_spec.get('wyckoff_letter', '')
            site.adp_type = site_spec.get('adp_type', 'Biso')
            fract_x, fract_y, fract_z = site_spec.get('fract', (0.0, 0.0, 0.0))
            site.fract_x = _parameter(site_spec.get('fract_x', fract_x))
            site.fract_y = _parameter(site_spec.get('fract_y', fract_y))
            site.fract_z = _parameter(site_spec.get('fract_z', fract_z))
            site.occupancy = _parameter(site_spec.get('occupancy', 1.0))
            site.adp_iso = _parameter(site_spec.get('adp_iso', 0.0))
            sites.append(site)
        # The keyed collection has no wholesale setter. The declared sites are admitted as ONE
        # list, so a duplicate id is refused by name instead of being collapsed by add()'s
        # upsert.
        structure.atom_sites._assign(sites)

        # The anisotropic sites' tensors, in each site's declared type. Without them, each
        # anisotropic site holds the tensor of its isotropic value.
        tensors = []
        for tensor_spec in spec.get('atom_site_aniso', ()):
            _reject_unknown(
                tensor_spec, _ATOM_SITE_ANISO_KEYS, 'StructureFactory.from_dict atom_site_aniso'
            )
            tensor = AtomSiteAniso()
            tensor.id = tensor_spec.get('id', '')
            for component in ('adp_11', 'adp_22', 'adp_33', 'adp_12', 'adp_13', 'adp_23'):
                setattr(tensor, component, _parameter(tensor_spec.get(component, 0.0)))
            tensors.append(tensor)
        if 'atom_site_aniso' in spec:
            structure.atom_site_aniso._assign(tensors)

        # Element -> b_c (fm) for crysta::NeutronScattering (empty => the engine's default table).
        structure.scattering_lengths_fm = {
            str(element): float(b_c)
            for element, b_c in spec.get('scattering_lengths_fm', {}).items()
        }
        return structure


def _cw_instrument_keys(experiment):
    """The instrument keys a CW spec may carry: the X-ray polarization pair on X-ray only."""
    keys = _CW_INSTRUMENT_KEYS | _CW_LINE_SHIFT_KEYS
    if experiment.experiment_type.radiation_probe == RadiationProbeEnum.XRAY:
        keys |= _XRAY_POLARIZATION_KEYS
    return keys


def _engage_cw_members(experiment, peak_type):
    """Engage a CW experiment's members at their defaults, its rung's asymmetry slots included."""
    for member in sorted(_CW_PEAK_KEYS - {'type', 'cutoff_fwhm'}):
        setattr(experiment.peak, member, Parameter(0.0))
    for member, default in _CW_ASYMMETRY_KEYS.get(peak_type, {}).items():
        setattr(experiment.peak, member, Parameter(default))
    for member in sorted(_CW_INSTRUMENT_KEYS):
        setattr(experiment.instrument, member, Parameter(0.0))


def _resolve_factory_kind(peak_spec, experiment_type_spec, where):
    """Resolve (peak_type_token, beam_mode_token, is_cw) for a factory spec, fail-closed.

    Mirrors the loader's four-case matrix: a reserved rung token is refused BY NAME, an unknown
    token is refused, a beam mode must be one of the two shipped tokens and must match the
    peak-type family. An absent ``peak.type`` keeps the historical TOF path; an absent
    ``experiment_type.beam_mode`` is not an error (the mode comes from the peak family alone).
    """
    peak_type = peak_spec.get('type', '')
    if peak_type in _RESERVED_CW_PEAK_TYPES:
        raise ValueError(
            f"{where}: peak type '{peak_type}' is a reserved constant-wavelength profile this "
            'build cannot compute yet'
        )
    if peak_type and peak_type not in _TOF_PEAK_TYPES and peak_type not in _CW_PEAK_TYPES:
        raise ValueError(
            f"{where}: unsupported peak type '{peak_type}' (expected one of "
            f'{sorted(_TOF_PEAK_TYPES | _CW_PEAK_TYPES)})'
        )
    is_cw = peak_type in _CW_PEAK_TYPES
    beam_mode = experiment_type_spec.get('beam_mode', '')
    if beam_mode:
        if beam_mode not in _BEAM_MODE_BY_TOKEN:
            raise ValueError(
                f"{where}: beam_mode '{beam_mode}' is not a known beam mode "
                f"(expected '{_BEAM_MODE_TOF}' or '{_BEAM_MODE_CW}')"
            )
        if (beam_mode == _BEAM_MODE_CW) != is_cw:
            raise ValueError(
                f"{where}: beam_mode '{beam_mode}' contradicts peak type "
                f"'{peak_type or 'tof-jorgensen'}'"
            )
    return peak_type, beam_mode, is_cw


def _apply_background(experiment, points):
    background = []
    for position, intensity in points:
        point = LineSegment()
        point.position = float(position)
        point.intensity = _parameter(intensity)
        background.append(point)
    experiment.background = background


def _apply_experiment_type(experiment, spec, where):
    """Set the typed experiment-type axes from their verbatim tokens, fail-closed."""
    _reject_unknown(spec, _EXPERIMENT_TYPE_KEYS, where)
    for key, table in (
        ('sample_form', _SAMPLE_FORM_BY_TOKEN),
        ('beam_mode', _BEAM_MODE_BY_TOKEN),
        ('radiation_probe', _RADIATION_PROBE_BY_TOKEN),
        ('scattering_type', _SCATTERING_TYPE_BY_TOKEN),
    ):
        if key in spec:
            token = spec[key]
            if token not in table:
                raise ValueError(
                    f"{where}: {key} '{token}' is not a known token "
                    f'(expected one of {sorted(table)})'
                )
            setattr(experiment.experiment_type, key, table[token])


def _apply_plain_experiment_keys(experiment, spec):
    """Apply the top-level experiment keys that are plain assignments, not category parsing.

    `name` and `excluded_regions` carry no sub-grammar and no parameter wrapping, so they do not
    belong beside the category blocks — and inlining them pushed `from_dict` past its branch
    ceiling. Keeping them here lets the dict be the whole model declaration (nothing set on the
    object after `from_dict` returns) without growing that function.
    """
    if 'name' in spec:
        experiment.name = spec['name']
    if 'excluded_regions' in spec:
        experiment.excluded_regions = list(spec['excluded_regions'])


class ExperimentFactory:
    """Build an ExperimentBase from a dict mirroring the categorised tree — sugar over the core.

    Registry-backed since the structural adoption: ``registry()`` lists the selector token of
    every registered concrete experiment; ``register()`` is the extension seam a later
    experiment kind uses.


    The dict grammar IS the object grammar — ``experiment_type`` / ``peak`` /
    ``instrument`` / ``linked_structure`` / ``background``, with the four experiment-type axes
    given as their verbatim tokens and ``peak.type`` selecting the key family
    (``'cwl-pseudo-voigt'`` swaps in the CW peak/instrument key sets, which REPLACE the TOF
    ones). No factory default frees a parameter; freeing one is the caller's act.
    """

    _registry: _ClassVar[dict] = {'bragg-pd': BraggPdExperiment}

    @classmethod
    def registry(cls) -> dict:
        return dict(cls._registry)

    @classmethod
    def register(cls, token_or_cls, experiment_cls=None) -> type:
        if experiment_cls is None:
            experiment_cls = token_or_cls
            token = getattr(experiment_cls, 'tag', None) or experiment_cls.__name__
        else:
            token = token_or_cls
        cls._registry[token] = experiment_cls
        return experiment_cls

    @classmethod
    def supported_tags(cls) -> list:
        return sorted(t for t, c in cls._registry.items() if c is not None)

    @classmethod
    def default_tag(cls) -> str:
        return 'bragg-pd'

    @classmethod
    def create(cls, tag='bragg-pd') -> 'BraggPdExperiment':
        experiment_cls = cls._registry.get(tag)
        if experiment_cls is None:
            msg = f"'{tag}' has no registered concrete experiment class"
            raise ValueError(msg)
        return experiment_cls()

    @classmethod
    def create_default_for(cls, _value) -> 'BraggPdExperiment':
        return cls.create('bragg-pd')

    @classmethod
    def from_cif_str(cls, cif_str) -> 'BraggPdExperiment':
        """Create an experiment from CIF/.edi text.

        diffraction-lib ``ExperimentFactory.from_cif_str``.
        """
        return _experiment_from_edi_text(cif_str)

    @classmethod
    def from_cif_path(cls, cif_path) -> 'BraggPdExperiment':
        """Create an experiment by reading and parsing a CIF/.edi file.

        diffraction-lib ``ExperimentFactory.from_cif_path``.
        """
        return _experiment_from_edi_text(_Path(cif_path).read_text(encoding='utf-8'))

    @classmethod
    def from_data_path(
        cls,
        *,
        name,
        data_path,
        sample_form='',
        beam_mode='',
        radiation_probe='',
        scattering_type='',
    ) -> 'BraggPdExperiment':
        """A from_scratch experiment with measured data read from a 2-3 column ASCII file.

        ``x y [sy]``: a missing ``sy`` is approximated as ``sqrt(y)`` and any ``sy < 1e-4``
        is replaced with ``1.0``.
        """
        experiment = cls.from_scratch(
            beam_mode=beam_mode,
            name=name,
            sample_form=sample_form,
            radiation_probe=radiation_probe,
            scattering_type=scattering_type,
        )
        rows = _np.loadtxt(data_path, ndmin=2)
        if rows.size == 0 or rows.shape[1] not in {2, 3}:
            raise ValueError(f"data file '{data_path}': expected 2 or 3 columns `x y [sy]`")
        x = rows[:, 0]
        y = rows[:, 1]
        if rows.shape[1] == 3:
            sy = rows[:, 2]
        else:
            if (y < 0.0).any():
                raise ValueError(
                    f"data file '{data_path}': cannot derive sqrt(y) sigma for a negative "
                    'intensity'
                )
            sy = _np.sqrt(y)
        if not (_np.isfinite(x).all() and _np.isfinite(y).all() and _np.isfinite(sy).all()):
            raise ValueError(f"data file '{data_path}': non-finite value")
        sy = _np.where(sy < 1e-4, 1.0, sy)
        if beam_mode == _BEAM_MODE_CW:
            experiment.data = PdCwlData(
                two_theta=x.tolist(),
                intensity_meas=y.tolist(),
                intensity_meas_su=sy.tolist(),
            )
        else:
            experiment.data = PdTofData(
                time_of_flight=x.tolist(),
                intensity_meas=y.tolist(),
                intensity_meas_su=sy.tolist(),
            )
        return experiment

    @staticmethod
    def from_scratch(
        peak_type='',
        beam_mode='',
        name='',
        sample_form='',
        radiation_probe='',
        scattering_type='',
    ):
        """A default ExperimentBase of the given peak type token — every parameter fixed.

        The from-scratch starting point: the same fail-closed resolution as
        ``from_dict``. An omitted ``peak_type`` is derived from ``beam_mode`` —
        ``'constant wavelength'`` selects the CW rung 0, anything else the historical
        ``tof-jorgensen``. A CW experiment starts with all five CW peak parameters and both CW
        instrument parameters present, fixed at 0.
        """
        peak_spec = {}
        if peak_type:
            peak_spec['type'] = peak_type
        elif beam_mode == _BEAM_MODE_CW:
            peak_spec['type'] = 'cwl-pseudo-voigt'
        else:
            peak_spec['type'] = 'tof-jorgensen'
        type_spec = {'beam_mode': beam_mode} if beam_mode else {}
        peak_type, beam_mode, is_cw = _resolve_factory_kind(
            peak_spec, type_spec, 'ExperimentFactory.from_scratch'
        )
        experiment = BraggPdExperiment()
        if name:
            experiment.name = name
        type_axes = {}
        if sample_form:
            type_axes['sample_form'] = sample_form
        if radiation_probe:
            type_axes['radiation_probe'] = radiation_probe
        if scattering_type:
            type_axes['scattering_type'] = scattering_type
        if type_axes:
            _apply_experiment_type(experiment, type_axes, 'ExperimentFactory.from_scratch')
        experiment.peak.type = _PEAK_PROFILE_BY_TOKEN[peak_type]
        if beam_mode:
            experiment.experiment_type.beam_mode = _BEAM_MODE_BY_TOKEN[beam_mode]
        if is_cw:
            _engage_cw_members(experiment, peak_type)
        return experiment

    @staticmethod
    def from_dict(spec):
        _reject_unknown(spec, _EXPERIMENT_KEYS, 'ExperimentFactory.from_dict')
        experiment = BraggPdExperiment()
        _apply_plain_experiment_keys(experiment, spec)

        peak_spec = spec.get('peak', {})
        type_spec = spec.get('experiment_type', {})
        peak_type, _beam_mode, is_cw = _resolve_factory_kind(
            peak_spec, type_spec, 'ExperimentFactory.from_dict'
        )
        _apply_experiment_type(
            experiment, type_spec, 'ExperimentFactory.from_dict experiment_type'
        )
        if peak_type:
            experiment.peak.type = _PEAK_PROFILE_BY_TOKEN[peak_type]

        # The key family is selected by the peak type: CW replaces (never extends) the TOF sets,
        # so a TOF key on a CW spec is rejected exactly as any other unknown key, and vice versa.
        if is_cw:
            asymmetry = _CW_ASYMMETRY_KEYS.get(peak_type, {})
            peak_keys = _CW_PEAK_KEYS | set(asymmetry)
            instrument_keys = _cw_instrument_keys(experiment)
            for member, default in asymmetry.items():  # the rung's own slots, at their defaults
                setattr(experiment.peak, member, Parameter(default))
        else:
            peak_keys, instrument_keys = _TOF_PEAK_KEYS, _TOF_INSTRUMENT_KEYS
        _reject_unknown(peak_spec, peak_keys, 'ExperimentFactory.from_dict peak')
        for name in sorted(peak_keys - {'type', 'cutoff_fwhm'}):
            if name in peak_spec:
                setattr(experiment.peak, name, _parameter(peak_spec[name]))
        if 'cutoff_fwhm' in peak_spec:
            experiment.peak.cutoff_fwhm = float(peak_spec['cutoff_fwhm'])

        instrument_spec = spec.get('instrument', {})
        _reject_unknown(instrument_spec, instrument_keys, 'ExperimentFactory.from_dict instrument')
        for name in sorted(instrument_keys):
            if name in instrument_spec:
                setattr(experiment.instrument, name, _parameter(instrument_spec[name]))

        linked_spec = spec.get('linked_structure', {})
        _reject_unknown(
            linked_spec, _LINKED_STRUCTURE_KEYS, 'ExperimentFactory.from_dict linked_structure'
        )
        if 'structure_id' in linked_spec:
            experiment.linked_structure.structure_id = linked_spec['structure_id']
        if 'scale' in linked_spec:
            experiment.linked_structure.scale = _parameter(linked_spec['scale'])

        if 'background' in spec:
            _apply_background(experiment, spec['background'])
        return experiment


# The verification-page helpers stay out of `__all__` (internal, register row D51) but are always
# reachable as `edi.verification`: a submodule that is an attribute only after someone imports it
# would make the surface universe depend on import order. Last, on purpose — the module imports
# `edi` back and touches it only inside its functions.
from edi import verification as verification  # noqa: E402
