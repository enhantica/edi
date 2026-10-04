# SPDX-License-Identifier: BSD-3-Clause
"""Helpers for the documentation cross-engine verification pages.

Port of diffraction-lib's ``easydiffraction.analysis.verification`` helper surface: load
externally calculated FullProf reference profiles, populate an experiment's measured pattern from
a reference, score how closely two calculated patterns agree, and render the pass/fail agreement
table plus the plotly comparison figure the Verification pages share. Deliberately kept out of the
headline ``edi`` API and imported explicitly by the verification notebooks so those pages stay
short and readable.

Closeness metrics are computed on absolute intensities. Every *expected/asserted comparison
value* on a page is the run-time output of :func:`load_fullprof_calc_profile` over the committed
FullProf reference projects — never a value produced by edi/crysta.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

import edi

# A FullProf ``Prf=2`` IGOR profile row has columns TOF, Iobs, Icalc, Diff under a
# ``BEGIN``/``END`` block; the calculated intensity is column 2 (Icalc).
_IGOR_ICALC_COLUMN = 2
_IGOR_MIN_COLUMNS = 3

# A FullProf ``.prf`` tab-separated (Prf=-3) profile data row has exactly these columns:
# 2Theta/TOF, Yobs, Ycal, Yobs-Ycal, Backg. Reflection-marker rows carry a trailing ``(h k l)``
# and more columns, so they are skipped. The calculated intensity is column 2 (Ycal).
_PRF_MIN_COLUMNS = 3
_PRF_YCALC_COLUMN = 2
# A two-column ``.bac`` background row holds ``x background``.
_BAC_MIN_COLUMNS = 2

# FullProf writes a profile header (min, increment, max) in three fixed columns of this width;
# adjacent values run together when one fills its field, so the header is sliced by column when
# it cannot be split on whitespace.
_FULLPROF_HEADER_FIELD_COUNT = 3
_FULLPROF_HEADER_FIELD_WIDTH = 10

# The FullProf reference projects for the Verification pages are committed under
# knowledge/verification/fullprof/ (copied byte-identical from diffraction-lib; regenerable with
# the fullprof-fp2k skill from the committed .pcr/.dat/.irf inputs). The notebook PAGES live in
# the docs tree (docs/dev/verification/); the reference DATA stays here, beside the tests that
# assert on it (fixtures live with their tests).
_VERIFICATION_DATA_DIR = ('knowledge', 'verification')
_BUNDLED_REFERENCE_SUBPATH = ('fullprof',)

# The engine-to-identity map for candidate labels: crysta is edi's only calculation engine,
# identified by the crysta-main commit the build fetched (provenance replaces the pin —
# build-crysta.sh records it at build/crysta-src/CRYSTA_SOURCE_SHA).
_CRYSTA_PIN_RELPATH = ('build', 'crysta-src', 'CRYSTA_SOURCE_SHA')
_LINKED_STAMP_NAME = '.crysta-linked-sha'
_PIN_ABBREV = 7
_SUPPORTED_ENGINES = ('crysta',)

# A page's plotly figure is presentation, not physics, and `fig.show()` needs a notebook
# frontend — so setting this variable makes `plot_pattern_comparison` a no-op while everything
# else about the page is unchanged: the same structure, reference load, `project.calculate` and
# `assert_patterns_agree` tolerances. Unset (the notebook/docs path) plots exactly as before.
#
# This knob currently has NO setter in the repo. Its only one was the
# `tests/simulation` page-executing runner, retired under owner ruling 18 — cross-engine parity
# moved to the system tier, which calls `project.calculate` directly and never executes a page.
# The knob is kept because it remains the supported way for any headless caller to run a page,
# but nothing in the tree exercises it today.
_HEADLESS_ENV_VAR = 'EDI_VERIFICATION_HEADLESS'


def plotting_disabled() -> bool:
    """Report whether verification plots are suppressed for a headless run.

    True when ``EDI_VERIFICATION_HEADLESS`` is set to anything other than the empty string or
    ``0``. The simulation tier sets it; notebook and docs execution leave it unset.
    """
    return os.environ.get(_HEADLESS_ENV_VAR, '').strip() not in {'', '0'}


def _repo_root() -> Path:
    """Resolve the edi repository root from any supported working directory.

    Works from the repository root (the script/test working directory) and from the
    notebook working directory under nbmake — ``docs/dev/verification/`` since
    (``knowledge/verification/`` before it).
    """
    data_dir = Path(*_VERIFICATION_DATA_DIR)
    for up in (Path(), Path('..', '..'), Path('..', '..', '..')):
        if (up / data_dir).is_dir():
            return up
    return Path()


def bundled_reference_dir() -> Path:
    """Return the committed FullProf reference directory.

    Returns
    -------
    Path
        Directory holding the FullProf reference project folders.
    """
    return _repo_root().joinpath(*_VERIFICATION_DATA_DIR, *_BUNDLED_REFERENCE_SUBPATH)


# ----------------------------------------------------------------------
#  Reference-profile loaders (FullProf output formats)
# ----------------------------------------------------------------------


def _parse_fullprof_header(line: str) -> tuple[float, float, float]:
    """Parse a FullProf profile header into ``(min, increment, max)``.

    The three leading numbers are read on whitespace when they are cleanly separated, and sliced
    from fixed-width columns when they run together.
    """
    header = line.split('!', 1)[0]
    count = _FULLPROF_HEADER_FIELD_COUNT
    tokens = header.split()
    if len(tokens) >= count and all(token.count('.') <= 1 for token in tokens[:count]):
        minimum, increment, maximum = (float(token) for token in tokens[:count])
    else:
        width = _FULLPROF_HEADER_FIELD_WIDTH
        minimum, increment, maximum = (
            float(header[index * width : (index + 1) * width]) for index in range(count)
        )
    return minimum, increment, maximum


def _parse_igor_profile(lines: list[str]) -> tuple[list[float], list[float]]:
    """Parse the ``Prf=2`` IGOR ``BEGIN``/``END`` profile block."""
    x_values: list[float] = []
    icalc: list[float] = []
    started = False
    for line in lines:
        text = line.strip()
        if text == 'BEGIN':
            started = True
            continue
        if text == 'END':
            break
        fields = text.split()
        if not started or len(fields) < _IGOR_MIN_COLUMNS:
            continue
        try:
            row = (float(fields[0]), float(fields[_IGOR_ICALC_COLUMN]))
        except ValueError:
            continue
        x_values.append(row[0])
        icalc.append(row[1])
    return x_values, icalc


def _parse_tabbed_profile(lines: list[str], path: str) -> tuple[list[float], list[float]]:
    """Parse a tab/space-separated profile table by row SHAPE, not by a pinned column count.

    FullProf's tabbed exports do not agree on width, and neither a fixed count nor the header's
    own width classifies them all:

    * ``Prf=-3`` writes an 8-field header (``T.O.F. Yobs Ycal Yobs-Ycal Backg Posr (hkl) K``)
      above 5-field data rows — so matching the header width skips every data row;
    * a 4-field ``TOF Iobs Icalc Diff`` table has 4-field rows — so a hardcoded 5 skips every
      data row instead.

    What is stable across both, and is what this relies on: after the header, a data row is a
    run of numbers whose first field is the x value and whose **third** is the calculated
    intensity. Reflection-marker rows carry ``(hkl)`` and are dropped by the parenthesis test;
    header and trailer text is dropped because it does not parse as a number.
    """
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.lstrip().startswith(('2Theta', 'TOF', 'T.O.F.'))
        ),
        None,
    )
    if header_index is None:
        msg = f'FullProf profile {path}: no profile header or IGOR block found.'
        raise ValueError(msg)
    x_values: list[float] = []
    icalc: list[float] = []
    for line in lines[header_index + 1 :]:
        if '(' in line:  # reflection-marker row
            continue
        fields = line.split()
        if len(fields) < _PRF_MIN_COLUMNS:
            continue
        try:
            x_value = float(fields[0])
            y_value = float(fields[_PRF_YCALC_COLUMN])
        except ValueError:
            continue
        x_values.append(x_value)
        icalc.append(y_value)
    return x_values, icalc


def _parse_fullprof_calc_profile(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Read ``(x, Icalc)`` from a FullProf calculated-profile export.

    Handles both the ``Prf=2`` IGOR text format and the tab-separated ``Prf=-3`` format; both
    place the calculated intensity in column 2. The x axis is whatever the export carries (TOF in
    microseconds for the TOF references).

    Raises
    ------
    ValueError
        If no profile data rows are found.
    """
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    is_igor = any('IGOR' in line.upper() for line in lines[:3])
    if is_igor:
        x_values, icalc = _parse_igor_profile(lines)
    else:
        x_values, icalc = _parse_tabbed_profile(lines, path)
    if not x_values:
        msg = f'FullProf profile {path}: no calculated-profile data rows found.'
        raise ValueError(msg)
    return np.asarray(x_values), np.asarray(icalc)


def _parse_array_background(lines: list[str], path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse the ``.sub``-style header + flat-array ``.bac`` layout."""
    x_min, x_step, _x_max = _parse_fullprof_header(lines[0])
    background: list[float] = []
    for line in lines[1:]:
        for text in line.split():
            try:
                background.append(float(text))
            except ValueError:
                break  # trailing non-numeric text ends the row
    if not background:
        msg = f'FullProf .bac {path}: no background values after the header.'
        raise ValueError(msg)
    y = np.asarray(background)
    x = x_min + x_step * np.arange(y.size)
    return x, y


def _parse_columned_background(lines: list[str], path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse the two-column ``x background`` ``.bac`` layout."""
    x_values: list[float] = []
    background: list[float] = []
    for line in lines:
        text = line.strip()
        if text.startswith('!'):
            continue
        fields = text.split()
        if len(fields) < _BAC_MIN_COLUMNS:
            continue
        try:
            row = (float(fields[0]), float(fields[1]))
        except ValueError:
            continue
        x_values.append(row[0])
        background.append(row[1])
    if not x_values:
        msg = f'FullProf .bac {path}: no background data rows found.'
        raise ValueError(msg)
    return np.asarray(x_values), np.asarray(background)


def _parse_fullprof_background(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Read ``(x, background)`` from a FullProf ``Ppl=2`` ``.bac`` file.

    FullProf writes the ``.bac`` in one of two layouts, both handled here: two-column rows under
    ``!`` comments, or a ``min step max`` header followed by the values as a flat array. In both
    layouts the x axis omits the zero shift, so the caller realigns it onto the profile axis.

    Raises
    ------
    ValueError
        If the file is empty or no background data rows are found.
    """
    lines = [line for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    if not lines:
        msg = f'FullProf .bac {path}: file is empty.'
        raise ValueError(msg)
    if not lines[0].lstrip().startswith('!'):
        return _parse_array_background(lines, path)
    return _parse_columned_background(lines, path)


def load_fullprof_calc_profile(
    project_dir: str,
    profile_file: str,
    background_file: str,
    zero_shift: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Load the Bragg-only profile from FullProf calculated + background files.

    The ``.prf`` (``Prf=2`` IGOR export for the TOF references) holds the calculated profile
    ``Icalc`` on the *corrected* x grid — the Zero systematic shift is applied. The ``Ppl=2``
    ``.bac`` holds the *real* background on the uncorrected grid, so it is realigned by adding
    ``zero_shift`` (the FullProf ``Zero``) and interpolated onto the profile grid before
    subtraction (the background is smooth, so interpolation is lossless and ``Icalc`` stays
    exact). Both files are resolved inside the committed reference directory.

    Parameters
    ----------
    project_dir : str
        Reference sub-folder name (under the committed reference directory).
    profile_file : str
        File name of the FullProf calculated-profile ``.prf`` file.
    background_file : str
        File name of the FullProf ``.bac`` background file.
    zero_shift : float
        The FullProf ``Zero`` offset that realigns the ``.bac`` axis onto the profile axis.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        The corrected x grid and the clean Bragg intensities.
    """
    base = bundled_reference_dir() / project_dir
    x, icalc = _parse_fullprof_calc_profile(str(base / profile_file))
    background_x, background_y = _parse_fullprof_background(str(base / background_file))
    background = np.interp(x, background_x + zero_shift, background_y)
    return x, icalc - background


def load_corpus_fullprof_profile(case_dir: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Load ``(x, Icalc)`` from a corpus case's manifest-declared FullProf reference.

    This is the public seam for owner ruling 18 — verification reads its reference FROM THE
    CORPUS, so a test names a case and gets that case's frozen FullProf profile, with no
    on-the-fly conversion and no second copy of the data in edi.

    **The manifest picks the file, not the directory listing.** The case's ``fullprof`` block
    pins the canonical ``.prf`` by ``prf_sha256``, and this resolves the profile by hashing the
    candidates and matching that pin. Taking "the first ``.prf``" would make the answer depend
    on filename order, so a stray or superseded export sorting earlier would silently become
    the reference.

    Parameters
    ----------
    case_dir : str | pathlib.Path
        A corpus case directory (the one holding ``project/``), inside a corpus whose
        ``manifest.yml`` declares this case.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        The x grid (TOF in microseconds, or 2theta for constant-wavelength cases) and the
        calculated intensities, exactly as the frozen ``.prf`` carries them.

    Raises
    ------
    FileNotFoundError
        If the corpus manifest or the declared FullProf directory does not exist.
    ValueError
        If the case is undeclared, declares no ``fullprof`` block, omits ``prf_sha256``, or no
        ``.prf`` in the declared directory matches that pin.
    TypeError
        If the declared ``fullprof`` block is not a mapping.
    """
    case = Path(case_dir)
    manifest_path = case.parent / 'manifest.yml'
    if not manifest_path.is_file():
        msg = f'no corpus manifest beside {case}: expected {manifest_path}'
        raise FileNotFoundError(msg)
    manifest = yaml.safe_load(manifest_path.read_text(encoding='utf-8')) or {}
    entry = next(
        (c for c in manifest.get('cases', []) if str(c.get('id')) == case.name),
        None,
    )
    if entry is None:
        msg = f"corpus manifest {manifest_path} declares no case '{case.name}'"
        raise ValueError(msg)
    block = entry.get('fullprof')
    if block is None:
        msg = (
            f"case '{case.name}' declares no fullprof block — it has no paired FullProf "
            f'reference to load'
        )
        raise ValueError(msg)
    if not isinstance(block, dict):
        msg = f"case '{case.name}' fullprof block must be a mapping, got {type(block).__name__}"
        raise TypeError(msg)
    pinned = str(block.get('prf_sha256', '')).strip()
    if not pinned:
        msg = f"case '{case.name}' fullprof block pins no prf_sha256"
        raise ValueError(msg)
    fp_dir = case / str(block.get('path', 'fullprof'))
    if not fp_dir.is_dir():
        msg = f"case '{case.name}' fullprof path does not resolve: {fp_dir}"
        raise FileNotFoundError(msg)
    for candidate in sorted(fp_dir.glob('*.prf')):
        if hashlib.sha256(candidate.read_bytes()).hexdigest() == pinned:
            return _parse_fullprof_calc_profile(str(candidate))
    msg = (
        f"case '{case.name}': no .prf in {fp_dir} matches the manifest pin "
        f'{pinned[:12]}… — the frozen reference and its declaration disagree'
    )
    raise ValueError(msg)


_FULLPROF_VERSION_RE = re.compile(r'FullProf\.2k\s*\(Version\s+([0-9][0-9.]*)')


def fullprof_version(project_dir: str, summary_file: str) -> str:
    """Return the FullProf version that produced a reference.

    Reads the version from the banner a FullProf run writes near the top of its ``.sum`` (or
    ``.out``) output and returns just the number (for example ``'8.40'``).

    Raises
    ------
    ValueError
        If no version banner is found in the file.
    """
    path = bundled_reference_dir() / project_dir / summary_file
    for line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
        match = _FULLPROF_VERSION_RE.search(line)
        if match is not None:
            return match.group(1)
    msg = f'FullProf summary {path}: no FullProf version banner found.'
    raise ValueError(msg)


def fullprof_label(project_dir: str, summary_file: str) -> str:
    """Return a FullProf plot-legend label, e.g. ``'FullProf 8.40'``."""
    return f'FullProf {fullprof_version(project_dir, summary_file)}'


_VCS_HASH_LOCAL_RE = re.compile(r'^g[0-9a-f]{6,40}$')


def _edi_display_version() -> str | None:
    """Return the installed edi distribution version formatted for a page label.

    Trims a g-prefixed VCS-hash local part (for example ``+g1a2b3c``) so the label stays
    readable; returns ``None`` when the distribution is not installed.
    """
    from importlib.metadata import PackageNotFoundError, version  # noqa: PLC0415

    try:
        raw = version('easydiffraction')
    except PackageNotFoundError:
        return None
    base, separator, local = raw.partition('+')
    if separator and _VCS_HASH_LOCAL_RE.match(local):
        return base
    return raw


def _crysta_display_pin() -> str | None:
    """Return the recorded crysta-source sha abbreviated for a page label, or ``None``.

    Provenance is fail-closed: the record is a label ONLY when it is exactly one 40-hex commit
    sha. A malformed, truncated, over-long or log-prefixed record renders unknown provenance
    (``None`` — the visible ``?`` marker) rather than a truncated fragment of garbage
    masquerading as an identity.
    """
    pin_path = _crysta_provenance_path()
    try:
        pin = pin_path.read_text(encoding='utf-8').strip()
    except OSError:
        return None
    if not re.fullmatch(r'[0-9a-f]{40}', pin):
        return None
    # A consumer artifact's linked stamp identifies the crysta it was BUILT from, and the
    # artifact can be stale — the live source advanced since. Attribution must not label results
    # with a source that was never built into the selected artifact, so when the live consumer
    # source tree is resolvable and disagrees with the stamp, the identity is
    # UNKNOWN (the visible ``?`` marker), never the stale sha.
    if (
        pin_path.name == _LINKED_STAMP_NAME
        and pin_path.parent.name == 'ci-consumer'
        and _consumer_source_is_tree()
    ):
        live_src = os.environ.get('CRYSTA_CONSUMER_SRC', '')
        try:
            live = subprocess.run(
                ['git', '-C', live_src, 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=False,
            )
            live_head = live.stdout.strip() if live.returncode == 0 else ''
        except OSError:
            live_head = ''
        if live_head and live_head != pin:
            return None
    return pin[:_PIN_ABBREV]


def _consumer_source_is_tree() -> bool:
    """True iff ``CRYSTA_CONSUMER_SRC`` names a real crysta source tree.

    The same validation the build applies: a bare string is never a selector, so a typo'd or
    stale-exported value cannot redirect provenance to the consumer artifact.
    """
    live_src = os.environ.get('CRYSTA_CONSUMER_SRC', '')
    return bool(live_src) and (Path(live_src) / 'CMakeLists.txt').is_file()


def _consumer_source_selects() -> bool:
    """True iff ``CRYSTA_CONSUMER_SRC`` selects the consumer configuration.

    A validated source tree (the ``CMakeLists.txt`` witness), or the repo's hidden control — the
    exact ``'hidden-surface-control'`` literal, exempt BY NAME. Any other bare string selects
    nothing. ONE definition, shared verbatim by all four sites:
    ``lib/edi/__init__.py``, this function, ``tools/checks/python_surface_superset.py``
    (resolve_prefix) and ``tools/ci/crysta-consumer.sh``.
    """
    if os.environ.get('CRYSTA_CONSUMER_SRC', '') == 'hidden-surface-control':
        return True
    return _consumer_source_is_tree()


def _crysta_provenance_path() -> Path:
    """The provenance record for the build configuration actually consumed.

    The extension is selected per configuration. A non-ordinary selection reads the linked
    stamp core-build wrote BESIDE that artifact, so a consumer build at B is never labelled
    with the ordinary source record at A; the ordinary selection keeps the ordinary source
    record. Both reads share the fail-closed 40-hex contract above.
    """
    ordinary = (_repo_root() / 'build' / 'ci').resolve()
    ext_dir = os.environ.get('EDI_EXTENSION_DIR')
    if ext_dir:
        build_dir = Path(ext_dir).resolve().parent.parent  # <build-dir>/python/edi
    elif os.environ.get('EDI_USE_CONSUMER_BUILD') or _consumer_source_selects():
        build_dir = (_repo_root() / 'build' / 'ci-consumer').resolve()
    else:
        build_dir = ordinary
    if build_dir == ordinary:
        return _repo_root().joinpath(*_CRYSTA_PIN_RELPATH)
    return build_dir / _LINKED_STAMP_NAME


def engine_label(engine: str, note: str | None = None) -> str:
    """Return the candidate label for a verification comparison.

    Builds the edi-plus-engine candidate string, for example ``'edi 0.1.0 (crysta 1a2b3c4)'`` or,
    with a ``note``, ``'edi 0.1.0 (crysta 1a2b3c4, refined)'``. crysta is identified by the
    recorded crysta-source sha the build fetched (the float; it has no release version). An
    unresolvable identity renders a visible ``?`` marker rather than being omitted.

    Raises
    ------
    ValueError
        If ``engine`` is not a supported edi engine.
    """
    if engine not in _SUPPORTED_ENGINES:
        supported = ', '.join(_SUPPORTED_ENGINES)
        msg = f'Unknown engine {engine!r}; expected one of: {supported}.'
        raise ValueError(msg)

    edi_version = _edi_display_version()
    engine_pin = _crysta_display_pin()
    edi_text = f'edi {edi_version}' if edi_version is not None else 'edi ?'
    engine_text = f'{engine} ?' if engine_pin is None else f'{engine} {engine_pin}'
    inner = engine_text if note is None else f'{engine_text}, {note}'
    return f'{edi_text} ({inner})'


# ----------------------------------------------------------------------
#  ExperimentBase-grid population and restriction
# ----------------------------------------------------------------------


def set_reference_as_measured(experiment: object, x: np.ndarray, y: np.ndarray) -> None:
    """Use a reference profile as an experiment's measured pattern.

    Stores ``x`` as the experiment grid and ``y`` as the measured intensities, so the engine
    calculates on exactly the reference grid. Standard uncertainties default to ones.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    su = list(np.ones_like(y))
    if experiment.experiment_type.beam_mode == edi.BeamModeEnum.CONSTANT_WAVELENGTH:
        experiment.data = edi.PdCwlData(
            two_theta=list(x), intensity_meas=list(y), intensity_meas_su=su
        )
    else:
        experiment.data = edi.PdTofData(
            time_of_flight=list(x), intensity_meas=list(y), intensity_meas_su=su
        )


def _included_mask(experiment: object, size: int) -> np.ndarray:
    """Boolean mask of the experiment grid points outside every excluded region."""
    grid = np.asarray(experiment.data.axis(), dtype=float)
    if grid.size != size:
        msg = f'grid has {grid.size} points, expected {size}.'
        raise ValueError(msg)
    mask = np.ones(size, dtype=bool)
    for start, end in experiment.excluded_regions:
        mask &= ~((grid >= start) & (grid <= end))
    return mask


def restrict_to_included(experiment: object, values: np.ndarray) -> np.ndarray:
    """Restrict a full-grid array to the experiment's included points.

    An excluded region drops points from the fit, but an external reference loaded onto the full
    grid still spans every point. This filters such a full-length array down to the included
    points. Arrays that are not full-length (already restricted) and the no-exclusion case are
    returned unchanged, so the call is safe to apply unconditionally.
    """
    array = np.asarray(values)
    grid = np.asarray(experiment.data.axis(), dtype=float)
    if array.shape[:1] != grid.shape or not len(experiment.excluded_regions):
        return array
    mask = _included_mask(experiment, grid.size)
    if bool(mask.all()):
        return array
    return array[mask]


# ----------------------------------------------------------------------
#  Closeness metrics
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class ClosenessMetrics:
    """Closeness scores between a reference and a candidate pattern."""

    profile_difference_percent: float
    max_deviation_percent: float
    intensity_ratio: float
    correlation: float


def pattern_closeness(reference: np.ndarray, candidate: np.ndarray) -> ClosenessMetrics:
    """Score how closely a candidate pattern matches a reference.

    Metrics are computed on the **absolute** intensities: the RMS and maximum differences are
    expressed as a percentage of the reference (its RMS and its peak), so the tolerances are
    dataset-independent; the integrated-intensity ratio is one only when the calculated areas
    agree.

    Raises
    ------
    ValueError
        If the two patterns have different lengths.
    """
    reference = np.asarray(reference, dtype=float)
    candidate = np.asarray(candidate, dtype=float)
    if reference.shape != candidate.shape:
        msg = (
            'Reference and candidate patterns must have the same length '
            f'(got {reference.shape} and {candidate.shape}).'
        )
        raise ValueError(msg)

    reference_area = float(np.sum(reference))
    intensity_ratio = float(np.sum(candidate) / reference_area) if reference_area else float('nan')

    difference = reference - candidate
    rms_reference = float(np.sqrt(np.mean(reference**2)))
    profile_difference_percent = (
        100.0 * float(np.sqrt(np.mean(difference**2))) / rms_reference
        if rms_reference
        else float('nan')
    )
    peak_reference = float(np.max(np.abs(reference)))
    max_deviation_percent = (
        100.0 * float(np.max(np.abs(difference))) / peak_reference
        if peak_reference
        else float('nan')
    )
    correlation = float(np.corrcoef(reference, candidate)[0, 1])

    return ClosenessMetrics(
        profile_difference_percent=profile_difference_percent,
        max_deviation_percent=max_deviation_percent,
        intensity_ratio=intensity_ratio,
        correlation=correlation,
    )


# ----------------------------------------------------------------------
#  Agreement assertion table
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class AgreementTolerances:
    """Tolerance bounds for cross-pattern agreement checks.

    Defaults match the diffraction-lib reference: integrated-intensity ratio within 1 % of one,
    profile difference under 2.5 %, worst point-wise deviation under 6 %, and shape correlation
    above 0.999.
    """

    max_profile_difference_percent: float = 2.5
    max_deviation_percent: float = 6.0
    min_intensity_ratio: float = 0.99
    max_intensity_ratio: float = 1.01
    min_correlation: float = 0.999


@dataclass(frozen=True)
class _AgreementCheck:
    """One scored metric row with its pass/fail verdict."""

    metric: str
    expected: str
    actual: str
    passed: bool


def _agreement_checks(
    metrics: ClosenessMetrics,
    tolerances: AgreementTolerances,
) -> list[_AgreementCheck]:
    """Score one comparison's metrics against the tolerances."""
    profile_ok = metrics.profile_difference_percent < tolerances.max_profile_difference_percent
    deviation_ok = metrics.max_deviation_percent < tolerances.max_deviation_percent
    ratio_ok = (
        tolerances.min_intensity_ratio < metrics.intensity_ratio < tolerances.max_intensity_ratio
    )
    correlation_ok = metrics.correlation > tolerances.min_correlation
    return [
        _AgreementCheck(
            metric='Profile diff (%)',
            expected=f'< {tolerances.max_profile_difference_percent:g}',
            actual=f'{metrics.profile_difference_percent:.2f}',
            passed=profile_ok,
        ),
        _AgreementCheck(
            metric='Max deviation (%)',
            expected=f'< {tolerances.max_deviation_percent:g}',
            actual=f'{metrics.max_deviation_percent:.2f}',
            passed=deviation_ok,
        ),
        _AgreementCheck(
            metric='Area ratio',
            # `:g` gives 6 significant digits, which rounds a tight bound to a value the reader
            # cannot distinguish from 1 — and a bound that prints as "1 to 1" reads as impossible
            # rather than strict. Both columns carry enough digits to show the bound and the
            # measurement apart at every tolerance the corpus uses.
            expected=(
                f'{tolerances.min_intensity_ratio:.10g} to {tolerances.max_intensity_ratio:.10g}'
            ),
            actual=f'{metrics.intensity_ratio:.6f}',
            passed=ratio_ok,
        ),
        _AgreementCheck(
            metric='Shape correlation',
            # Same reason as the area ratio: `> 0.999999998` printed as `> 1` under `:g`.
            expected=f'> {tolerances.min_correlation:.12g}',
            actual=f'{metrics.correlation:.9f}',
            passed=correlation_ok,
        ),
    ]


# Red for out-of-tolerance values in the in-plot metrics box, matching the candidate-curve
# colour (Plotly annotations accept limited HTML).
_ANNOTATION_FAIL_COLOR = 'rgb(214, 39, 40)'


def closeness_annotation(
    metrics: ClosenessMetrics,
    tolerances: AgreementTolerances | None = None,
) -> list[str]:
    """Return in-plot metric lines with pass/fail icons.

    Each line carries a check or cross icon and shows an out-of-tolerance value in red,
    mirroring the agreement table.
    """
    tolerances = tolerances or AgreementTolerances()
    lines: list[str] = []
    for check in _agreement_checks(metrics, tolerances):
        icon = '✅' if check.passed else '❌'
        value = (
            check.actual
            if check.passed
            else f'<span style="color:{_ANNOTATION_FAIL_COLOR}">{check.actual}</span>'
        )
        lines.append(f'{icon} {check.metric}: {value}')
    return lines


def _render_agreement_table(rows: list[list[str]]) -> None:
    """Print the agreement table as plain fixed-width text."""
    headers = ['Comparison', 'Metric', 'Expected', 'Actual', 'OK']
    widths = [
        max(len(headers[column]), *(len(row[column]) for row in rows))
        for column in range(len(headers))
    ]
    aligns = ['<', '<', '>', '>', '^']
    header_line = '  '.join(
        f'{headers[column]:{aligns[column]}{widths[column]}}' for column in range(len(headers))
    )
    print(f'  {header_line}')
    print(f'  {"-" * len(header_line)}')
    for row in rows:
        body = '  '.join(
            f'{row[column]:{aligns[column]}{widths[column]}}' for column in range(len(headers))
        )
        print(f'  {body}')


def assert_patterns_agree(
    comparisons: list[tuple[str, np.ndarray, np.ndarray]],
    *,
    tolerances: AgreementTolerances | None = None,
    known_discrepancy: bool = False,
    reason: str | None = None,
) -> bool:
    """Assert one or more pattern pairs meet their documented expectation.

    Each comparison is scored with :func:`pattern_closeness` and checked against ``tolerances``.
    A single table summarises every metric with a check/cross icon.

    The assertion is two-sided and driven by ``known_discrepancy``:

    * ``known_discrepancy=False`` (default) asserts the patterns **agree** — the page is a
      regression test, and any out-of-tolerance metric raises ``AssertionError``.
    * ``known_discrepancy=True`` asserts that **every** listed comparison **still disagrees** —
      the documented known-bad state. If any comparison has started agreeing within tolerance it
      raises ``AssertionError`` so the now-fixed comparison fails CI and must be re-gated by
      hand. A known-bad comparison cannot mask a regression in an expected-good one: keep
      expected-good comparisons in their own default (gated) call.

    Raises
    ------
    ValueError
        If ``known_discrepancy=True`` is given without a non-empty ``reason``.
    AssertionError
        If the expectation is not met.
    """
    if known_discrepancy and not (reason and reason.strip()):
        msg = (
            '`known_discrepancy=True` requires a non-empty `reason` '
            'explaining the known-bad state (shown on the page).'
        )
        raise ValueError(msg)

    tolerances = tolerances or AgreementTolerances()
    rows: list[list[str]] = []
    failures: list[str] = []
    agreeing: list[str] = []
    for label, reference, candidate in comparisons:
        checks = _agreement_checks(pattern_closeness(reference, candidate), tolerances)
        comparison_failed = False
        for index, check in enumerate(checks):
            rows.append([
                label if index == 0 else '',
                check.metric,
                check.expected,
                check.actual,
                '✅' if check.passed else '❌',
            ])
            if not check.passed:
                failures.append(f'{label} · {check.metric} = {check.actual}')
                comparison_failed = True
        if not comparison_failed:
            agreeing.append(label)

    _render_agreement_table(rows)

    if known_discrepancy:
        print(f'  Known discrepancy: {reason}')
        if agreeing:
            joined = ', '.join(agreeing)
            msg = (
                f'These comparisons now agree within tolerance: {joined}. '
                'A `known_discrepancy=True` call asserts that every listed comparison still '
                'disagrees; move each agreeing comparison into its own gated '
                '`assert_patterns_agree(...)` call (without `known_discrepancy`), or tighten '
                'the tolerance if the match is spurious.'
            )
            raise AssertionError(msg)
        return True

    if failures:
        joined = '; '.join(failures)
        msg = f'Pattern agreement check failed: {joined}.'
        raise AssertionError(msg)
    return True


# ----------------------------------------------------------------------
#  Comparison plot (plotly, matching the reference presentation)
# ----------------------------------------------------------------------


def _x_axis_title(experiment: object) -> str:
    """The x-axis label for the experiment's beam mode (2θ for CW, TOF otherwise)."""
    kind = getattr(experiment, 'kind', None)
    if kind is not None and getattr(kind, 'name', '') == 'CONSTANT_WAVELENGTH':
        return _X_AXIS_TITLE_CW
    return _X_AXIS_TITLE


# Trace styling per the diffraction-lib renderer: reference solid line, candidate dashed line,
# residual panel below; the metrics box sits in the main panel's top-left corner.
_REFERENCE_LINE_COLOR = 'rgb(31, 119, 180)'
_CANDIDATE_LINE_COLOR = 'rgb(214, 39, 40)'
_RESIDUAL_LINE_COLOR = 'rgb(44, 160, 44)'
_LINE_WIDTH = 2.0
_X_AXIS_TITLE = 'TOF (μs)'
_X_AXIS_TITLE_CW = '2θ (deg)'
_Y_AXIS_TITLE = 'Intensity (arb. units)'
_RESIDUAL_HEIGHT_FRACTION = 0.2
_METRICS_FONT_SIZE = 12
_METRICS_INSET_PX = 8
# 'notebook_connected' alone targets CLASSIC notebook: it emits a <script> payload JupyterLab
# does not execute, so a plot cell completes silently with no figure and no error — measured
# 2026-09-10 on the verification pages. 'plotly_mimetype' is what Lab consumes (via the
# jupyterlab-plotly extension); the pair keeps classic notebook and the mkdocs-jupyter docs
# render working, so this widens the renderer chain rather than swapping it.
_PLOTLY_RENDERER = 'plotly_mimetype+notebook_connected'


def plot_pattern_comparison(
    experiment: object,
    *,
    reference: np.ndarray,
    candidate: np.ndarray,
    reference_label: str,
    candidate_label: str,
    show_metrics: bool = True,
    title: str | None = None,
) -> None:
    """Overlay a reference and a candidate calculated pattern.

    Draws the reference as a solid line and the candidate as a dashed line on the experiment's
    included grid, with a residual panel below and, by default, a closeness-metrics box in the
    top-left corner. Bragg ticks and background are omitted. The experiment supplies the x grid,
    the excluded-region restriction, and (via its ``name``) the default title.

    Parameters
    ----------
    experiment : object
        ExperimentBase supplying the grid, exclusions, and title name.
    reference : numpy.ndarray
        Reference intensities (for example FullProf), drawn as a solid line.
    candidate : numpy.ndarray
        Candidate intensities (for example edi/crysta), drawn as a dashed line.
    reference_label : str
        Legend name for the reference curve.
    candidate_label : str
        Legend name for the candidate curve.
    show_metrics : bool, default=True
        Whether to annotate the plot with closeness metrics.
    title : str | None, default=None
        Plot title; defaults to the reference presentation's dynamic title.

    Notes ----- Returns immediately without drawing when :func:`plotting_disabled` is true;
    the page's assertions are unaffected.
    """
    if plotting_disabled():
        return

    import plotly.graph_objects as go  # noqa: PLC0415
    from plotly.subplots import make_subplots  # noqa: PLC0415

    x = restrict_to_included(experiment, np.asarray(experiment.data.axis(), dtype=float))
    reference = restrict_to_included(experiment, np.asarray(reference, dtype=float))
    candidate = restrict_to_included(experiment, np.asarray(candidate, dtype=float))

    annotation_lines: tuple[str, ...] = ()
    if show_metrics:
        metrics = pattern_closeness(reference, candidate)
        annotation_lines = tuple(closeness_annotation(metrics))

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[1.0 - _RESIDUAL_HEIGHT_FRACTION, _RESIDUAL_HEIGHT_FRACTION],
        vertical_spacing=0.05,
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=reference,
            name=reference_label,
            mode='lines',
            line={'color': _REFERENCE_LINE_COLOR, 'width': _LINE_WIDTH},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=candidate,
            name=candidate_label,
            mode='lines',
            line={'color': _CANDIDATE_LINE_COLOR, 'width': _LINE_WIDTH, 'dash': 'dash'},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=reference - candidate,
            name='Residual',
            mode='lines',
            line={'color': _RESIDUAL_LINE_COLOR, 'width': _LINE_WIDTH},
        ),
        row=2,
        col=1,
    )
    fig.update_layout(
        title=title or f"Calculated pattern comparison for 🔬 '{experiment.name}'",
        template='plotly_white',
        # 750 total at the 0.8/0.2 row split: a 600 px main panel, 1.5x the earlier 400 px.
        # Both rows scale together, so the residual keeps the main area's units per pixel.
        height=750,
        # Inside the axes, top right: the legend is short and the top-right corner of a
        # diffraction pattern is empty, so an outside legend only steals plot width.
        legend={
            'xref': 'paper',
            'yref': 'paper',
            'x': 1.0,
            'y': 1.0,
            'xanchor': 'right',
            'yanchor': 'top',
            'bgcolor': 'rgba(255, 255, 255, 0.8)',
            'bordercolor': 'rgb(190, 199, 208)',
            'borderwidth': 1,
        },
    )
    fig.update_xaxes(title_text=_x_axis_title(experiment), row=2, col=1)
    fig.update_yaxes(title_text=_Y_AXIS_TITLE, row=1, col=1)
    # The residual shares the PATTERN's units-per-pixel, not its own autoscale. Autoscaling it
    # made a residual of +-1.5 counts fill its panel beside peaks of 3000 — visually identical
    # to a bad fit. Deriving the range from the pattern span and the row-height ratio keeps one
    # count the same distance in both panels, so the residual looks as small as it is.
    pattern_span = float(np.nanmax(reference) - min(0.0, float(np.nanmin(reference))))
    if np.isfinite(pattern_span) and pattern_span > 0.0:
        residual_half = (
            pattern_span * _RESIDUAL_HEIGHT_FRACTION / (1.0 - _RESIDUAL_HEIGHT_FRACTION) / 2.0
        )
        fig.update_yaxes(range=[-residual_half, residual_half], row=2, col=1)
    if annotation_lines:
        fig.add_annotation(
            text='<br>'.join(annotation_lines),
            xref='x domain',
            yref='y domain',
            x=0.0,
            y=1.0,
            xshift=_METRICS_INSET_PX,
            yshift=-_METRICS_INSET_PX,
            xanchor='left',
            yanchor='top',
            align='left',
            showarrow=False,
            font={'size': _METRICS_FONT_SIZE},
            bordercolor='rgb(190, 199, 208)',
            borderwidth=1,
            borderpad=4,
            bgcolor='rgba(255, 255, 255, 0.8)',
            row=1,
            col=1,
        )
    fig.show(renderer=_PLOTLY_RENDERER)
