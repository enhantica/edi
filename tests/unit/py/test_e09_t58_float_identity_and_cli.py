"""Float provenance and project-owned CLI behavior, from the  contract.

Identity strings are synthetic format fixtures, not repository anchors. CLI doubles
isolate routing/persistence; literal records follow the public schema-8 undo contract.
No refinement or generated scientific reference is used by these unit cases.
"""

from __future__ import annotations

import importlib.metadata
from pathlib import Path
from types import SimpleNamespace

import edi
import edi.__main__ as cli
import pytest
from edi import verification as verify

SOURCE_SHA = ('0123456789abcdef' * 3)[:40]


def _identity_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(verify, '_repo_root', lambda: tmp_path)
    monkeypatch.setattr(importlib.metadata, 'version', lambda _name: '0.8.0+gabcdef1')
    # These record-reading cases prove the ordinary float artifact. The paired consumer build
    # deliberately has no CRYSTA_SOURCE_SHA; ambient selectors must not silently change which
    # artifact the unit case claims to exercise.
    monkeypatch.delenv('EDI_EXTENSION_DIR', raising=False)
    monkeypatch.delenv('EDI_USE_CONSUMER_BUILD', raising=False)
    monkeypatch.delenv('CRYSTA_CONSUMER_SRC', raising=False)
    record = tmp_path / 'build' / 'crysta-src' / 'CRYSTA_SOURCE_SHA'
    record.parent.mkdir(parents=True)
    return record


def test_float_label_reads_recorded_source_and_preserves_the_note(tmp_path, monkeypatch):
    record = _identity_root(tmp_path, monkeypatch)
    record.write_text(SOURCE_SHA + '\n', encoding='utf-8')
    assert (
        verify.engine_label('crysta', note='refined') == 'edi 0.8.0 (crysta 0123456, refined)'
    ), 'the float label must identify the recorded source and preserve the comparison note'
    record.write_text('fedcba9876543210' * 2 + 'fedcba98\n', encoding='utf-8')
    assert verify.engine_label('crysta') == 'edi 0.8.0 (crysta fedcba9)', (
        'the label must follow a new recorded source rather than cache the previous identity'
    )


def test_float_label_marks_missing_empty_and_unreadable_records_unknown(tmp_path, monkeypatch):
    record = _identity_root(tmp_path, monkeypatch)
    assert verify.engine_label('crysta') == 'edi 0.8.0 (crysta ?)', (
        'a missing fetched-source record must render an explicit unknown identity'
    )
    record.write_text(' \n', encoding='utf-8')
    assert verify.engine_label('crysta') == 'edi 0.8.0 (crysta ?)', (
        'a blank fetched-source record must not masquerade as a known identity'
    )

    def unreadable(_path, **_kwargs):
        raise PermissionError('source record is unreadable')

    monkeypatch.setattr(Path, 'read_text', unreadable)
    assert verify.engine_label('crysta') == 'edi 0.8.0 (crysta ?)', (
        'an unreadable source record must remain visibly unknown without inventing provenance'
    )


def test_float_label_rejects_malformed_source_identity(tmp_path, monkeypatch):
    record = _identity_root(tmp_path, monkeypatch)
    labels = []
    for malformed in ('not-a-sha', 'f' * 39, 'f' * 41, 'crysta-source: ' + SOURCE_SHA):
        record.write_text(malformed + '\n', encoding='utf-8')
        labels.append(verify.engine_label('crysta'))
    assert labels == ['edi 0.8.0 (crysta ?)'] * 4, (
        'malformed, abbreviated, overlong and log-prefixed records must not claim a source sha'
    )


def test_float_label_keeps_distribution_absence_and_non_vcs_local_versions(tmp_path, monkeypatch):
    record = _identity_root(tmp_path, monkeypatch)
    record.write_text(SOURCE_SHA, encoding='utf-8')
    monkeypatch.setattr(importlib.metadata, 'version', lambda _name: '0.8.0+local.2')
    assert verify.engine_label('crysta') == 'edi 0.8.0+local.2 (crysta 0123456)', (
        'a meaningful non-VCS local version must survive display normalization'
    )

    def missing_distribution(_name):
        raise importlib.metadata.PackageNotFoundError('easydiffraction')

    monkeypatch.setattr(importlib.metadata, 'version', missing_distribution)
    assert verify.engine_label('crysta') == 'edi ? (crysta 0123456)', (
        'missing edi distribution metadata must not discard the known engine identity'
    )


def test_consumer_source_selector_refuses_bare_values_and_accepts_only_named_contracts(
    tmp_path, monkeypatch
):
    bare = tmp_path / 'not-a-crysta-tree'
    bare.mkdir()
    monkeypatch.setenv('CRYSTA_CONSUMER_SRC', str(bare))
    assert verify._consumer_source_is_tree() is False, (
        ' a directory without the crysta source marker must not select a consumer build'
    )
    assert verify._consumer_source_selects() is False, (
        ' a merely truthy source-path value must not redirect runtime provenance'
    )

    monkeypatch.setenv('CRYSTA_CONSUMER_SRC', 'hidden-surface-control')
    assert verify._consumer_source_selects() is True, (
        ' the one named hidden-control selector must remain expressible after the split'
    )

    source = tmp_path / 'crysta'
    source.mkdir()
    source.joinpath('CMakeLists.txt').write_text('project(crysta)\n', encoding='utf-8')
    monkeypatch.setenv('CRYSTA_CONSUMER_SRC', str(source))
    assert verify._consumer_source_is_tree() is True, (
        ' a source path carrying the crysta build marker must validate as a real tree'
    )
    assert verify._consumer_source_selects() is True, (
        ' a validated crysta tree must select the consumer configuration'
    )


def test_consumer_provenance_refuses_a_live_source_mismatch(tmp_path, monkeypatch):
    linked = tmp_path / 'build' / 'ci-consumer' / '.crysta-linked-sha'
    linked.parent.mkdir(parents=True)
    linked.write_text(SOURCE_SHA, encoding='utf-8')
    live_sha = 'f' * 40
    source = tmp_path / 'crysta'
    monkeypatch.setenv('CRYSTA_CONSUMER_SRC', str(source))
    monkeypatch.setattr(verify, '_crysta_provenance_path', lambda: linked)
    monkeypatch.setattr(verify, '_consumer_source_is_tree', lambda: True)

    def live_head(command, **kwargs):
        assert command == ['git', '-C', str(source), 'rev-parse', 'HEAD'], (
            ' provenance must query the exact live source selected by the caller'
        )
        assert kwargs == {'capture_output': True, 'text': True, 'check': False}, (
            ' the live identity query must stay non-throwing and inspectable'
        )
        return SimpleNamespace(returncode=0, stdout=live_sha + '\n')

    monkeypatch.setattr(verify.subprocess, 'run', live_head)
    assert verify._crysta_display_pin() is None, (
        ' a consumer artifact built from another source sha must render unknown provenance'
    )

    linked.write_text(live_sha, encoding='utf-8')
    assert verify._crysta_display_pin() == live_sha[:7], (
        ' matching live and linked source identities must render the linked abbreviation'
    )


def test_consumer_provenance_path_tracks_the_selected_build(tmp_path, monkeypatch):
    monkeypatch.setattr(verify, '_repo_root', lambda: tmp_path)
    monkeypatch.delenv('EDI_EXTENSION_DIR', raising=False)
    monkeypatch.delenv('EDI_USE_CONSUMER_BUILD', raising=False)
    monkeypatch.delenv('CRYSTA_CONSUMER_SRC', raising=False)
    assert verify._crysta_provenance_path() == (
        tmp_path / 'build' / 'crysta-src' / 'CRYSTA_SOURCE_SHA'
    ), ' the ordinary build must retain the fetched-source provenance record'

    monkeypatch.setenv('EDI_USE_CONSUMER_BUILD', '1')
    assert verify._crysta_provenance_path() == (
        tmp_path / 'build' / 'ci-consumer' / '.crysta-linked-sha'
    ), ' the explicit runtime selector must read provenance beside the consumer artifact'

    extension = tmp_path / 'build' / 'custom' / 'python' / 'edi'
    monkeypatch.setenv('EDI_EXTENSION_DIR', str(extension))
    assert verify._crysta_provenance_path() == (
        tmp_path / 'build' / 'custom' / '.crysta-linked-sha'
    ), ' an explicit extension directory must bind provenance to that exact build artifact'


@pytest.mark.parametrize('report', ['human', 'machine'])
@pytest.mark.parametrize('dry', [False, True])
def test_cli_fit_reads_analysis_and_saves_only_when_requested(monkeypatch, capsys, report, dry):
    calls = []
    outcome = object()

    def fit(**kwargs):
        assert kwargs == {}, 'the quiet project fit must receive no duplicate model inputs'
        calls.append('fit')
        return outcome

    project = SimpleNamespace(
        analysis=SimpleNamespace(fit=fit, fitting_mode='single'),
        save=lambda: calls.append('save'),
        _save_silent=lambda: calls.append('silent-save'),
    )

    def load(path):
        assert path == 'project', 'the CLI must load exactly the project selected by its argument'
        return project

    def machine_record(given, result, verbosity):
        assert (given, result, verbosity) == (project, outcome, edi.VerbosityEnum.OFF), (
            'machine formatting must receive the same model and its analysis outcome'
        )
        return ''

    monkeypatch.setattr(cli.edi, 'Project', SimpleNamespace(load=load))
    monkeypatch.setattr(cli.edi, 'machine_report', machine_record)
    argv = ['fit', 'project', '--report', report, '--verbosity', 'off']
    if dry:
        argv.append('--dry')
    assert cli.main(argv) == 0, 'a successful model-owned fit must return success through main'
    expected = ['fit'] if dry else ['fit', 'save' if report == 'human' else 'silent-save']
    assert calls == expected, 'dry fits must not persist and machine saves must remain silent'
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ('', ''), (
        'quiet fit success must leave both output channels empty'
    )


@pytest.mark.parametrize(
    'case',
    [
        (
            'machine',
            'full',
            False,
            False,
            'silent-save',
            (
                'schema=8\nrecord=undo\nwas_no_op=false\nrestored=2\n'
                'restored_parameter=structure.cell.length_a\nrestored_parameter=experiment.scale\n'
            ),
        ),
        (
            'machine',
            'compact',
            True,
            False,
            None,
            'schema=8\nrecord=undo\nwas_no_op=false\nrestored=2\n',
        ),
        (
            'machine',
            'compact',
            False,
            True,
            None,
            'schema=8\nrecord=undo\nwas_no_op=true\nrestored=0\n',
        ),
        ('machine', 'off', False, False, 'silent-save', ''),
        (
            'human',
            'full',
            False,
            False,
            'save',
            (
                'Restored 2 parameter(s) to their pre-fit state.\n'
                '  structure.cell.length_a\n  experiment.scale\n'
            ),
        ),
        (
            'human',
            'compact',
            True,
            False,
            None,
            'Restored 2 parameter(s) to their pre-fit state.\n',
        ),
        (
            'human',
            'compact',
            False,
            True,
            None,
            'Nothing to undo: no fit state is recorded in this project.\n',
        ),
        ('human', 'off', False, False, 'save', ''),
    ],
    ids=[
        'machine-full',
        'machine-dry',
        'machine-noop',
        'machine-off',
        'human-full',
        'human-dry',
        'human-noop',
        'human-off',
    ],
)
def test_cli_undo_routes_model_outcomes_without_unrequested_writes(monkeypatch, capsys, case):
    report, verbosity, dry, noop, save, expected = case
    calls = []
    restored = [] if noop else ['structure.cell.length_a', 'experiment.scale']

    def undo():
        calls.append('undo')
        return restored, noop

    project = SimpleNamespace(
        _undo_fit=undo,
        save=lambda: calls.append('save'),
        _save_silent=lambda: calls.append('silent-save'),
    )
    monkeypatch.setattr(cli.edi, 'Project', SimpleNamespace(load=lambda _path: project))
    argv = ['undo', 'project', '--report', report, '--verbosity', verbosity]
    if dry:
        argv.append('--dry')
    assert cli.main(argv) == 0, 'undo dispatch must succeed for restored and no-op model outcomes'
    assert calls == (['undo', save] if save else ['undo']), (
        'undo must persist only non-dry changes using the selected report channel'
    )
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == (expected, ''), (
        'undo output must follow the literal schema or human contract without stderr noise'
    )
