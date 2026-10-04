"""gates for persisted project identity and missing-record diagnostics."""

from __future__ import annotations

import hashlib
import io
import os
import re
import shlex
import shutil
import subprocess
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import edi
import pytest
from e04_t5_calculator_bytes import without_calculator

from conftest import calculator_load_warning, corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]
PROJECT_WITHOUT_RECORD = ROOT / 'tests/fixtures/c09_t6_ncaf_5bank_absorption/key_absent_project'

# Independent field-name reference: diffraction-lib's written
# tmp/tutorials/projects/refine-cosio-d20-tscan/project.edi. The schema value is edi/crysta's
# current version; diffraction-lib's reference uses version 1 by design.
METADATA_FIELDS = (
    'name',
    'title',
    'description',
    'created',
    'last_modified',
    'timestamp',
)
REFERENCE_PROJECT_RECORD = """\
_edi.schema_version 3

_metadata.name             c11_t56_reference
_metadata.title            "C11 T56 Reference Title"
_metadata.description      "C11 T56 reference description"
_metadata.created          "17 Sep 2024 12:34:56"
_metadata.last_modified    "18 Sep 2024 01:23:45"
_metadata.timestamp        "19 Sep 2024 06:07:08"
"""
OPAQUE_CORPUS_TIMESTAMP = '2026-09-09T07:34:35+00:00'

# Regression pins from the packet's pre-fix measurement at edi 9f531d4 / crysta 26f340ab.
# These are deliberately not presented as independent correctness values: criterion 5 says the
# existing datablock bytes must not move while project-record persistence is added.
PRE_FIX_DATABLOCK_SHA256 = {
    'analysis/analysis.edi': '4dd097a7292bf002ab4757bf63e3774fe517b35187e81378fafa06e08c619781',
    'experiments/sepd.edi': '262ba0c59894678c0c8c66482352ab5117a6642915601c8d62c795ee054ae55a',
    'structures/si.edi': '7ad514f47ced64ec522f8265777254fc3e3c9553174f78cae42631b712cb56c6',
}


def _stage_project_without_record(tmp_path: Path) -> Path:
    staged = tmp_path / 'source'
    shutil.copytree(PROJECT_WITHOUT_RECORD, staged)
    assert not (staged / 'project.edi').exists(), (
        'the  vehicle must begin without the project record whose creation it gates'
    )
    return staged


def _stage_committed_corpus_project(tmp_path: Path) -> Path:
    """Copy the corpus project's committed bytes, never a prior test's saved output."""
    source = corpus_case_dir('si-sepd-s2') / 'project'
    repo = next(
        (parent for parent in (source, *source.parents) if (parent / '.git').exists()),
        None,
    )
    assert repo is not None, (
        'the criterion-5 vehicle must come from a git checkout so its committed pre-save bytes '
        'cannot be replaced by an earlier test mutating the shared corpus worktree'
    )
    relative_source = source.relative_to(repo)
    archive = subprocess.run(
        [
            'git',
            '-C',
            str(repo),
            'archive',
            '--format=tar',
            'HEAD',
            '--',
            relative_source.as_posix(),
        ],
        check=True,
        capture_output=True,
    ).stdout

    staged = tmp_path / 'source'
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as committed:
        files = [member for member in committed.getmembers() if member.isfile()]
        assert files, (
            'the criterion-5 vehicle must resolve tracked si-sepd-s2 project files at crysta HEAD'
        )
        for member in files:
            relative_file = Path(member.name).relative_to(relative_source)
            destination = staged / relative_file
            destination.parent.mkdir(parents=True, exist_ok=True)
            extracted = committed.extractfile(member)
            assert extracted is not None, (
                'every regular file named by the committed project archive must be readable'
            )
            destination.write_bytes(extracted.read())
    return staged


def _star_text(value: datetime) -> str:
    months = (
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'Dec',
    )
    return (
        f'{value.day:02d} {months[value.month - 1]} {value.year:04d} '
        f'{value.hour:02d}:{value.minute:02d}:{value.second:02d}'
    )


def _metadata_values(metadata: edi.ProjectMetadata) -> dict[str, str]:
    return {
        'name': metadata.name,
        'title': metadata.title,
        'description': metadata.description,
        'created': _star_text(metadata.created),
        'last_modified': _star_text(metadata.last_modified),
        'timestamp': metadata.timestamp,
    }


def _reference_token(value: str) -> str:
    if not value:
        return '?'
    if any(character.isspace() for character in value) or value[0] in "_#$'?;":
        return f'"{value}"'
    return value


def _assert_metadata_record(record_text: str, expected: dict[str, str]) -> None:
    schema_lines = re.findall(r'^_edi\.schema_version\s+(\S+)\s*$', record_text, re.MULTILINE)
    assert schema_lines == ['3'], (
        'project.edi must contain exactly one edi/crysta schema-version 3 declaration'
    )
    for field in METADATA_FIELDS:
        tag = f'_metadata.{field}'
        values = re.findall(rf'^{re.escape(tag)}[ \t]+(.+?)\s*$', record_text, re.MULTILINE)
        assert values == [_reference_token(expected[field])], (
            f'project.edi must write exactly one {tag} using the diffraction-lib field spelling '
            'and the project metadata value'
        )


def _assert_metadata_values(actual: dict[str, str], expected: dict[str, str]) -> None:
    for field in METADATA_FIELDS:
        assert actual[field] == expected[field], (
            f'Project.load must restore _metadata.{field} exactly instead of substituting a '
            'default or dropping the saved value'
        )


def _assert_metadata_restored(restored: edi.ProjectMetadata, expected: dict[str, str]) -> None:
    _assert_metadata_values(_metadata_values(restored), expected)


def _save_through_route(
    project: edi.Project,
    source: Path,
    tmp_path: Path,
    route: str,
) -> Path:
    if route == 'save_as':
        saved = tmp_path / 'saved'
        project.save_as(saved)
        return saved
    getattr(project, route)()
    return source


@pytest.mark.parametrize('route', ['save_as', 'save', '_save_silent'])
def test_c11_t56_all_owned_metadata_matches_live_project_after_each_save_route(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    route: str,
) -> None:
    source = _stage_project_without_record(tmp_path)
    project = edi.Project.load(source)
    capfd.readouterr()
    project.metadata.name = 'c11_t56_named_project'
    project.metadata.title = 'C11 T56 Nontrivial Title'
    project.metadata.description = 'C11 T56 nontrivial description'
    project.metadata.timestamp = '19 Sep 2024 06:07:08'
    before_save = project.metadata.last_modified

    saved = _save_through_route(project, source, tmp_path, route)
    live_after_save = _metadata_values(project.metadata)

    assert project.metadata.last_modified > before_save, (
        f'{route} must exercise the save-triggered metadata mutation whose persisted identity '
        'this gate proves'
    )
    for field in METADATA_FIELDS:
        assert live_after_save[field], (
            f'the  round-trip vehicle must carry a non-empty _metadata.{field} value'
        )

    record = saved / 'project.edi'
    assert record.is_file(), (
        f'{route} must create project.edi at the project root before identity can round-trip'
    )
    _assert_metadata_record(record.read_text(encoding='utf-8'), live_after_save)
    capfd.readouterr()

    restored = edi.Project.load(saved)
    captured = capfd.readouterr()

    _assert_metadata_restored(restored.metadata, live_after_save)
    assert not captured.out, (
        'loading an existing project.edi must leave the stdout machine channel exactly empty'
    )
    assert captured.err == calculator_load_warning(saved), (
        'complete metadata emits no stderr beyond the declared  calculator warning'
    )


@pytest.mark.parametrize('field', METADATA_FIELDS)
def test_c11_t56_identity_oracle_rejects_each_single_field_disagreement(field: str) -> None:
    expected = dict(REFERENCE_METADATA)
    mismatched = dict(expected)
    mismatched[field] = f'oracle-disagreement-{field}'

    with pytest.raises(AssertionError, match=rf'_metadata\.{field}'):
        _assert_metadata_values(mismatched, expected)

    mismatched_record = _replace_tag_value(
        REFERENCE_PROJECT_RECORD,
        f'_metadata.{field}',
        _reference_token(mismatched[field]),
    )
    with pytest.raises(AssertionError, match=rf'_metadata\.{field}'):
        _assert_metadata_record(mismatched_record, expected)


@pytest.mark.parametrize('field', ['title', 'description', 'timestamp'])
def test_c11_t56_literal_star_missing_token_survives_save_load(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    field: str,
) -> None:
    source = _stage_project_without_record(tmp_path)
    project = edi.Project.load(source)
    capfd.readouterr()
    setattr(project.metadata, field, '?')

    saved = tmp_path / f'literal-{field}'
    project.save_as(saved)
    record_text = (saved / 'project.edi').read_text(encoding='utf-8')
    tokens = re.findall(
        rf'^_metadata\.{field}[ \t]+(.+?)\s*$',
        record_text,
        re.MULTILINE,
    )
    assert tokens == ['"?"'], (
        f'a literal question mark in _metadata.{field} must be quoted so it stays distinct '
        'from the unquoted STAR missing-value token'
    )

    capfd.readouterr()
    restored = edi.Project.load(saved)
    captured = capfd.readouterr()
    assert getattr(restored.metadata, field) == '?', (
        f'a quoted literal question mark in _metadata.{field} must survive save-load unchanged'
    )
    assert not captured.out and captured.err == calculator_load_warning(saved), (
        'a complete literal question-mark record admits only its declared calculator warning'
    )


@pytest.mark.parametrize('field', ['title', 'description', 'timestamp'])
def test_c11_t56_bare_star_missing_token_remains_empty(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    field: str,
) -> None:
    source = _stage_project_without_record(tmp_path)
    record_text = _replace_tag_value(
        REFERENCE_PROJECT_RECORD,
        f'_metadata.{field}',
        '?',
    )
    (source / 'project.edi').write_text(record_text, encoding='utf-8')

    restored = edi.Project.load(source)
    captured = capfd.readouterr()
    expected = None if field == 'timestamp' else ''
    assert getattr(restored.metadata, field) == expected, (
        f'an unquoted STAR missing-value token in _metadata.{field} must stay distinct from '
        'the quoted literal question-mark value'
    )
    assert not captured.out and captured.err == calculator_load_warning(source), (
        'a complete missing-value record admits only its declared calculator warning'
    )


def test_c11_t56_missing_project_record_defaults_with_one_stderr_diagnostic(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    source = _stage_project_without_record(tmp_path)

    restored = edi.Project.load(source)
    captured = capfd.readouterr()

    assert restored.metadata.name == 'untitled_project', (
        'a legacy datablock directory without project.edi must remain loadable with '
        'default metadata'
    )
    assert not captured.out, 'the missing-project.edi diagnostic must leave stdout exactly empty'
    expected_warning = (
        f"Warning: no project.edi in '{source}' - loading with default metadata "
        "(name 'untitled_project')\n"
    )
    assert captured.err == calculator_load_warning(source) + expected_warning, (
        'a missing project.edi emits exactly its diagnostic after the declared calculator warning'
    )


def _without_tag(record: str, tag: str) -> str:
    return re.sub(rf'^{re.escape(tag)}[^\n]*\n?', '', record, count=1, flags=re.MULTILINE)


def _replace_tag_value(record: str, tag: str, value: str) -> str:
    return re.sub(
        rf'^{re.escape(tag)}[^\n]*$',
        f'{tag} {value}',
        record,
        count=1,
        flags=re.MULTILINE,
    )


REFERENCE_METADATA = {
    'name': 'c11_t56_reference',
    'title': 'C11 T56 Reference Title',
    'description': 'C11 T56 reference description',
    'created': '17 Sep 2024 12:34:56',
    'last_modified': '18 Sep 2024 01:23:45',
    'timestamp': '19 Sep 2024 06:07:08',
}
STATIC_CONSTRUCTED_DEFAULTS = {
    'name': 'untitled_project',
    'title': 'Untitled Project',
    'description': '',
    'timestamp': None,
}

# Precedence makes the packet's record states disjoint: after presence, filesystem/read and
# lexical failures refuse first; a parsed record the loader cannot prove it understands refuses
# next; only an understood record can reach completeness, where missing fields retain defaults.
# The reason fragments on overlap cases prove which earlier branch won.
TEXT_REFUSALS = [
    pytest.param('', '_edi.schema_version', 'declares no', id='precedence-empty-is-no-schema'),
    pytest.param(
        '_edi.schema_version 3\n_metadata.name "unterminated\n',
        None,
        None,
        id='malformed-unterminated-quote',
    ),
    pytest.param(
        '_edi.schema_version 3\n_metadata.name\n',
        None,
        None,
        id='malformed-missing-value',
    ),
    pytest.param(
        _without_tag(REFERENCE_PROJECT_RECORD, '_edi.schema_version'),
        '_edi.schema_version',
        'declares no',
        id='not-understood-no-schema',
    ),
    pytest.param(
        _without_tag(
            _without_tag(REFERENCE_PROJECT_RECORD, '_edi.schema_version'),
            '_metadata.title',
        ),
        '_edi.schema_version',
        'declares no',
        id='precedence-no-schema-before-incomplete',
    ),
    *[
        pytest.param(
            REFERENCE_PROJECT_RECORD.replace(
                '_edi.schema_version 3', f'_edi.schema_version {value}'
            ),
            '_edi.schema_version',
            'unsupported',
            id=f'not-understood-schema-{label}',
        )
        for value, label in ((0, 'below-range'), (4, 'above-range'), (999, 'far-above-range'))
    ],
    pytest.param(
        REFERENCE_PROJECT_RECORD.replace('_edi.schema_version 3', '_edi.schema_version newer'),
        '_edi.schema_version',
        'unsupported',
        id='not-understood-schema-non-integer',
    ),
    *[
        pytest.param(
            REFERENCE_PROJECT_RECORD + f'_metadata.{field} duplicate_value\n',
            f'_metadata.{field}',
            'more than once',
            id=f'not-understood-duplicate-{field}',
        )
        for field in METADATA_FIELDS
    ],
    pytest.param(
        _replace_tag_value(REFERENCE_PROJECT_RECORD, '_metadata.name', 'invalid/name')
        + '_metadata.name duplicate_name\n',
        '_metadata.name',
        'more than once',
        id='precedence-duplicate-before-invalid-value',
    ),
    pytest.param(
        _replace_tag_value(REFERENCE_PROJECT_RECORD, '_metadata.name', 'invalid/name'),
        '_metadata.name',
        'path separator',
        id='not-understood-name-forward-slash',
    ),
    pytest.param(
        _replace_tag_value(REFERENCE_PROJECT_RECORD, '_metadata.name', r'invalid\\name'),
        '_metadata.name',
        'path separator',
        id='not-understood-name-backslash',
    ),
    pytest.param(
        _replace_tag_value(REFERENCE_PROJECT_RECORD, '_metadata.created', 'not-a-timestamp'),
        '_metadata.created',
        'STAR timestamp',
        id='not-understood-created-timestamp',
    ),
    pytest.param(
        _replace_tag_value(REFERENCE_PROJECT_RECORD, '_metadata.last_modified', '2024-09-18'),
        '_metadata.last_modified',
        'STAR timestamp',
        id='not-understood-last-modified-timestamp',
    ),
]

SEMANTIC_DATETIME_REFUSALS = (
    pytest.param('31 Feb 2024 12:34:56', id='february-31'),
    pytest.param('29 Feb 2023 12:34:56', id='non-leap-february-29'),
    pytest.param('31 Apr 2024 12:34:56', id='april-31'),
    pytest.param('00 Jan 2024 12:34:56', id='day-zero'),
    pytest.param('01 Jan 0000 12:34:56', id='year-zero'),
    pytest.param('01 Jan 2024 24:00:00', id='hour-24'),
    pytest.param('01 Jan 2024 23:60:00', id='minute-60'),
    pytest.param('01 Jan 2024 23:59:60', id='second-60'),
)


def _assert_record_refuses(
    source: Path,
    capfd: pytest.CaptureFixture[str],
    *,
    offending_item: str | None = None,
    reason: str | None = None,
) -> None:
    record = source / 'project.edi'
    capfd.readouterr()
    with pytest.raises(edi.IoError) as captured_error:
        edi.Project.load(source)
    capfd.readouterr()

    message = str(captured_error.value)
    assert str(record) in message, (
        'refusing a present project.edi must name the exact record path that was not restored'
    )
    if offending_item is not None:
        assert offending_item in message, (
            'refusing a parsed but not understood project.edi must name the specific offending '
            'schema or metadata item'
        )
    if reason is not None:
        assert reason in message, (
            'an overlapping project.edi state must follow the committed precedence branch'
        )


@pytest.mark.parametrize(('record_text', 'offending_item', 'reason'), TEXT_REFUSALS)
def test_c11_t56_present_text_record_refuses_with_state_specific_io_error(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    record_text: str,
    offending_item: str | None,
    reason: str | None,
) -> None:
    source = _stage_project_without_record(tmp_path)
    (source / 'project.edi').write_text(record_text, encoding='utf-8')

    _assert_record_refuses(
        source,
        capfd,
        offending_item=offending_item,
        reason=reason,
    )


@pytest.mark.parametrize('field', ['created', 'last_modified'])
@pytest.mark.parametrize('invalid_value', SEMANTIC_DATETIME_REFUSALS)
def test_c11_t56_semantically_invalid_datetime_refuses_at_record_boundary(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    field: str,
    invalid_value: str,
) -> None:
    source = _stage_project_without_record(tmp_path)
    record_text = _replace_tag_value(
        REFERENCE_PROJECT_RECORD,
        f'_metadata.{field}',
        f'"{invalid_value}"',
    )
    (source / 'project.edi').write_text(record_text, encoding='utf-8')

    _assert_record_refuses(
        source,
        capfd,
        offending_item=f'_metadata.{field}',
    )


@pytest.mark.parametrize('field', ['created', 'last_modified'])
def test_c11_t56_valid_leap_day_datetime_remains_materializable(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    field: str,
) -> None:
    source = _stage_project_without_record(tmp_path)
    leap_day = '29 Feb 2024 23:59:59'
    record_text = _replace_tag_value(
        REFERENCE_PROJECT_RECORD,
        f'_metadata.{field}',
        f'"{leap_day}"',
    )
    (source / 'project.edi').write_text(record_text, encoding='utf-8')

    restored = edi.Project.load(source)
    captured = capfd.readouterr()

    assert _star_text(getattr(restored.metadata, field)) == leap_day, (
        f'a real leap-day _metadata.{field} must remain accepted while impossible dates refuse'
    )
    assert not captured.out and captured.err == calculator_load_warning(source), (
        'a complete leap-day record admits only its declared calculator warning'
    )


def test_c11_t56_opaque_fit_timestamp_round_trips_byte_identically(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    source = _stage_project_without_record(tmp_path)
    record = source / 'project.edi'
    record.write_text(
        _replace_tag_value(
            REFERENCE_PROJECT_RECORD,
            '_metadata.timestamp',
            OPAQUE_CORPUS_TIMESTAMP,
        ),
        encoding='utf-8',
    )

    loaded = edi.Project.load(source)
    captured = capfd.readouterr()
    assert loaded.metadata.timestamp == OPAQUE_CORPUS_TIMESTAMP, (
        '_metadata.timestamp is an opaque string and must not be STAR-validated on load'
    )
    assert not captured.out and captured.err == calculator_load_warning(source), (
        'a complete opaque-timestamp record admits only its declared calculator warning'
    )

    saved = tmp_path / 'saved'
    loaded.save_as(saved)
    timestamp_token = rb'^_metadata\.timestamp[ \t]+(.+?)[ \t]*$'
    original_tokens = re.findall(timestamp_token, record.read_bytes(), re.MULTILINE)
    saved_tokens = re.findall(
        timestamp_token,
        (saved / 'project.edi').read_bytes(),
        re.MULTILINE,
    )
    assert saved_tokens == original_tokens == [OPAQUE_CORPUS_TIMESTAMP.encode()], (
        'save_as must write an opaque _metadata.timestamp value back byte-identically'
    )

    capfd.readouterr()
    restored = edi.Project.load(saved)
    captured = capfd.readouterr()
    assert restored.metadata.timestamp == OPAQUE_CORPUS_TIMESTAMP, (
        'the opaque _metadata.timestamp value must survive load-save-load unchanged'
    )
    assert not captured.out and captured.err == calculator_load_warning(saved), (
        'a saved opaque-timestamp record admits only its declared calculator warning'
    )


@pytest.mark.parametrize(
    'relative_project',
    [
        pytest.param(Path('project'), id='edi-corpus-record'),
        pytest.param(Path('diffraction-lib/project'), id='diffraction-lib-corpus-record'),
    ],
)
def test_c11_t56_committed_corpus_metadata_dates_remain_loadable(
    relative_project: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    source = corpus_case_dir('cosio-d20-scan-3f') / relative_project

    restored = edi.Project.load(source)
    captured = capfd.readouterr()

    assert _star_text(restored.metadata.created) == '09 Sep 2026 07:33:40', (
        'the committed corpus _metadata.created value must remain accepted by its validator'
    )
    assert _star_text(restored.metadata.last_modified) == '09 Sep 2026 07:34:27', (
        'the committed corpus _metadata.last_modified value must remain accepted by its validator'
    )
    assert restored.metadata.timestamp == OPAQUE_CORPUS_TIMESTAMP, (
        'the committed corpus fit timestamp must remain an opaque string'
    )
    #  and  add declared type diagnostics; metadata stays silent.
    declared_types = [
        shlex.split(line)[1]
        for line in (source / 'analysis/analysis.edi').read_text().splitlines()
        if line.startswith('_minimizer.type ')
    ]
    expected_warning = ''.join(
        f'Warning: unsupported _minimizer.type "{declared_type}" - using crysta\n'
        for declared_type in declared_types
        if declared_type != 'crysta'
    )
    assert (
        not captured.out and captured.err == calculator_load_warning(source) + expected_warning
    ), 'complete metadata allows exactly the declared calculator and minimizer warnings'


@pytest.mark.parametrize(
    'missing_fields',
    [
        *(pytest.param((field,), id=f'missing-{field}') for field in METADATA_FIELDS),
        pytest.param(
            ('title', 'description', 'timestamp'),
            id='missing-multiple-fields-keeps-each-default',
        ),
    ],
)
def test_c11_t56_incomplete_record_restores_present_fields_and_keeps_defaults(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    missing_fields: tuple[str, ...],
) -> None:
    source = _stage_project_without_record(tmp_path)
    record_text = REFERENCE_PROJECT_RECORD
    for field in missing_fields:
        record_text = _without_tag(record_text, f'_metadata.{field}')
    (source / 'project.edi').write_text(record_text, encoding='utf-8')

    default_time_floor = datetime.now(UTC).replace(microsecond=0) - timedelta(seconds=1)
    restored = edi.Project.load(source)
    default_time_ceiling = datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=1)
    captured = capfd.readouterr()

    actual = _metadata_values(restored.metadata)
    for field in METADATA_FIELDS:
        if field not in missing_fields:
            assert actual[field] == REFERENCE_METADATA[field], (
                f'an incomplete project.edi must restore its present _metadata.{field} value'
            )
        elif field in {'created', 'last_modified'}:
            value = getattr(restored.metadata, field)
            assert default_time_floor <= value <= default_time_ceiling, (
                f'a missing _metadata.{field} must keep the freshly constructed timestamp default'
            )
        else:
            assert actual[field] == STATIC_CONSTRUCTED_DEFAULTS[field], (
                f'a missing _metadata.{field} must keep its constructed metadata default'
            )

    assert not captured.out and captured.err == calculator_load_warning(source), (
        'an incomplete project.edi must restore present fields and retain constructed defaults '
        'for missing fields; stderr contains only the declared calculator warning'
    )


def test_c11_t56_present_invalid_utf8_record_refuses_with_io_error(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    source = _stage_project_without_record(tmp_path)
    (source / 'project.edi').write_bytes(b'\xff\xfe\x00')

    _assert_record_refuses(source, capfd)


def test_c11_t56_present_unreadable_record_refuses_with_io_error(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    source = _stage_project_without_record(tmp_path)
    record = source / 'project.edi'
    record.write_text(REFERENCE_PROJECT_RECORD, encoding='utf-8')
    record.chmod(0)
    try:
        assert not os.access(record, os.R_OK), (
            'the filesystem-failure vehicle must make project.edi unreadable before loading'
        )
        _assert_record_refuses(source, capfd)
    finally:
        record.chmod(0o600)


def test_c11_t56_present_directory_record_refuses_with_io_error(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    source = _stage_project_without_record(tmp_path)
    (source / 'project.edi').mkdir()

    _assert_record_refuses(source, capfd)


def test_c11_t56_present_broken_symlink_record_refuses_with_io_error(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    source = _stage_project_without_record(tmp_path)
    record = source / 'project.edi'
    record.symlink_to(source / 'missing-record-target')
    assert os.path.lexists(record), (
        'the filesystem-failure vehicle must leave a present directory entry for project.edi'
    )
    assert not record.exists(), 'the filesystem-failure vehicle must be a broken symlink'

    _assert_record_refuses(source, capfd)


def _save_project_with_record(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> tuple[edi.Project, Path]:
    source = _stage_project_without_record(tmp_path)
    project = edi.Project.load(source)
    capfd.readouterr()
    saved = tmp_path / 'saved'
    project.save_as(saved)
    capfd.readouterr()
    record = saved / 'project.edi'
    assert record.is_file(), (
        'the carried-record failure vehicle must begin with a regular project.edi document'
    )
    return project, record


def test_c11_t56_save_refuses_broken_carried_record_without_replacing_it(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    project, record = _save_project_with_record(tmp_path, capfd)
    missing_target = tmp_path / 'missing-carried-record'
    record.unlink()
    record.symlink_to(missing_target)
    before_last_modified = project.metadata.last_modified

    with pytest.raises(
        (edi.IoError, OSError, ValueError),
        match=r'project|record|read|stage|save',
    ):
        project.save()

    assert record.is_symlink() and not record.exists(), (
        'a failed save must preserve the broken carried project.edi entry instead of replacing '
        'it with a metadata-only regular file'
    )
    assert record.readlink() == missing_target, (
        'a failed save must leave the unreadable carried project.edi link target unchanged'
    )
    assert project.metadata.last_modified == before_last_modified, (
        'a save that cannot merge its carried record must not advance live last_modified'
    )


def test_c11_t56_save_refuses_unreadable_carried_record_without_replacing_it(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    project, record = _save_project_with_record(tmp_path, capfd)
    expected_bytes = record.read_bytes()
    before_last_modified = project.metadata.last_modified
    record.chmod(0)
    try:
        assert not os.access(record, os.R_OK), (
            'the carried-record failure vehicle must remove read access before save'
        )
        with pytest.raises(
            (edi.IoError, OSError, ValueError),
            match=r'project|record|read|stage|save',
        ):
            project.save()

        assert record.is_file() and record.stat().st_mode & 0o777 == 0, (
            'a failed save must preserve the unreadable carried project.edi entry and mode'
        )
        assert project.metadata.last_modified == before_last_modified, (
            'a save that cannot read its carried record must not advance live last_modified'
        )
    finally:
        record.chmod(0o600)
    assert record.read_bytes() == expected_bytes, (
        'a failed save must leave every byte of the unreadable carried project.edi unchanged'
    )


def test_c11_t56_datablock_bytes_match_pre_fix_regression_pins(tmp_path: Path) -> None:
    source = _stage_committed_corpus_project(tmp_path)
    (source / 'project.edi').unlink()
    project = edi.Project.load(source)
    project.metadata.name = 'si_sepd'
    saved = tmp_path / 'saved'

    project.save_as(saved)

    for relative_path, expected_sha256 in PRE_FIX_DATABLOCK_SHA256.items():
        data = without_calculator(relative_path, (saved / relative_path).read_bytes())
        if relative_path == 'analysis/analysis.edi':
            #  adds precisely the previously dropped minimizer declaration.
            original = [
                shlex.split(line)
                for line in (source / relative_path).read_text().splitlines()
                if line.startswith('_minimizer.type ')
            ]
            emitted = [
                shlex.split(line)
                for line in data.decode().splitlines()
                if line.startswith('_minimizer.type ')
            ]
            assert emitted == original and len(emitted) == 1, (
                ' must add exactly the source minimizer declaration to saved analysis'
            )
            data, removed = re.subn(rb'(?m)^_minimizer\.type [^\n]*\n\n', b'', data)
            assert removed == 1, ' normalizes only the one newly persisted declaration'
        if relative_path == 'structures/si.edi':
            #  now retains the two source-declared _geom inputs. Keep
            # the old regression hash as a byte oracle for every other field.
            original = (source / relative_path).read_bytes()
            assert original.count(b'_geom.min_bond_distance_cutoff 0.\n') == 1, (
                ' the source structure declares one minimum bond cutoff'
            )
            assert original.count(b'_geom.bond_distance_inc 0.25\n') == 1, (
                ' the source structure declares one bond distance increment'
            )
            block = b'_geom.min_bond_distance_cutoff 0\n_geom.bond_distance_inc 0.25\n'
            assert data.count(block) == 1, (
                ' the saved structure keeps each declared geom value once'
            )
            assert data.count(b'\n' + block) == 1, (
                ' the geometry block is separated once before the old byte oracle'
            )
            data = data.replace(b'\n' + block, b'', 1)
        actual_sha256 = hashlib.sha256(data).hexdigest()
        assert actual_sha256 == expected_sha256, (
            f"{relative_path} must remain byte-identical to the packet's labelled pre-fix "
            'regression pin apart from the separately checked  minimizer, '
            ' geom and  calculator declarations'
        )
