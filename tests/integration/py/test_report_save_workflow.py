"""Report save and check are observed through real files and the public CLI/Python paths."""

import json
import re
import shlex
import subprocess
import sys

import edi
import numpy as np
import pytest

from tests.integration.py.test_report_storage import REFERENCE, inventory, put, report_text, source


def command(path, *flags):
    return subprocess.run(
        [sys.executable, '-m', 'edi', 'report', str(path), *flags],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


def rows(path):
    words = shlex.split((path / 'reports/report.edi').read_text(), comments=True)
    start = words.index('_report_file.format')
    keys = []
    while start < len(words) and words[start].startswith('_report_file.'):
        keys.append(words[start].split('.', 1)[1])
        start += 1
    values = words[start:]
    end = next(
        (i for i, word in enumerate(values) if word.startswith('_') or word == 'loop_'),
        len(values),
    )
    values = values[:end]
    assert len(values) % len(keys) == 0, (
        'I36 every saved-file row has its complete declared fields'
    )
    records = [
        dict(zip(keys, values[i : i + len(keys)], strict=True))
        for i in range(0, len(values), len(keys))
    ]
    assert len({row['name'] for row in records}) == len(records), (
        'I36 names are unique saved-file row identities'
    )
    return {row['name']: row for row in records}


def fnv(text):
    value = 0xCBF29CE484222325
    for byte in text.encode():
        value = ((value ^ byte) * 0x100000001B3) & ((1 << 64) - 1)
    return f'{value:016x}'


def save_python(path):
    project = edi.Project.load(path)
    assert hasattr(project, 'report') and hasattr(project.report, 'save'), (
        'I36 Project.report.save is the Python path for the project ticked formats'
    )
    project.report.save()
    return project


def status(path, name, expected, code):
    result = command(path, '--check')
    assert result.returncode == code and re.search(
        re.escape(name) + r'\s+' + re.escape(expected), result.stdout
    ), (
        'I37 --check lists the named file as '
        + expected
        + ' with the required exit status: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize('surface', ['python', 'cli'])
def test_save_report_writes_only_ticked_formats_and_replaces_rows_by_name(tmp_path, surface):
    path = source(
        tmp_path, ['_report.html true', '_report.pdf false', '_report.html_offline false']
    )
    name = edi.Project.load(path).metadata.name
    if surface == 'python':
        save_python(path)
    else:
        result = command(path)
        assert result.returncode == 0, (
            'I36 the CLI writes the ticked HTML format: ' + result.stderr
        )
    html = path / f'reports/{name}.html'
    assert html.is_file() and not list(path.glob('reports/*.pdf')), (
        'I36 HTML alone produces HTML alone'
    )
    first = rows(path)
    assert set(first) == {name + '.html'}, (
        'I36 a first Save report records exactly the file it wrote'
    )
    entry = first[name + '.html']
    assert entry['format'] == 'html' and re.fullmatch(r'[0-9a-f]{16}', entry['digest']), (
        'I36 a saved HTML row carries its typed format and 64-bit lowercase digest'
    )
    assert re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z', entry['saved']), (
        'I36 the saved timestamp is UTC rather than local wall time'
    )
    status(path, html.name, 'current', 0)
    result = command(path)
    assert result.returncode == 0 and set(rows(path)) == set(first), (
        'I36 saving the same file replaces its row instead of appending a duplicate'
    )


@pytest.mark.parametrize('surface', ['python', 'cli'])
def test_ticked_pdf_is_named_as_app_only_and_its_existing_file_and_row_are_untouched(
    tmp_path, surface, capfd
):
    path = source(tmp_path, [])
    put(path, 'reports/report.edi', report_text(rows=[REFERENCE['rows'][1]]))
    pdf = put(path, 'reports/input.pdf', '%PDF-1.4\n%opaque existing app output\n')
    before, old_row = pdf.read_bytes(), rows(path)['input.pdf']
    if surface == 'python':
        save_python(path)
        output = ''.join(capfd.readouterr())
    else:
        result = command(path)
        assert result.returncode == 0, 'I36 an app-only PDF does not prevent the CLI HTML save'
        output = result.stdout + result.stderr
    assert 'pdf' in output.lower() and 'app' in output.lower(), (
        'I36 CLI and Python explicitly say the ticked PDF is written by the app'
    )
    assert pdf.read_bytes() == before and rows(path)['input.pdf'] == old_row, (
        'I36 a non-app export leaves every byte and field of an existing PDF untouched'
    )
    assert list(path.glob('reports/*.html')), (
        'I36 the other ticked format still writes despite PDF being app-only'
    )


def test_cli_check_ignores_legacy_options_and_has_no_rows_for_an_absent_report_file(tmp_path):
    path = source(tmp_path, [])
    record = path / 'project.edi'
    record.write_text(record.read_text() + '\n'.join(REFERENCE['legacy']) + '\n')
    before = inventory(path)
    result = command(path, '--check')
    assert result.returncode == 0 and not re.search(
        r'\.(?:html|pdf|cif)\s+(?:current|out of date|missing)', result.stdout
    ), 'I34 --check on legacy-only input succeeds and lists no saved-file row'
    assert inventory(path) == before, (
        'I37 --check is a read-only query and creates no report settings'
    )


@pytest.mark.parametrize('change', ['cell', 'embed', 'data', 'missing'])
def test_check_uses_digest_and_file_existence_instead_of_save_timestamps(tmp_path, change):
    path = source(
        tmp_path, ['_report.html true', '_report.pdf false', '_report.html_offline false']
    )
    project = save_python(path)
    name = project.metadata.name + '.html'
    entry = rows(path)[name]
    assert all(fnv(text) == expected for text, expected in REFERENCE['fnv'].items()), (
        'The independent FNV oracle reaches both published nontrivial test vectors'
    )
    text = (path / 'reports' / name).read_text()
    match = re.search(r'"generated"\s*:\s*("(?:[^"\\]|\\.)*")', text)
    assert match is not None, (
        'I37 HTML carries the generation-time field whose contents are excluded from the digest'
    )
    generated = json.loads(match[1])
    neutral = text.replace(match[1], '""', 1)
    if generated:
        neutral = neutral.replace(generated, '')
    assert entry['digest'] == fnv(neutral), (
        'I37 the actual saved HTML row uses FNV-1a of its writer text with generated empty'
    )
    project.save()
    status(path, name, 'current', 0)
    assert rows(path)[name] == entry, (
        'I35 project Save changes no saved-file timestamp or digest row'
    )
    if change == 'missing':
        (path / 'reports' / name).unlink()
    else:
        if change == 'cell':
            project.structures[0].cell.length_a.value += 0.137
        elif change == 'embed':
            project.report.html_offline = True
        else:
            project.report.excluded = []
        project.save()
    status(path, name, 'missing' if change == 'missing' else 'out of date', 1)
    assert rows(path)[name] == entry, 'I37 a stale or missing query never deletes or edits its row'
    save_python(path)
    status(path, name, 'current', 0)


def test_save_as_copied_actual_html_stays_current_and_destination_edits_do_not_stale_source(
    tmp_path,
):
    path = source(
        tmp_path, ['_report.html true', '_report.pdf false', '_report.html_offline false']
    )
    project = save_python(path)
    name = project.metadata.name + '.html'
    before = inventory(path)
    target = tmp_path / 'destination'
    project.save_as(target)
    assert inventory(path) == before, 'I35 Save as preserves the complete original project folder'
    assert inventory(target / 'reports') == inventory(path / 'reports'), (
        'I35 Save as copies the real HTML output and row byte for byte'
    )
    status(path, name, 'current', 0)
    status(target, name, 'current', 0)
    copied = edi.Project.load(target)
    copied.structures[0].cell.length_a.value += 0.137
    copied.save()
    status(target, name, 'out of date', 1)
    status(path, name, 'current', 0)


def test_failed_report_write_keeps_the_previous_row_and_every_unticked_file(tmp_path):
    path = source(tmp_path, [])
    put(path, 'reports/report.edi', report_text(rows=REFERENCE['rows']))
    name = edi.Project.load(path).metadata.name + '.html'
    directory = path / 'reports' / name
    directory.mkdir()
    put(path, f'reports/{name}/child', 'blocks replacing this directory')
    pdf = put(path, 'reports/input.pdf', 'untouched app-only bytes')
    before = rows(path)
    probe = command(path, '--check')
    assert probe.returncode == 1 and all(name in probe.stdout for name in before), (
        'I36 the failure gate first reaches the report command and every stored row, '
        'rather than accepting an unknown-command error'
    )
    result = command(path)
    assert result.returncode != 0, 'I36 writing HTML over a nonempty directory fails visibly'
    assert rows(path) == before and pdf.read_text() == 'untouched app-only bytes', (
        'I36 a failed file write leaves existing rows and unticked output bytes unchanged'
    )


@pytest.mark.parametrize('surface', ['python', 'cli'])
def test_report_saved_after_project_save_stays_current_after_reopening(tmp_path, surface):
    path = source(
        tmp_path, ['_report.html true', '_report.pdf false', '_report.html_offline false']
    )
    project = edi.Project.load(path)
    project.su_rule = 'iucr_19'
    parameter = project.experiments['bank'].background[5].intensity
    assert project.experiments['bank'].background[5].position == 72.321, (
        'The save-adoption witness uses the last authored point bordering the measured range, '
        'so its changed intensity must affect the actual calculated pattern'
    )
    parameter.value, parameter.uncertainty, parameter.free = 5.000000000000001, 0.0692616, True
    project.analysis.calculate()
    project.save()
    # Independent recommendation-12 arithmetic: ceil(.0692616/.01)=7, value -> 5.00.
    actual = (parameter.value, parameter.uncertainty)
    assert actual == (5.0, 0.07), (
        'A successful project Save adopts the file-rounded value and upward-rounded s.u. '
        f'in its already-open parameter view; actual={actual}, expected=(5.0, 0.07)'
    )
    reopened = edi.Project.load(path)
    reopened.analysis.calculate()
    assert np.array_equal(
        project.experiments['bank'].data.intensity_calc,
        reopened.experiments['bank'].data.intensity_calc,
    ), 'The open project recalculates saved values and has the exact reopened calculated pattern'
    # Use a second nontrivial value so a writer-only fix cannot pass a pattern-coherence check.
    parameter.value, parameter.uncertainty = 5.03641, 0.0692616
    project.analysis.calculate()
    before = np.array(project.experiments['bank'].data.intensity_calc, copy=True)
    project.save()
    assert (parameter.value, parameter.uncertainty) == (5.04, 0.07), (
        'The same open parameter view adopts a genuinely shifted saved value; '
        f'actual={(parameter.value, parameter.uncertainty)}, expected=(5.04, 0.07)'
    )
    reopened = edi.Project.load(path)
    reopened.analysis.calculate()
    after = np.array(project.experiments['bank'].data.intensity_calc, copy=True)
    assert not np.array_equal(before, after) and np.array_equal(
        after, reopened.experiments['bank'].data.intensity_calc
    ), 'The saved rounding shift really changes the pattern, which is exactly coherent with disk'
    name = project.metadata.name + '.html'
    if surface == 'python':
        project.report.save()
    else:
        result = command(path)
        assert result.returncode == 0, (
            'The actual CLI saves a report after project Save: ' + result.stdout + result.stderr
        )
    status(path, name, 'current', 0)
    loaded = edi.Project.load(path)
    assert (
        loaded.experiments['bank'].background[5].intensity.value,
        loaded.experiments['bank'].background[5].intensity.uncertainty,
    ) == (5.04, 0.07), 'Reopening retains the independently rounded values used to save the report'
    status(path, name, 'current', 0)
