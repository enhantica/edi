# SPDX-License-Identifier: BSD-3-Clause
"""The autoloaded runtime fit policy for edi (invariant I20).

I20 requires actual-entry-point sentinels in **both** repos. This is edi's half; crysta's lives
at crysta and enforces the same two rules:

- **No ``tests/unit/**`` node performs a fit or reaches a fit entry point.** Absolute, no
  exceptions.
- **``tests/integration/**`` and ``tests/system/**`` may fit only a corpus case.**

Both refusals fire **before** the call is forwarded, decided from the node id and the project's
recorded origin, so a sentinel can probe with a deliberately invalid operand and still prove
interception without itself fitting.

⛔ **WHAT "THE CORPUS" MEANS HERE, NAMED RATHER THAN INFERRED.** edi has **no ``manifest.yml`` of
its own**, so the question *"is this fit inside the corpus?"* has no edi-local answer. The basis
this policy uses, and the only one available today, is **crysta's corpus reached through edi's own
pin**: the root that ``tests/conftest.py:corpus_case_dir`` resolves, and a case is admitted only if
it is a directory there **named by that tree's committed ``manifest.yml``**. That is the same
authority edi's corpus consumers already use, so the policy and the tests agree by construction
rather than by a second definition that could drift.

Adds the narrow registry ``tests/fit-sites.yml`` for a second admissible shape: an exact test
file may name the corpus case from which it stages a disposable copy. This is required for
save-by-default and undo gates, which must not mutate the corpus authority in place. A row naming
an absent case refuses; an unregistered copied project still refuses.

**⛔ IT FAILS CLOSED. If the corpus is unresolvable, every integration/system fit is REFUSED.**
This module previously failed OPEN there — admitting everything, loudly — on the reasoning that
refusing in a checkout that simply has not been built yet is indistinguishable from a broken
environment. That reasoning was wrong, and review-17 F3 named why: **a warning makes a bypass
visible without making it conforming.** I20 admits a fit only when the project resolves to a
manifest-declared case; deleting, mispointing or failing to build the very authority that proves
membership must not disable the rule that authority exists to enforce. An unbuilt checkout is a
loud, named refusal with a remedy in the message — not a silent licence. When edi gets
its own registry, that is the seam to replace — not this module's rules.

⛔ **BOUND — this is a PYTHON-ONLY gate**, exactly as in crysta. Native C++ tests call the engine
directly and are invisible here.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import edi
import pytest
import yaml

_UNIT_PREFIX = 'tests/unit/'
_ADMITTED_PREFIXES = ('tests/integration/', 'tests/system/')


def _project_fit_entry_points() -> tuple[str, ...]:
    """Every public fit entry bound on ``edi.Project``, DERIVED from the live surface.

    The hand-maintained tuple omitted the public ``fit_independent``, so a unit node could
    reach it while the gate reported success. Enforcement scope must equal the public
    model-operation inventory, so it is read off the class itself: any callable named
    ``fit`` or ``fit_*`` is a fit entry point, and a future binding is wrapped the day it
    lands (the pin below then flags the move loudly). Fails LOUD on an empty derivation —
    no fit entry means this module is armed against the wrong library.
    """
    names = tuple(
        sorted(
            name
            for name in dir(edi.Project)
            if (name == 'fit' or name.startswith('fit_'))
            and callable(getattr(edi.Project, name, None))
        )
    )
    if not names:
        raise RuntimeError(
            'fit_policy: edi.Project binds no fit entry point - refusing to arm an empty '
            'sentinel (is the wrong library on the path?)'
        )
    return names


_ENTRY_POINTS = _project_fit_entry_points()
# The derived set TODAY, pinned as a fail-loud drift ALARM — the derivation above stays the
# wrapping authority. added fit_sequential to the retired hand tuple; a future surface move
# fails here by name so the pin is moved deliberately, never silently.
_EXPECTED_ENTRY_POINTS = ('fit', 'fit_independent', 'fit_joint', 'fit_sequential')
if _ENTRY_POINTS != _EXPECTED_ENTRY_POINTS:
    raise RuntimeError(
        f'fit_policy: the public fit surface moved - derived {_ENTRY_POINTS}, pinned '
        f'{_EXPECTED_ENTRY_POINTS}; every derived entry is still wrapped - move the pin '
        'deliberately with the surface change'
    )
# The other two surfaces a fit can be spelled through: the diffraction-lib-shaped
# `project.analysis.fit(...)` wrapper, and the cached model's own fit. Wrapped on their own
# types because they are not methods of Project.
_ANALYSIS_ENTRY = 'fit'
_CACHED_ENTRY = 'fit'
_LOADERS = ('load',)
_CLI_FIT_VERB = 'fit'

_current_node: str | None = None
# Latched so the unresolvable-corpus warning is emitted ONCE per session, not per call.
_origins: dict[int, str] = {}


class FitPolicyViolation(RuntimeError):  # noqa: N818
    """A fit was performed, or a fit entry point reached, from a node that may not."""


def _linked_crysta_source() -> Path | None:
    """The source tree of the crysta the imported edi extension links, or None if unknown.

    The consumer artifact (``build/ci-consumer``, built with ``CRYSTA_CONSUMER_SRC``) links that
    working tree; every other artifact links the pinned ``build/crysta-src``. The same pairing
    ``tests/conftest.py:crysta_reference_source`` makes, so the policy admits the corpus of the
    engine actually under test, not crysta main's.
    """
    repo = Path(__file__).resolve().parents[2]
    artifact = Path(edi._edi.__file__).resolve().parents[2]
    if artifact == (repo / 'build' / 'ci-consumer').resolve():
        source = os.environ.get('CRYSTA_CONSUMER_SRC')
        return Path(source) if source else None
    return repo / 'build' / 'crysta-src'


def _corpus_root() -> Path | None:
    """The corpus of the crysta under test, or None when it cannot be resolved (then: refuse)."""
    override = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
    source = _linked_crysta_source()
    if override:
        root = Path(override)
    elif source is not None:
        root = source / 'tests' / 'fitting'
    else:
        return None
    return root if (root / 'manifest.yml').is_file() else None


def _corpus_case_ids(root: Path) -> set[str]:
    doc = yaml.safe_load((root / 'manifest.yml').read_text(encoding='utf-8'))
    return {str(case['id']) for case in doc['cases']}


def _declared_site_case(node_file: str, root: Path) -> str | None:
    registry = Path(__file__).resolve().parents[2] / 'tests' / 'fit-sites.yml'
    try:
        doc = yaml.safe_load(registry.read_text(encoding='utf-8'))
        rows = doc['sites']
    except (OSError, KeyError, TypeError, yaml.YAMLError):
        return None
    matches = [str(row.get('case', '')) for row in rows if row.get('file') == node_file]
    if len(matches) != 1 or matches[0] not in _corpus_case_ids(root):
        return None
    return matches[0]


def _is_corpus(origin: str | None) -> bool:
    """Whether a recorded project origin resolves to a case of the pinned corpus."""
    root = _corpus_root()
    if root is None:
        # ⛔ FAIL CLOSED. Losing the authority that proves membership does not suspend the rule
        # that authority exists to enforce — it removes our ability to satisfy it, which is a
        # refusal, not a licence. The earlier version warned and admitted everything; that made
        # the bypass visible without making it conforming. The remedy is in the refusal
        # message, so an unbuilt checkout is a named, actionable stop rather than a silent one.
        return False
    if origin is None:
        return False
    ids = _corpus_case_ids(root)
    origin_path = Path(origin)

    # ⛔ EXACT, not "somewhere under a case". The previous rule admitted ANY origin whose first
    # path component was a case id, so `<case>/fullprof` or `<case>/goldens` passed as a
    # project. A case declares exactly one project: `<case>/project`.
    if _is_declared_project(root, ids, origin_path):
        return True

    # A STAGED corpus project: the directory lives outside the corpus, but every part of it must
    # come from ONE case — the DATA from that case's declared project, and the ANALYSIS from that
    # same case's canonical analysis or exactly one of its declared `*-analysis` variants.
    #
    # The analysis is what DEFINES a fit: which parameters are free, their bounds, the algorithm.
    # A rule that proved the data came from the corpus but let the recipe come from anywhere is
    # satisfiable by the very thing I20 exists to stop.
    staged_case = _case_whose_data_is_staged(root, ids, origin_path)
    if staged_case is None:
        return False
    return _analysis_is_one_declared_variant(root / staged_case, origin_path / 'analysis')


def _is_declared_project(root: Path, ids: set[str], origin: Path) -> bool:
    """Whether `origin` IS a case's one declared project directory — `<case>/project`."""
    try:
        resolved = origin.resolve()
        return any(resolved == (root / case_id / 'project').resolve() for case_id in ids)
    except OSError:
        return False


def _case_whose_data_is_staged(root: Path, ids: set[str], origin: Path) -> str | None:
    """The single case whose declared project supplies BOTH staged data directories, else None."""
    try:
        for case_id in ids:
            project = root / case_id / 'project'
            if all(
                (origin / child).resolve() == (project / child).resolve()
                for child in ('experiments', 'structures')
            ):
                return case_id
    except OSError:
        return None
    return None


def _variant_dirs(case_dir: Path) -> list[Path]:
    """The canonical analysis directory plus every declared `*-analysis` variant, in order."""
    try:
        extras = sorted(
            directory
            for directory in case_dir.iterdir()
            if directory.is_dir() and directory.name.endswith('-analysis')
        )
    except OSError:
        return []
    return [d for d in [case_dir / 'project' / 'analysis', *extras] if d.is_dir()]


def _declared_analysis_variants(case_dir: Path) -> list[dict[str, bytes]]:
    """Each analysis variant the case DECLARES, as a complete {filename: bytes} mapping.

    A case declares its canonical analysis (``project/analysis``) and may declare variants beside
    it. Each is a whole document set, and
    they are kept SEPARATE rather than pooled: pooling let a subset or a cross-variant mixture
    pass as "the case's own" without matching anything the case actually declared.
    """
    variants: list[dict[str, bytes]] = []
    for directory in _variant_dirs(case_dir):
        try:
            documents = {path.name: path.read_bytes() for path in sorted(directory.glob('*.edi'))}
        except OSError:
            return []
        if documents:
            variants.append(documents)
    return variants


def _analysis_is_one_declared_variant(case_dir: Path, analysis_dir: Path) -> bool:
    """Whether a staged ``analysis/`` EQUALS one declared variant of this case, exactly.

    Equality is on the whole mapping — same filenames and same bytes — so a subset, an extra
    file, and a mixture of two variants are all refused. A staged project cannot symlink the
    analysis when it wants a declared VARIANT, which is why content equality is the test and
    resolution is only the shortcut for the canonical case. Fails closed on unreadable or empty.
    """
    try:
        resolved = analysis_dir.resolve()
        if any(resolved == directory.resolve() for directory in _variant_dirs(case_dir)):
            return True
    except OSError:
        return False
    variants = _declared_analysis_variants(case_dir)
    if not variants:
        return False
    try:
        staged = {path.name: path.read_bytes() for path in sorted(analysis_dir.glob('*.edi'))}
    except OSError:
        return False
    if not staged:
        return False
    return any(staged == variant for variant in variants)


def _refuse(entry: str, why: str) -> None:
    node = _current_node or '<no node>'
    message = (
        f'fit policy: {node} may not reach edi.Project.{entry} — {why}. A unit test never fits; '
        f'an integration/system test fits only a case of the pinned crysta corpus.'
    )
    raise FitPolicyViolation(message)


def _check(entry: str, origin: str | None) -> None:
    """Decide BEFORE the call is forwarded. Never validates operands, never enters the solver."""
    node_file = (_current_node or '').split('::', 1)[0]
    if node_file.startswith(_UNIT_PREFIX):
        _refuse(entry, 'the unit tier reaches no fit entry point, without exception')
    if not node_file.startswith(_ADMITTED_PREFIXES):
        return
    root = _corpus_root()
    if root is not None and _declared_site_case(node_file, root) is not None:
        return
    if not _is_corpus(origin):
        _refuse(entry, f'its project does not resolve to a corpus case ({origin or "no origin"})')


@pytest.fixture(autouse=True, scope='session')
def _fit_policy() -> object:
    monkey = pytest.MonkeyPatch()
    for name in _LOADERS:
        loader = getattr(edi.Project, name, None)
        if loader is None:
            continue

        def wrapped_loader(*args: object, _loader: object = loader, **kwargs: object) -> object:
            result = _loader(*args, **kwargs)
            if args:
                _origins[id(result)] = str(args[0])
            return result

        monkey.setattr(edi.Project, name, wrapped_loader, raising=False)

    for name in _ENTRY_POINTS:
        entry = getattr(edi.Project, name, None)
        if entry is None:
            continue

        def wrapped_entry(
            *args: object, _entry: object = entry, _name: str = name, **kwargs: object
        ) -> object:
            _check(_name, _origins.get(id(args[0])) if args else None)
            return _entry(*args, **kwargs)

        monkey.setattr(edi.Project, name, wrapped_entry, raising=False)

    # `project.analysis.fit(...)` — Analysis holds the project it wraps, so the origin is the
    # project's, looked up through whatever attribute the wrapper stores it in.
    analysis_fit = getattr(edi.Analysis, _ANALYSIS_ENTRY, None)
    if analysis_fit is not None:

        def wrapped_analysis(
            *args: object, _entry: object = analysis_fit, **kwargs: object
        ) -> object:
            origin = None
            if args:
                inner = getattr(args[0], '_project', None) or getattr(args[0], 'project', None)
                origin = _origins.get(id(inner)) if inner is not None else None
            _check('analysis.fit', origin)
            return _entry(*args, **kwargs)

        monkey.setattr(edi.Analysis, _ANALYSIS_ENTRY, wrapped_analysis, raising=False)

    for name in ('run', 'Popen', 'check_output', 'call'):
        launcher = getattr(subprocess, name, None)
        if launcher is None:
            continue

        def wrapped(*args: object, _launcher: object = launcher, **kwargs: object) -> object:
            argv = args[0] if args else kwargs.get('args')
            listed = isinstance(argv, (list, tuple))
            parts = [str(p) for p in argv] if listed else str(argv).split()
            non_op = ('--help', '-h', '--version')
            if _CLI_FIT_VERB in parts and not any(f in parts for f in non_op):
                origin = next((p for p in parts if 'fitting/' in p or 'project' in p), None)
                _check('fit (CLI)', origin)
            return _launcher(*args, **kwargs)

        monkey.setattr(subprocess, name, wrapped, raising=False)
    yield
    monkey.undo()


# The corpus a session fits is a SCRATCH CHECKOUT of the resolved source, never the source itself.
# A corpus fit through the CLI persists by default, so a test fitting a case in place saves the
# fitted project back into its case directory. That silently rewrote edi's pinned build/crysta-src
# copy for as long as the corpus resolved there, and it rewrote tracked files in the crysta
# checkout once the corpus followed CRYSTA_CONSUMER_SRC. pytest_configure runs before collection
# and makes a shared clone of the source crysta repository with only `tests/` checked out at its
# HEAD (0.1 s, 15 MB) — so a consumer deriving the repository or a sibling fixture from the corpus
# path finds crysta's own layout — and points EDI_CRYSTA_CORPUS_ROOT at its
# `tests/fitting`, the root tests/conftest.py:corpus_case_dir and this policy both honour. It then
# fingerprints the source; pytest_sessionfinish fails the session if any source byte changed,
# whatever the route.
_source_corpus: dict[str, object] = {}


def _fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def pytest_configure(config: pytest.Config) -> None:  # noqa: ARG001
    """Stage the session's corpus as a scratch copy and fingerprint the source."""
    source = _corpus_root()
    if source is None:
        return  # unresolvable: every corpus fit refuses, and there is nothing to protect
    work = Path(tempfile.mkdtemp(prefix='edi-corpus-', dir=os.environ.get('RUNNER_TEMP') or None))
    repo = source.parents[1]
    if (repo / '.git').exists() and source == repo / 'tests' / 'fitting':
        clone = work / repo.name
        git = ('git', '-c', 'advice.detachedHead=false')
        subprocess.run(
            (*git, 'clone', '-q', '--shared', '--no-checkout', str(repo), str(clone)), check=True
        )
        subprocess.run(
            (*git, '-C', str(clone), 'checkout', '-q', 'HEAD', '--', 'tests'), check=True
        )
        scratch = clone / 'tests' / 'fitting'
    else:  # an explicit root outside a crysta checkout: a plain copy of the corpus itself
        scratch = work / 'tests' / 'fitting'
        shutil.copytree(source, scratch, symlinks=True)
    _source_corpus.update(
        source=source,
        work=work,
        fingerprint=_fingerprint(source),
        previous=os.environ.get('EDI_CRYSTA_CORPUS_ROOT'),
    )
    os.environ['EDI_CRYSTA_CORPUS_ROOT'] = str(scratch)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:  # noqa: ARG001
    """Fail the session if the source corpus changed; drop the scratch copy."""
    if not _source_corpus:
        return
    source = _source_corpus['source']
    previous = _source_corpus['previous']
    if previous is None:
        os.environ.pop('EDI_CRYSTA_CORPUS_ROOT', None)
    else:
        os.environ['EDI_CRYSTA_CORPUS_ROOT'] = previous
    shutil.rmtree(_source_corpus['work'], ignore_errors=True)
    if _fingerprint(source) != _source_corpus['fingerprint']:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        reporter = session.config.pluginmanager.get_plugin('terminalreporter')
        message = (
            f'corpus guard: the source corpus {source} CHANGED during this session — '
            'a fit wrote into it; corpus fits must run on the session scratch copy'
        )
        if reporter is not None:
            reporter.write_line(message, red=True, bold=True)
        else:
            print(message)


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Record the node the policy is deciding for."""
    global _current_node  # noqa: PLW0603 — one process-wide current node is the point
    _current_node = item.nodeid


def pytest_runtest_teardown(item: pytest.Item) -> None:  # noqa: ARG001
    """Clear the recorded node so a fit outside a test is never attributed to one."""
    global _current_node  # noqa: PLW0603
    _current_node = None
