"""Independent dictionary and ZIP inputs judge the real project paths."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import edi
import pytest
import yaml

from tests.conftest import crysta_reference_source, tree_bytes_with_normalized_project_metadata
from tests.fixtures.project_text.generate import classic_zip, project

ROOT = Path(__file__).resolve().parents[3]
PROJECTS = [
    'pd-neut-cwl_lbco-hrpt',
    'pd-neut-tof_ncaf-wish-5bank_start-5',
    'pd-neut-cwl_cosio-d20_scan',
    'sc-neut-tof_taurine_fit',
    'pd-neut-tof_ferrite-austenite-beer',
]


def category_metadata():
    source = crysta_reference_source() / 'data/dictionary/parameters.yaml'
    rows = yaml.safe_load(source.read_text())['categories']
    result = {}
    for row in rows:
        values = [value for value in row.values() if type(value) is int]
        assert len(values) == 1, 'The pinned dictionary declares each category presentation number'
        result[row['edi_name']] = (values[0], len(result))
    return result


def category_runs(text):
    result = []
    multiline = False
    for line in text.splitlines():
        if line.startswith(';'):
            multiline = not multiline
        if multiline:
            continue
        match = re.match(r'^(_[A-Za-z0-9_]+)\.', line)
        if match and (not result or result[-1] != match[1]):
            result.append(match[1])
    return result


@pytest.mark.parametrize('name', PROJECTS)
def test_every_saved_file_obeys_dictionary_order_and_reopen_fixed_point(tmp_path, name):
    source = ROOT / 'docs/user/cli' / name / 'project'
    assert (source / 'project.edi').is_file(), (
        'Each required reference project exists in this repo'
    )
    supplied = tmp_path / 'supplied'
    shutil.copytree(source, supplied)
    report = supplied / 'reports/report.edi'
    if not report.exists():
        report.parent.mkdir(exist_ok=True)
        report.write_text('_edi.schema_version 3\n_report.html true\n_report.pdf false\n')
    order = category_metadata()
    original = edi.Project.load(supplied)
    first, second = tmp_path / 'first', tmp_path / 'second'
    original.save_as(first)
    reached = set()
    for file in sorted(first.rglob('*.edi')):
        runs = category_runs(file.read_text())
        assert runs, 'Every saved EDI file contributes categories to the file-order check'
        assert all(category in order for category in runs), (
            'Every category the writer emits is declared by the pinned dictionary'
        )
        assert runs == sorted(runs, key=order.__getitem__), (
            'Every saved file follows presentation numbers with declaration order breaking ties'
        )
        reached.add(file.relative_to(first).parts[0])
    assert {'project.edi', 'structures', 'experiments', 'analysis', 'reports'} <= reached, (
        'The file-order witness reaches project, structure, experiment, analysis and report files'
    )
    edi.Project.load(first).save_as(second)
    assert tree_bytes_with_normalized_project_metadata(first, 'last_modified') == (
        tree_bytes_with_normalized_project_metadata(second, 'last_modified')
    ), 'Opening and saving again preserves every file after the first save in the new order'


@pytest.mark.parametrize(
    'actor',
    [
        'ProjectText::test_apply_and_single_undo',
        'ProjectText::test_invalid_edits_are_atomic',
        'ProjectText::test_everything_is_read_only',
        'ProjectText::test_syntax_colours',
        'ProjectText::test_per_structure_appearance',
        'ProjectText::test_exact_classic_archive_opens_and_saves',
        'ProjectText::test_report_is_written_inside_opened_zip',
        'ProjectText::test_report_asks_for_location',
    ],
)
def test_real_text_tab_actor(tmp_path, actor):
    source = project(tmp_path / 'project')
    if actor.endswith('test_exact_classic_archive_opens_and_saves'):
        classic_zip(tmp_path / 'classic.zip', source)
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Text-tab acceptance uses a freshly built production Qt application'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_project_text.qml'),
            '-o',
            '-,txt',
            actor,
        ],
        env={
            **os.environ,
            'EDI_PROJECT_TEXT_REFERENCE': str(tmp_path),
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
        },
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
    )
    assert result.returncode == 0, (
        'The real application satisfies its Text-tab acceptance actor: '
        + result.stdout
        + result.stderr
    )
