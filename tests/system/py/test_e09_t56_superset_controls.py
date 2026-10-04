"""visible controls for the crysta-py -> edi-py existence gate.

The gate proves that every name crysta declares public, and every declared member of a declared
class, EXISTS in edi — and nothing more (owner ruling 2026-08-29, development hub
``knowledge/decision-records.md`` "DELETE the signature comparison; the gate checks existence, and
real scripts prove behaviour"). The checker is driven as a library over synthetic manifests, and
as a subprocess for the prefix-resolution seam. Every fixture value is derived by direct
introspection (``dir()``, ``hasattr``) that never calls the checker. Each assertion names the plan
requirement it proves (invariant ``I<n>`` or seam row ``S<n>``). The hidden gate is the tests
lane's.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / 'tools' / 'checks' / 'python_surface_superset.py'
SEED = '__e09_t56_seed__'


@pytest.fixture(scope='module')
def checker():
    spec = importlib.util.spec_from_file_location('python_surface_superset', CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest(checker, public):
    return {'schema': 4, 'directionality': checker.DIRECTIONALITY, 'public': public}


def _members(cls):
    return sorted(name for name in dir(cls) if not name.startswith('_'))


@pytest.fixture
def existing_public():
    """A synthetic public section every row of which the built edi package carries."""
    return {
        'Parameter': {'kind': 'class', 'members': ['free', 'uncertainty', 'value']},
        'IoError': {'kind': 'exception', 'members': _members(edi.IoError)},
        'VerbosityEnum': {'kind': 'enum', 'members': ['COMPACT', 'OFF']},
        'Project': {'kind': 'class', 'members': ['load', 'fit', 'save_as', 'structure']},
    }


def test_every_fixture_value_is_derived_without_the_checker():
    assert {'free', 'uncertainty', 'value'} <= set(_members(edi.Parameter)), (
        'S8: the Parameter members are read from dir(), not from the checker'
    )
    assert issubclass(edi.IoError, BaseException), 'S5: IoError is an exception class'
    assert {'COMPACT', 'OFF'} <= set(edi.VerbosityEnum.__members__), (
        'S6: the VerbosityEnum members are read from __members__'
    )
    for member in ('load', 'fit', 'save_as', 'structure'):
        assert hasattr(edi.Project, member), f'S8: Project.{member} exists, read by hasattr'


# --- (1) the empty declared set is green, and the output states the limits --------------------
def test_empty_public_set_is_green_and_bounded(checker, capsys):
    assert checker.check_manifest(_manifest(checker, {}), edi) == [], (
        'I7: an empty declared set has zero findings'
    )
    assert checker.report([], _manifest(checker, {})) == 0, 'I7: zero findings exit 0'
    out = capsys.readouterr().out
    assert 'superset OK' in out, 'I7: the OK line is printed at zero findings'
    assert 'proves EXISTENCE only' in out, 'I12: the gate says it proves existence only'
    assert 'no signature, default, type, base chain or behaviour' in out, (
        'I12: the gate names what it does not compare'
    )
    assert 'demonstrated by the substitution scripts' in out, (
        'I12: the gate says where behaviour is demonstrated instead'
    )
    assert 'does not exhaustively reject malformed public-record shape' in out, (
        'I12: the gate states its schema bound'
    )


def test_existing_names_and_members_are_green(checker, existing_public):
    assert checker.check_manifest(_manifest(checker, existing_public), edi) == [], (
        'I4/I5: every declared name and member that exists in edi has zero findings'
    )


def test_checker_carries_no_signature_comparison(checker):
    source = CHECKER.read_text(encoding='utf-8')
    for retired in (
        'parse_nb_signature',
        '__nb_signature__',
        'import inspect',
        'identity_header',
        'RECORDED_FIELDS',
        '_shape(',
    ):
        assert retired not in source, (
            f'the owner ruling deleted the signature comparison: {retired} must not survive'
        )
    assert not hasattr(checker, 'compare_signatures'), 'no signature comparator exists'
    assert 'hasattr' in source, 'existence is attribute lookup, nothing more'


# --- I6: the emitted, byte-enforced direction carries the current bound ------------------------
def test_directionality_carries_the_current_bound(checker, capsys):
    sentence = checker.DIRECTIONALITY
    assert "red at crysta's PR consumer job today" in sentence, (
        'I6: the sentence names where the direction is enforced today'
    )
    assert 'once edi' in sentence, 'I6: the sentence says edi verify enforces it only later'
    assert 'tools/ci/crysta.pin carries the declaration' in sentence, (
        'I6: the sentence names the condition under which edi verify enforces it'
    )
    assert 'crysta cannot add a public name without edi following' in sentence, (
        'I6: the bound must state the concrete follow-up obligation for added public names'
    )
    assert 'compatibly' not in sentence, (
        'I6: the direction no longer promises compatibility - only that edi carries the name'
    )
    checker.report(['x: absent in edi'], None)
    assert sentence in capsys.readouterr().out, 'I6: every red emits the bounded sentence'


# --- (2) a name or member edi lacks is red, naming it -----------------------------------------
def test_missing_name_is_red(checker, existing_public, capsys):
    public = copy.deepcopy(existing_public)
    public[SEED] = {'kind': 'function'}
    findings = checker.check_manifest(_manifest(checker, public), edi)
    assert findings == [f'{SEED}: absent in edi'], (
        'I6/I8: a declared name edi lacks is the one finding, naming it as absent'
    )
    assert checker.report(findings, None) == 1, 'I7: a finding exits 1'
    out = capsys.readouterr().out
    assert 'RED' in out, 'I7: the red line is printed on a finding'
    assert 'crysta cannot add a public name without edi following' in out, (
        'I6: the red output states the direction'
    )


def test_missing_member_is_red(checker, existing_public):
    public = copy.deepcopy(existing_public)
    public['Parameter']['members'].append(SEED)
    assert not hasattr(edi.Parameter, SEED), 'S8: the seed member is absent, read by hasattr'
    findings = checker.check_manifest(_manifest(checker, public), edi)
    assert findings == [f'Parameter.{SEED}: absent in edi'], (
        'I4/I8: a declared member edi lacks is red, naming its full path'
    )


def test_missing_enum_member_is_red(checker, existing_public):
    public = copy.deepcopy(existing_public)
    public['VerbosityEnum']['members'].append(SEED)
    findings = checker.check_manifest(_manifest(checker, public), edi)
    assert findings == [f'VerbosityEnum.{SEED}: absent in edi'], (
        'S6/I4: an enum member edi lacks is red like any member, by attribute lookup'
    )


def test_existence_is_attribute_lookup_and_nothing_more(checker):
    class Plain:
        value = 1

        @staticmethod
        def method(a, b=2):
            return (a, b)

    class Other:
        value = 'text'

        @staticmethod
        def method():
            return None

    live = type('FakeModule', (), {'Plain': Other})
    public = {'Plain': {'kind': 'class', 'members': ['method', 'value']}}
    assert checker.check_manifest(_manifest(checker, public), live) == [], (
        'I4: a member that exists is green whatever its signature, kind or value - the gate '
        'compares nothing beyond existence, by design'
    )
    public = {'Plain': {'kind': 'function', 'members': ['method', 'value']}}
    assert checker.check_manifest(_manifest(checker, public), live) == [], (
        'I4: the declared kind is not compared either; only names resolve'
    )
    live = type('FakeModule', (), {'Plain': Plain})
    public = {'Plain': {'kind': 'class', 'members': ['method', 'missing', 'value']}}
    findings = checker.check_manifest(_manifest(checker, public), live)
    assert findings == ['Plain.missing: absent in edi'], (
        'I8: the one member that does not resolve is the one finding'
    )


def test_sparse_and_malformed_records_are_tolerated_as_names_only(checker):
    public = {'Project': {'kind': 'class'}, 'IoError': 'not-a-record'}
    assert checker.check_manifest(_manifest(checker, public), edi) == [], (
        'S8: a record without members, or not a mapping, still proves its name exists '
        '(schema bound: generated internal data, not hostile input)'
    )
    manifest = _manifest(checker, ['Project'])
    assert 'public: section is not a mapping of declared names' in checker.check_manifest(
        manifest, edi
    ), 'S8: a public section that is not a mapping is refused, not iterated'


# --- header: schema and direction are enforced ------------------------------------------------
def test_header_is_enforced(checker):
    manifest = _manifest(checker, {})
    manifest['schema'] = 3
    manifest['directionality'] = 'the other way round'
    findings = checker.check_manifest(manifest, edi)
    assert any('schema' in f for f in findings), (
        'S8: the pre-necessity schema 3 is red - a declaration without verdicts is stale'
    )
    assert any('direction' in f for f in findings), (
        'I6: a directionality text other than I6 is red'
    )


# --- (7) prefix resolution mirrors core-build.sh; absent is a refusal naming the remedy ---------
def _run(root, env_extra):
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {'CRYSTA_CONSUMER_SRC', 'EDI_USE_CONSUMER_BUILD'}
    }
    env['EDI_EXTENSION_DIR'] = str(Path(sys.modules['edi._edi'].__file__).parent)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(CHECKER), '--root', str(root)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _install(root, prefix_name, checker):
    target = root / 'build' / prefix_name / 'share' / 'crysta' / 'python-surface.json'
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(_manifest(checker, {})), encoding='utf-8')


def test_consumer_prefix_wins_only_when_requested(checker, tmp_path):
    _install(tmp_path, 'crysta-consumer-prefix', checker)

    bare_directory = _run(tmp_path, {'CRYSTA_CONSUMER_SRC': str(tmp_path)})
    assert bare_directory.returncode == 1, (
        'S10/I9: a merely existing CRYSTA_CONSUMER_SRC directory is not a request for the '
        'consumer prefix'
    )
    assert 'crysta-prefix' in bare_directory.stdout, (
        'S10/I9: the bare-directory refusal must name the required pinned prefix'
    )

    (tmp_path / 'CMakeLists.txt').write_text('project(crysta)\n', encoding='utf-8')
    requested = (
        {'EDI_USE_CONSUMER_BUILD': '1'},
        {'CRYSTA_CONSUMER_SRC': 'hidden-surface-control'},
        {'CRYSTA_CONSUMER_SRC': str(tmp_path)},
    )
    for selector in requested:
        assert _run(tmp_path, selector).returncode == 0, (
            'S10/I9: the explicit selector, exact hidden-control literal, and source-tree '
            f'CMakeLists.txt witness must each request the consumer prefix; selector={selector}'
        )

    unrequested = _run(tmp_path, {})
    assert unrequested.returncode == 1, 'S10/I9: without it the pinned prefix is required'
    assert 'crysta-prefix' in unrequested.stdout, 'S10/I9: the refusal names the pinned prefix'
    assert 'crysta-consumer-prefix' not in unrequested.stdout.split('is absent')[0], (
        'S10/I9: the consumer prefix is never read unrequested'
    )


def test_absent_prefix_refuses_with_the_build_remedy(tmp_path):
    result = _run(tmp_path, {})
    assert result.returncode == 1, 'I9: an absent declaration is a refusal (exit 1), never a skip'
    assert 'is absent' in result.stdout, 'I9: the refusal says the declaration is absent'
    assert 'pixi run core-build' in result.stdout, 'I9: the refusal names the remedy'
    assert 'refused, never skipped' in result.stdout, 'I9: the refusal says it is not a skip'


def test_checker_never_imports_crysta():
    source = CHECKER.read_text(encoding='utf-8')
    assert 'import crysta' not in source, 'I14: the edi checker never imports crysta-py'
    assert "import_module('crysta')" not in source, 'I14: nor imports it dynamically'
