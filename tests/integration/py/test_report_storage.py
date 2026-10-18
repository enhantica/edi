"""Both loaders' report-file boundaries and the save staging retention invariant."""

import json
import os
import shlex
from pathlib import Path

import edi as engine
import pytest

from tests.integration.py.test_report_project_options import report, source

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = json.loads((ROOT / 'tests/fixtures/report_storage/reference.json').read_text())


def put(path, relative, text):
    file = path / relative
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text)
    return file


def report_text(settings=None, rows=()):
    text = '_edi.schema_version 3\n' + '\n'.join(settings or REFERENCE['settings']) + '\n'
    if rows:
        text += (
            'loop_\n' + '\n'.join('_report_file.' + key for key in REFERENCE['row_keys']) + '\n'
        )
        text += '\n'.join(' '.join(shlex.quote(value) for value in row) for row in rows) + '\n'
    return text


def inventory(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*') if p.is_file()}


@pytest.mark.parametrize('new_file', [False, True], ids=['defaults', 'new-files-win'])
def test_legacy_report_lines_are_ignored_preserved_and_never_migrated(tmp_path, new_file):
    path = source(tmp_path, [])
    record = path / 'project.edi'
    legacy = ('\n'.join(REFERENCE['legacy']) + '\n').encode()
    record.write_bytes(record.read_bytes() + legacy)
    before = None
    if new_file:
        before = report_text([
            '_report.html true',
            '_report.pdf false',
            '_report.html_offline false',
            '_report.excluded ""',
        ]).encode()
        put(path, 'reports/report.edi', before.decode())
        analysis = path / 'analysis/analysis.edi'
        analysis.write_text(
            analysis.read_text()
            + '\n_correlation_chart.threshold 0.5\n_pattern_chart.x_axis native\n'
        )
    loaded = engine.Project.load(path)
    settings = report(loaded)
    assert (settings.html, settings.pdf, settings.cif, settings.html_offline) == (
        True,
        False,
        False,
        False,
    ), 'I34 legacy formats and Embed never override new-file values or their defaults'
    assert list(settings.excluded) == ([] if new_file else ['data']), (
        'I34 only the new file determines explicit include-all versus absent Data exclusion'
    )
    assert settings.correlation_threshold == (0.5 if new_file else None), (
        'I34 only analysis/analysis.edi determines explicit versus automatic correlation level'
    )
    assert settings.x_axis == 'native', 'I34 the legacy d-spacing option is ignored'
    loaded.save()
    assert legacy in record.read_bytes(), (
        'I34 project Save retains all seven legacy lines byte for byte'
    )
    file = path / 'reports/report.edi'
    assert file.read_bytes() == before if new_file else not file.exists(), (
        'I35 Save neither migrates legacy options nor rewrites an unchanged new settings file'
    )


def test_project_save_changes_only_settings_and_keeps_unchanged_file_bytes_and_time(tmp_path):
    path = source(tmp_path, ['_report.html_offline false'])
    loaded = engine.Project.load(path)
    report(loaded).html_offline = True
    loaded.save()
    file = path / 'reports/report.edi'
    assert '_report.html_offline true' in file.read_text(), (
        'I35 a changed Embed setting is written to its report-owned file'
    )
    assert not list(path.glob('reports/*.html')) and not list(path.glob('reports/*.pdf')), (
        'I35 project Save writes settings and never creates a report output'
    )
    sentinel_ns = 1_700_000_000_123_456_789
    os.utime(file, ns=(sentinel_ns, sentinel_ns))
    before, timestamp = file.read_bytes(), file.stat().st_mtime_ns
    loaded.save()
    assert file.read_bytes() == before and file.stat().st_mtime_ns == timestamp, (
        'I35 unchanged report settings retain both exact bytes and modification time '
        'after staging publish'
    )


def test_save_as_copies_every_report_row_and_file_without_touching_the_source(tmp_path):
    path = source(tmp_path, [])
    text = report_text(rows=REFERENCE['rows'])
    put(path, 'reports/report.edi', text)
    put(path, 'reports/input.html', '<!doctype html><title>opaque source report</title>\n')
    put(
        path,
        'reports/input.pdf',
        '%PDF-1.4\n%opaque existing report; saving a project must not parse it\n',
    )
    put(path, 'reports/older-name.html', 'older report which has no row\n')
    before = inventory(path)
    loaded = engine.Project.load(path)
    target = tmp_path / 'destination'
    loaded.save_as(target)
    assert inventory(path) == before, 'I35 Save as leaves the source inventory and bytes unchanged'
    assert inventory(target / 'reports') == inventory(path / 'reports'), (
        'I35 Save as copies settings, both rows, all report files and an unlisted old '
        'report byte for byte'
    )
    assert (target / 'reports/report.edi').read_text() == text, (
        'I35 Save as retains every saved-file identity and timestamp rather than '
        'generating replacement rows'
    )


@pytest.mark.parametrize(
    'row',
    [
        ['tex', 'input.tex', '2031-02-03T04:05:06Z', '2030-01-02T03:04:05Z', '0123456789abcdef'],
        ['html', 'input.html', '2031-02-03T04:05:06Z', '2030-01-02T03:04:05Z'],
    ],
    ids=['unknown-format', 'incomplete-row'],
)
def test_saved_file_rows_refuse_unknown_formats_and_incomplete_boundaries(tmp_path, row):
    path = source(tmp_path, [])
    put(path, 'reports/report.edi', report_text(rows=[row]))
    with pytest.raises(ValueError, match='_report_file'):
        engine.Project.load(path)


def test_analysis_and_report_files_do_not_write_chart_items_into_project_record(tmp_path):
    path = source(
        tmp_path,
        [
            '_report.html_offline true',
            '_report.correlation_threshold 0.9',
            '_report.x_axis d_spacing',
        ],
    )
    loaded = engine.Project.load(path)
    target = tmp_path / 'saved'
    loaded.save_as(target)
    analysis = (target / 'analysis/analysis.edi').read_text()
    assert (
        '_correlation_chart.threshold 0.9' in analysis
        and '_pattern_chart.x_axis d_spacing' in analysis
    ), 'I34 the two nontrivial chart choices remain in their Analysis categories'
    assert '_report.' not in (target / 'project.edi').read_text(), (
        'I34 a new project record contains no report-owned options'
    )
    assert '_report.correlation_threshold' not in (target / 'reports/report.edi').read_text(), (
        'I34 the report-owned file never owns the Analysis correlation level'
    )
