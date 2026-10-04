"""Hidden  gates for crysta-py being an existence-checked subset of edi-py."""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / 'tools/checks/python_surface_superset.py'
SEED_NAME = '__e09_t56_seed__'
SEED_MEMBER = '__e09_t56_member__'
DIRECTIONALITY = (
    'crysta-py ⊆ edi-py is a standing constraint on edi: a name enters crysta.__all__ only in a '
    "commit where edi carries it; a public crysta name edi lacks is red at crysta's PR consumer "
    "job today, and at edi's verify against the pinned crysta once edi's tools/ci/crysta.pin "
    'carries the declaration (development hub ) — crysta cannot add a public name without edi '
    'following'
)
EXISTENCE_LIMIT = (
    'This check proves EXISTENCE only: every declared name, and every declared member of a '
    'declared class, resolves in edi by attribute lookup - the rule that crysta may not get ahead '
    'of edi, and nothing more. It records and compares no signature, default, type, base chain or '
    'behaviour - surface existence, never semantics; whether refine computes the same thing on '
    'both is demonstrated by the substitution scripts (crysta tools/substitution/) for the paths '
    'they cover and proven by tests, never by this gate.'
)
SCHEMA = 4
SCHEMA_BOUND = (
    'Schema v4 is generated internal data, not hostile input: this check does not '
    'exhaustively reject malformed public-record shape.'
)
PINNED_PREFIX_RESIDUAL = (
    "While edi's pinned crysta predates the python-surface declaration, edi's own CI proves "
    "only the refusal branch; the real superset property is proven at crysta's PR gate through "
    'the consumer prefix. Move tools/ci/crysta.pin after crysta merges so this installed-prefix '
    'case activates the full superset assertion.'
)


def _kind_of(value: object) -> str:
    if isinstance(value, type):
        if issubclass(value, BaseException):
            return 'exception'
        if hasattr(value, '__members__'):
            return 'enum'
        return 'class'
    return 'function' if callable(value) else 'constant'


def _live_reference_public() -> dict[str, object]:
    """Build a schema-4 positive fixture from direct introspection, never from the checker."""
    selected = ('IoError', 'Parameter', 'Project', 'VerbosityEnum', 'stream_header')
    assert set(selected) <= set(edi.__all__), (
        'I4 independent reference: the selected names must remain in live edi.__all__'
    )
    public: dict[str, object] = {}
    for name in selected:
        value = getattr(edi, name)
        record: dict[str, object] = {'kind': _kind_of(value)}
        if isinstance(value, type):
            record['members'] = sorted(
                member for member in dir(value) if not member.startswith('_')
            )
        public[name] = record
    return public


def _manifest(public: object) -> dict[str, object]:
    return {
        'schema': SCHEMA,
        'directionality': DIRECTIONALITY,
        'public': public,
        'classification': {'module': {}, 'members': {}},
    }


def _checker_copy(tmp_path: Path) -> Path:
    assert CHECKER.is_file(), 'I4:  must provide the edi existence checker'
    checker = tmp_path / 'repo/tools/checks/python_surface_superset.py'
    checker.parent.mkdir(parents=True)
    shutil.copy2(CHECKER, checker)
    return checker


def _write_prefix_manifest(
    checker: Path,
    manifest: dict[str, object],
    *,
    consumer: bool = False,
) -> Path:
    prefix_name = 'crysta-consumer-prefix' if consumer else 'crysta-prefix'
    path = checker.parents[2] / 'build' / prefix_name / 'share/crysta/python-surface.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return path


def _run_checker(
    checker: Path,
    *,
    consumer: bool = False,
    pythonpath: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env['EDI_EXTENSION_DIR'] = str(Path(sys.modules['edi._edi'].__file__).parent)
    env.pop('CRYSTA_CONSUMER_SRC', None)
    env.pop('EDI_USE_CONSUMER_BUILD', None)
    if consumer:
        env['CRYSTA_CONSUMER_SRC'] = 'hidden-surface-control'
    if pythonpath is not None:
        inherited = env.get('PYTHONPATH')
        env['PYTHONPATH'] = (
            str(pythonpath) if not inherited else os.pathsep.join((str(pythonpath), inherited))
        )
    return subprocess.run(
        [sys.executable, str(checker)],
        cwd=checker.parents[2],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _output(completed: subprocess.CompletedProcess[str]) -> str:
    return completed.stdout + completed.stderr


def _assert_bounds(output: str) -> None:
    assert EXISTENCE_LIMIT in output, 'I12: the existence-only limit must remain byte-exact'
    assert SCHEMA_BOUND in output, 'I12: the schema-3 bound must remain byte-exact'


def _assert_green(completed: subprocess.CompletedProcess[str]) -> None:
    output = _output(completed)
    assert completed.returncode == 0, f'I7: zero existence findings must be green:\n{output}'
    _assert_bounds(output)


def _assert_red_with(completed: subprocess.CompletedProcess[str], *tokens: str) -> None:
    output = _output(completed)
    assert completed.returncode != 0, f'I8: an existence/refusal finding must be red:\n{output}'
    folded = output.casefold()
    for token in tokens:
        assert token.casefold() in folded, (
            f'I8: the red diagnostic must include {token!r}:\n{output}'
        )
    _assert_bounds(output)


def _assert_installed_prefix_refuses_with_remedy(
    completed: subprocess.CompletedProcess[str],
) -> None:
    output = _output(completed)
    assert completed.returncode != 0, (
        'I9: a declaration-less installed prefix must refuse, never silently pass. '
        f'{PINNED_PREFIX_RESIDUAL}\n{output}'
    )
    folded = output.casefold()
    for token in ('manifest', 'absent', 'core-build', 'refused', 'never skipped'):
        assert token in folded, (
            f'I9: the refusal must name {token!r} and its build remedy. '
            f'{PINNED_PREFIX_RESIDUAL}\n{output}'
        )
    _assert_bounds(output)


def test_e09_t56_installed_manifest_matches_live_built_edi_module() -> None:
    assert CHECKER.is_file(), 'I4:  must provide the edi existence checker'
    consumer_source = os.environ.get('CRYSTA_CONSUMER_SRC')
    consumer = bool(consumer_source) or bool(os.environ.get('EDI_USE_CONSUMER_BUILD'))
    assert not consumer or consumer_source, (
        'I4: a selected consumer prefix needs its live Crysta source to prove provenance'
    )
    source = Path(consumer_source).resolve() if consumer_source else ROOT / 'build/crysta-src'
    assert (source / 'CMakeLists.txt').is_file(), (
        'I4: the selected Crysta source must be a buildable checkout'
    )
    prefix = ROOT / 'build' / ('crysta-consumer-prefix' if consumer else 'crysta-prefix')
    linked = ROOT / 'build' / ('ci-consumer' if consumer else 'ci') / '.crysta-linked-sha'
    recorded_sha = linked.read_text(encoding='utf-8').strip()
    assert re.fullmatch(r'[0-9a-f]{40}', recorded_sha), (
        ': the Crysta source linked into Edi must be one full commit identity'
    )
    assert (prefix / '.crysta-sha').read_text(encoding='utf-8').strip() == recorded_sha, (
        'I4: the selected installed prefix must name the Crysta source linked into Edi'
    )
    if not consumer:
        assert (source / 'CRYSTA_SOURCE_SHA').read_text(
            encoding='utf-8'
        ).strip() == recorded_sha, (
            'I4: the pinned source record must match the Edi-linked Crysta source'
        )
    source_head = subprocess.run(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert source_head == recorded_sha, 'I4: the selected source tree must match the linked SHA'
    completed = _run_checker(CHECKER, consumer=consumer)
    if (prefix / 'share/crysta/python-surface.json').is_file():
        _assert_green(completed)
    else:
        _assert_installed_prefix_refuses_with_remedy(completed)


def test_e09_t56_live_edi_surface_accepts_existing_names_and_members(tmp_path: Path) -> None:
    checker = _checker_copy(tmp_path)
    _write_prefix_manifest(checker, _manifest(_live_reference_public()))
    _assert_green(_run_checker(checker))


@pytest.mark.parametrize(
    ('field', 'value', 'expected'),
    [
        ('schema', 3, 'schema'),
        ('directionality', '__e09_t56_wrong_direction__', 'direction'),
    ],
)
def test_e09_t56_schema_and_direction_headers_are_enforced(
    field: str,
    value: object,
    expected: str,
    tmp_path: Path,
) -> None:
    checker = _checker_copy(tmp_path)
    manifest = _manifest(_live_reference_public())
    manifest[field] = value
    _write_prefix_manifest(checker, manifest)
    _assert_red_with(_run_checker(checker), expected)


def test_e09_t56_declared_member_absent_from_live_edi_is_red(tmp_path: Path) -> None:
    checker = _checker_copy(tmp_path)
    public = _live_reference_public()
    project = public['Project']
    assert isinstance(project, dict), 'I4: the independent Project record must be a mapping'
    members = project['members']
    assert isinstance(members, list), 'I4: schema 4 records members as a list of names'
    assert not hasattr(edi.Project, SEED_MEMBER), 'I8: the seeded member is independently absent'
    members.append(SEED_MEMBER)
    _write_prefix_manifest(checker, _manifest(public))
    _assert_red_with(_run_checker(checker), f'Project.{SEED_MEMBER}', 'absent')


def test_e09_t56_declared_enum_member_absent_from_live_edi_is_red(tmp_path: Path) -> None:
    checker = _checker_copy(tmp_path)
    public = _live_reference_public()
    verbosity = public['VerbosityEnum']
    assert isinstance(verbosity, dict), 'I4: the independent enum record must be a mapping'
    members = verbosity['members']
    assert isinstance(members, list), 'I4: schema 4 records enum members as names'
    assert not hasattr(edi.VerbosityEnum, SEED_MEMBER), 'I8: the seeded enum member is absent'
    members.append(SEED_MEMBER)
    _write_prefix_manifest(checker, _manifest(public))
    _assert_red_with(_run_checker(checker), f'VerbosityEnum.{SEED_MEMBER}', 'absent')


def test_e09_t56_empty_set_is_green_but_a_missing_name_is_red(tmp_path: Path) -> None:
    checker = _checker_copy(tmp_path)
    _write_prefix_manifest(checker, _manifest({}))
    _assert_green(_run_checker(checker))

    assert not hasattr(edi, SEED_NAME), 'I8: the seeded public name is independently absent'
    _write_prefix_manifest(checker, _manifest({SEED_NAME: {'kind': 'function'}}))
    _assert_red_with(_run_checker(checker), SEED_NAME, 'absent', 'edi')


def test_e09_t56_extra_edi_members_do_not_weaken_declared_existence(tmp_path: Path) -> None:
    checker = _checker_copy(tmp_path)
    declared = ['load']
    assert hasattr(edi.Project, declared[0]), 'I4: the declared Project member must exist'
    assert len([name for name in dir(edi.Project) if not name.startswith('_')]) > len(declared), (
        'I4: the non-trivial superset control requires additional edi members'
    )
    public = {'Project': {'kind': 'class', 'members': declared}}
    _write_prefix_manifest(checker, _manifest(public))
    _assert_green(_run_checker(checker))


def test_e09_t56_non_mapping_public_section_is_refused(tmp_path: Path) -> None:
    checker = _checker_copy(tmp_path)
    _write_prefix_manifest(checker, _manifest(['Project']))
    _assert_red_with(_run_checker(checker), 'public', 'mapping')


def test_e09_t56_consumer_prefix_wins_only_when_requested(tmp_path: Path) -> None:
    checker = _checker_copy(tmp_path)
    compatible = _manifest(_live_reference_public())
    incompatible = copy.deepcopy(compatible)
    public = incompatible['public']
    assert isinstance(public, dict), 'I9: the synthetic public section must be a mapping'
    public[SEED_NAME] = {'kind': 'function'}
    _write_prefix_manifest(checker, incompatible)
    _write_prefix_manifest(checker, compatible, consumer=True)

    consumer = _run_checker(checker, consumer=True)
    _assert_green(consumer)
    assert SEED_NAME not in _output(consumer), (
        'I9: the requested consumer prefix must ignore the incompatible pinned prefix'
    )
    _assert_red_with(_run_checker(checker), SEED_NAME, 'absent')


def test_e09_t56_absent_prefix_refuses_with_build_remedy(tmp_path: Path) -> None:
    checker = _checker_copy(tmp_path)
    _assert_red_with(
        _run_checker(checker),
        'manifest',
        'absent',
        'core-build',
        'refused',
        'never skipped',
    )


def test_e09_t56_edi_checker_never_imports_crysta_py(tmp_path: Path) -> None:
    checker = _checker_copy(tmp_path)
    _write_prefix_manifest(checker, _manifest(_live_reference_public()))
    poison = tmp_path / 'poison'
    poison.mkdir()
    (poison / 'crysta.py').write_text(
        "raise AssertionError('I14: edi superset checker imported crysta-py')\n",
        encoding='utf-8',
    )
    _assert_green(_run_checker(checker, pythonpath=poison))
