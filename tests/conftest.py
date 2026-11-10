# SPDX-License-Identifier: BSD-3-Clause
"""Shared test wiring: session producers, golden-pin bounds, and corpus resolution.

RETIRED the measured `heavy` marker this file used to derive from
``tests/per-pr-runtimes.tsv`` (per-test rows and module-fixture costs alike). The marker
was a selection derived from a measurement — invisible by construction and fail-open for
unmeasured nodes. Selection now lives in the three named groups declared in
``tests/test-groups.json`` (local-before-PR / CI-on-PR / CI-on-merge), each naming TIERS;
with every tier meeting its ruled per-test bound, no group deselects anything by runtime.
The manifest and its per-tier ratchet (``tools/checks/per_pr_runtimes.py``) stay the
measured guard, and the audit refuses any marker-based deselection returning.
"""

from __future__ import annotations

import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import NamedTuple

import edi
import pytest


def pytest_configure() -> None:
    """Parent options have been parsed; nested pytest owns its own arguments.

    Inheriting the parent's basetemp destroys its scratch directory. Inherited
    selectors likewise change a child oracle's test set. Tests exercising an
    explicit child selector set it in that child's environment themselves.
    """
    os.environ.pop('PYTEST_ADDOPTS', None)


def calculator_load_warning(source: Path) -> str:
    """Owner decision (2026-09-29): warn for the declared unsupported calculator.

    Expectations come from the input files, including saved projects that now declare
    crysta or omit the tag. Exact stderr comparisons still reject unrelated diagnostics.
    """
    declared = dict.fromkeys(
        shlex.split(line)[1]
        for experiment in sorted((source / 'experiments').glob('*.edi'))
        for line in experiment.read_text(encoding='utf-8').splitlines()
        if line.startswith('_calculator.type ')
    )
    return ''.join(
        f'Warning: unsupported _calculator.type "{value}" - using crysta\n'
        for value in declared
        if value != 'crysta'
    )


def tree_bytes_with_normalized_project_metadata(
    root: Path,
    *fields: str,
) -> dict[str, bytes]:
    """Read a whole saved tree while replacing only named project-record values.

    The path set and every other byte remain part of the comparison. This is deliberately
    narrower than dropping ``project.edi``: a new, missing, duplicated, or otherwise changed
    record still fails the whole-tree gate.
    """
    snapshot = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }
    if not fields:
        return snapshot

    assert 'project.edi' in snapshot, (
        'a saved-tree comparison that normalizes project metadata requires project.edi to exist'
    )
    record = snapshot['project.edi']
    for field in fields:
        assert field in {'created', 'last_modified'}, (
            'saved-tree normalization is restricted to the two wall-clock metadata fields'
        )
        pattern = re.compile(
            rb'(?m)^(_metadata\.' + re.escape(field.encode()) + rb'[ \t]+).+?(\r?\n|$)'
        )
        assert len(pattern.findall(record)) == 1, (
            f'project.edi must carry exactly one _metadata.{field} before its wall-clock value '
            'can be normalized for a saved-tree comparison'
        )
        record = pattern.sub(rb'\1<NORMALIZED-WALL-CLOCK>\2', record, count=1)
    snapshot['project.edi'] = record
    return snapshot


def project_tree_parts(
    root: Path, *, normalize_fit_time: bool = False
) -> tuple[dict[str, bytes], bytes]:
    """Split a saved tree, optionally masking only a valid fit's wall-clock seconds.

    Cross-CLI fits now persist _fit_result. All its scientific
    fields, paths, whitespace and field presence remain exact comparison inputs.
    """
    snapshot = tree_bytes_with_normalized_project_metadata(root)
    record = snapshot.pop('project.edi', None)
    assert record is not None, 'a saved project tree must carry project.edi at its root'
    if normalize_fit_time:
        analysis = snapshot.get('analysis/analysis.edi')
        assert analysis is not None, 'cross-CLI fit comparison requires saved analysis.edi'
        pattern = re.compile(
            rb'(?m)^(_fit_result\.fitting_time[ \t]+)([^ \t\r\n]+)([ \t]*)(\r?\n|$)'
        )
        values = pattern.findall(analysis)
        assert len(values) == 1, (
            'cross-CLI fit comparison requires exactly one fitting_time scalar'
        )
        duration = float(values[0][1])
        assert math.isfinite(duration) and duration > 0, (
            'cross-CLI fitting_time must be finite positive seconds before normalization'
        )
        snapshot['analysis/analysis.edi'] = pattern.sub(
            rb'\1<NORMALIZED-WALL-CLOCK>\3\4', analysis, count=1
        )
    return snapshot, record


def project_record_value(record: bytes, field: str) -> bytes:
    """Return one metadata token while refusing a missing or duplicated field."""
    pattern = re.compile(
        rb'(?m)^_metadata\.' + re.escape(field.encode()) + rb'[ \t]+(.+?)(?:\r?\n|$)'
    )
    values = pattern.findall(record)
    assert len(values) == 1, (
        f'project.edi must carry exactly one _metadata.{field} value for this assertion'
    )
    return values[0]


def project_record_datetime(record: bytes, field: str) -> datetime:
    """Parse one writer-owned STAR datetime token as a materializable value."""
    token = project_record_value(record, field)
    assert token.startswith(b'"') and token.endswith(b'"'), (
        f'project.edi _metadata.{field} must use the writer-owned quoted STAR datetime spelling'
    )
    return datetime.strptime(token[1:-1].decode(), '%d %b %Y %H:%M:%S').replace(tzinfo=UTC)


def project_record_without_fields(record: bytes, *fields: str) -> bytes:
    """Remove named metadata lines only after proving each occurs exactly once."""
    for field in fields:
        project_record_value(record, field)
        record = re.sub(
            rb'(?m)^_metadata\.' + re.escape(field.encode()) + rb'[ \t]+.+?(?:\r?\n|$)',
            b'',
            record,
            count=1,
        )
    return record


class SessionDocsBuild(NamedTuple):
    """The shared strict-docs-build producer's contract."""

    returncode: int
    output: str
    site_dir: Path


@pytest.fixture(scope='session')
def session_docs_build(tmp_path_factory: pytest.TempPathFactory) -> SessionDocsBuild:
    """ONE strict mkdocs build per session (the docs-build dedup).

    The e01-scaffold and c09_t16 hidden gates each paid their own ~11.6 s strict build of the
    same tree; both now consume this single shared build. The site renders into a session tmp
    dir so the working tree is never mutated; the gate semantics (strict mode, this checkout's
    docs) are unchanged — consumers assert on the returncode, the captured output, and the
    rendered site.
    """
    root = Path(__file__).resolve().parents[1]
    site_dir = tmp_path_factory.mktemp('session-docs-build') / 'site'
    completed = subprocess.run(
        [sys.executable, '-m', 'mkdocs', 'build', '--strict', '--site-dir', str(site_dir)],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    return SessionDocsBuild(completed.returncode, completed.stdout + completed.stderr, site_dir)


class SessionJointFit(NamedTuple):
    """The F-live producer's exposed contract."""

    project: object  # the in-process model load of the same case (no fit)
    outcome: SimpleNamespace  # the observed fit's outcome view (values/esd/start/banks/...)
    record: dict  # the harness's full JSON transcript (incl. callback history + write-back)
    observations: list[str]  # native I/O + subprocess events the observer logged during the fit


def _build_native_observer(destination: Path) -> tuple[Path, str]:
    """Compile the c08_t2 native I/O observer for preloading into the producer subprocess."""
    compiler = shutil.which('cc')
    assert compiler is not None, 'the F-live producer requires the pinned C compiler'
    source = Path(__file__).resolve().parents[1] / 'tests' / 'unit' / 'cpp'
    observer_source = source / 'c08_t2_native_observer.c'
    if sys.platform.startswith('linux'):
        library = destination / 'session_native_observer.so'
        command = [compiler, '-shared', '-fPIC', str(observer_source), '-ldl', '-o', str(library)]
        preload_variable = 'LD_PRELOAD'
    elif sys.platform == 'darwin':
        library = destination / 'session_native_observer.dylib'
        command = [compiler, '-dynamiclib', str(observer_source), '-o', str(library)]
        preload_variable = 'DYLD_INSERT_LIBRARIES'
    else:
        raise AssertionError(f'no fail-closed native I/O observer for {sys.platform!r}')
    completed = subprocess.run(
        command, cwd=destination, check=False, capture_output=True, text=True, timeout=120
    )
    assert completed.returncode == 0, (
        'the native I/O observer must compile before its observations can be trusted; '
        f'command={command!r}, exit={completed.returncode}\n'
        f'stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}'
    )
    return library, preload_variable


@pytest.fixture(scope='session')
def session_joint_fit(tmp_path_factory: pytest.TempPathFactory) -> SessionJointFit:
    """The F-live producer — the ONE declared live fit anchor.

    Runs a single joint refinement of the corpus case ``ncaf-wish-3bank-s5`` (the cheapest
    structurally-adequate vehicle — multi-bank, absorption layout, shared and per-bank
    parameters, distinct bank metrics, convergence) through the public edi surface, once per
    session, INSIDE the preloaded native I/O observer — the harness subprocess is the one
    place the fit runs, with the callback history attached and the post-fit model parameter
    table (the write-back evidence) emitted in its transcript. Consumers assert live
    properties on the returned contract — value/ESD/write-back completeness over the case's
    full value set, per-bank metric distinctness, and the I/O invariant — never on a cached
    or related-case result. The converged numbers themselves are held by the case's
    FullProf-referenced ``expected.json`` (I16) and its ``goldens/joint-default.json`` F-rec
    record, not re-pinned here.
    """
    case = corpus_case_dir('ncaf-wish-3bank-s5')
    workdir = tmp_path_factory.mktemp('session-joint-fit')
    library, preload_variable = _build_native_observer(workdir)
    log_path = workdir / 'fit-native.log'
    environment = os.environ.copy()
    environment['EDI_C08_NATIVE_OBSERVER_LOG'] = str(log_path)
    previous = environment.get(preload_variable)
    environment[preload_variable] = (
        str(library) if not previous else os.pathsep.join((str(library), previous))
    )
    if sys.platform == 'darwin':
        environment['DYLD_FORCE_FLAT_NAMESPACE'] = '1'
    harness = Path(__file__).resolve().parent / 'system' / 'py' / 'session_joint_fit_harness.py'
    completed = subprocess.run(
        [sys.executable, str(harness), str(case / 'project')],
        cwd=workdir,
        env=environment,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    record = json.loads(completed.stdout)
    assert log_path.is_file(), 'the native observer did not initialise in the producer'
    observations = log_path.read_text(encoding='utf-8').splitlines()

    outcome = SimpleNamespace(
        status=record['status'],
        converged=record['converged'],
        iterations=record['iterations'],
        reduced_chi_square=record['reduced_chi_square'],
        rwp=record['rwp'],
        values=record['values'],
        uncertainty=record['uncertainty'],
        banks=[SimpleNamespace(**bank) for bank in record['banks']],
    )
    project = edi.Project.load(case / 'project')
    return SessionJointFit(project, outcome, record, observations)


def frec_golden_record(case_id: str, label: str) -> dict[str, str]:
    """Parse one committed F-rec golden's machine record into a key->value map.

    The golden is the corpus-record artifact (`goldens/<label>.json` in the case directory):
    a provenance-stamped transcript of the crysta CLI's full-verbosity record. Consumers get
    the parsed record; the provenance stays in the artifact for review.
    """
    golden_path = corpus_case_dir(case_id) / 'goldens' / f'{label}.json'
    payload = json.loads(golden_path.read_text(encoding='utf-8'))
    record: dict[str, str] = {}
    for line in payload['record'].splitlines():
        key, _, value = line.partition('=')
        assert key and value, f'malformed golden record line: {line!r}'
        assert key not in record, f'duplicate golden record key: {key}'
        record[key] = value
    return record


# ⛔ The committed F-rec goldens are the crysta CLI's OWN OUTPUT, so they are REGRESSION PINS,
# never independent references — the case's FullProf-referenced `expected.json` is the physics
# anchor (independent-reference rule). A pin of a CONVERGED FIT cannot be asserted digit-for-digit
# off the architecture that produced it: crysta builds SLEEF AD-Jacobian kernels with compile-time
# aarch64/NEON dispatch, so on ARM64 the minimiser walks a marginally different path and stops at
# a marginally different point inside the same basin. Exact 10-significant-digit STRING equality
# and a 5e-09 relative bound were claims about x86_64 arithmetic wearing the costume of claims
# about the fit.
#
# WHAT THE BOUND IS, AND WHY A THIRD ARCHITECTURE WILL ALSO SATISFY IT. Two ARM measurements exist
# (both from the owner's M2, neither reproducible here), and a bound fitted to them would just
# re-pin to two machines instead of one. So the bound is set by MEANING and only checked against
# the measurements:
#
#   Ceiling — a fitted parameter means nothing below its own standard uncertainty. Crystallographic
#   values are quoted to one or two digits of their su, so a difference of 1% OF ONE SIGMA is far
#   under any reportable resolution: it cannot change a number anyone writes down, and it cannot be
#   told apart from where the minimiser happened to stop. That is the bound: 1e-2 x esd.
#
#   Floor — the mechanism says which parameters use most of that budget, and it is NOT the ones
#   this was first calibrated on. A gradient perturbation eps displaces a parameter by ~eps/H
#   (H = curvature), while sigma = 1/sqrt(H); so displacement IN SIGMA is ~eps*sigma, i.e. it grows
#   LINEARLY with sigma. Poorly-determined parameters wander furthest in sigma units, which is
#   exactly where a bound calibrated on well-determined ones gets surprised. Measured, both ARM
#   points agree on eps ~ 1e-5:
#       structure.atom_sites[Al1].adp_iso            sigma 0.0750   ->  2.6e-06 sigma
#       experiments[wish_2_9].peak.broad_gauss_sigma_1  sigma 19.38 ->  1.2e-04 sigma
#   The worst-determined parameter in this 102-parameter fit is sigma 41.48
#   (experiments[wish_2_9].background[14]), predicting ~4.2e-04 sigma — so the bound clears the
#   WHOLE parameter set by ~24x, not merely the two displacements that have been observed.
#
# It stays a strict pin: anything that moves a parameter by 1% of one sigma fails, and a real
# regression moves numbers by a sigma or more.
GOLDEN_PIN_ESD_FRACTION = 1e-2
# For quantities carrying no ESD: rwp and chi-square are STATIONARY at the minimum, so a parameter
# set displaced by ~4e-04 sigma moves them second-order — ~(d/sigma)^2 summed over 102 parameters,
# order 1e-05 relative — and 1e-4 is both comfortably clear of that and far tighter than any
# regression, which moves these percent-wise. ⛔ ESDs TAKE THIS BOUND TOO, NOT the `esd` one above:
# a caller comparing an ESD OMITS `esd`, which is what the docstring below says and what every call
# site now does. This comment used to instruct the opposite — route ESDs through the `esd` path at
# 1% — and the call sites followed the comment, so every ESD was held to a bound 100x looser than
# the documented one. The reason it is 1e-4: an ESD is a smooth function of the solution point, and
# the solution moves ~1e-4 sigma between architectures, so the ESD's own relative change is SECOND
# ORDER and far inside this bound — corroborated by the owner's M2 run, which failed on a VALUE
# while every ESD compared before it held here.
GOLDEN_PIN_REL = 1e-4
# Floor for a pin of exactly zero, below every quantity's meaningful resolution.
GOLDEN_PIN_ABS = 1e-12


def assert_matches_golden_pin(
    actual: float, expected: float, where: str, *, esd: float | None = None
) -> None:
    """Hold a live value against a committed golden REGRESSION PIN, architecture-robustly.

    Pass ``esd`` whenever the compared quantity is a fitted parameter value; omit it for ESDs and
    for derived scalars (rwp, chi-square), which fall back to the relative bound.
    """
    if esd is not None and abs(esd) > 0.0:
        bound = GOLDEN_PIN_ESD_FRACTION * abs(esd)
        scale = f'{GOLDEN_PIN_ESD_FRACTION:g} x esd {esd:.6g}'
    else:
        bound = GOLDEN_PIN_REL * abs(expected)
        scale = f'{GOLDEN_PIN_REL:g} x |pin|'
    bound = max(bound, GOLDEN_PIN_ABS)
    delta = abs(actual - expected)
    assert delta <= bound, (
        f'{where}: {actual:.17g} is {delta:.3g} from the pinned CLI value {expected:.17g}, '
        f'outside {bound:.3g} ({scale}). This is a regression pin, so a breach of a bound set by '
        f'the quantity itself means the RESULT moved - not that the arithmetic did.'
    )


def crysta_reference_prefix() -> Path:
    """Match the comparison CLI to the extension actually imported, including overrides."""
    root = Path(__file__).resolve().parents[1]
    artifact = Path(sys.modules['edi._edi'].__file__).resolve().parents[2]
    configurations = {
        (root / 'build/ci').resolve(): root / 'build/crysta-prefix',
        (root / 'build/ci-consumer').resolve(): root / 'build/crysta-consumer-prefix',
    }
    assert artifact in configurations, (
        'engine comparison requires a known edi artifact and its matching crysta prefix'
    )
    prefix = configurations[artifact]
    linked = (artifact / '.crysta-linked-sha').read_text().strip()
    assert re.fullmatch(r'[0-9a-f]{40}', linked), (
        'engine comparison requires a full linked crysta source identity'
    )
    assert (prefix / '.crysta-sha').read_text().strip() == linked, (
        'engine comparison must never run a different crysta than the linked edi artifact'
    )
    return prefix


def crysta_reference_source() -> Path:
    """Resolve the source belonging to the selected comparison prefix, fail closed."""
    root = Path(__file__).resolve().parents[1]
    prefix = crysta_reference_prefix()
    if prefix.name == 'crysta-consumer-prefix':
        source = os.environ.get('CRYSTA_CONSUMER_SRC')
        assert source, 'consumer comparisons require the source used to build the artifact'
        result = Path(source)
    else:
        result = root / 'build/crysta-src'
    current = subprocess.run(
        ['git', '-C', str(result), 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert current == (prefix / '.crysta-sha').read_text().strip(), (
        'engine comparison corpus and CLI must belong to the same linked crysta source'
    )
    return result


def corpus_case_dir(case_id: str) -> Path:
    """Resolve one crysta fitting-corpus case directory.

    Order: the cross-build override (`EDI_CRYSTA_CORPUS_ROOT`, set by the harness that also
    rebuilds the core against the same tree), then the recorded crysta-main checkout. A root
    with no corpus at all is a loud, named source transition skip; a present root missing the
    requested case fails (never a silent skip).
    """
    root_override = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
    root = Path(root_override) if root_override else crysta_reference_source() / 'tests/fitting'
    if not (root / 'manifest.yml').is_file():
        if root_override:
            msg = f'EDI_CRYSTA_CORPUS_ROOT={root_override} names no fitting corpus'
            raise AssertionError(msg)
        record = Path(__file__).resolve().parents[1] / 'build' / 'crysta-src' / 'CRYSTA_SOURCE_SHA'
        sha = record.read_text(encoding='utf-8').strip() if record.is_file() else 'unreadable-sha'
        pytest.skip(
            f'corpus not present at recorded crysta source {sha}',
            allow_module_level=True,
        )
    case = root / case_id
    if not case.is_dir():
        msg = f"fitting corpus at {root} has no case '{case_id}'"
        raise AssertionError(msg)
    return case


@pytest.fixture(scope='module')
def private_native_workflow():
    """Artifact reuse exists only in the private workflow set.

    Public omission is admitted only after all real public local-build boundaries
    and the token/artifact release contracts pass. Mixed runners refuse.
    """
    from tests.integration.py.test_e09_t75_native_workflow import (  # noqa: PLC0415 - defer cross-module test wiring
        CONSUMERS,
        jobs,
        public_build_boundary,
        public_profile,
    )
    from tests.system.py import (  # noqa: PLC0415 - avoid test-module import cycles
        test_e04_t12_public_release as release,
    )

    data = jobs()
    if public_profile(data):
        for name in ['native', *CONSUMERS]:
            public_build_boundary(data, name)
        release.test_public_ci_uses_hosted_runners_and_guards_private_tokens()
        release.test_public_artifacts_exclude_engine_object_code_and_runner_names()
        pytest.skip('Private native artifact reuse is absent; public local-build contracts passed')
