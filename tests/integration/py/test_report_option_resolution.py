"""Stored report options and per-run overrides from hand-declared project inputs."""

import json
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / 'tests/fixtures/report_options'


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.external = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('src'):
            self.external.append(dict(attrs)['src'])


def external_scripts(text):
    parser = Scripts()
    parser.feed(text)
    return parser.external


def input_project(tmp_path, graph='pairs', **items):
    path = tmp_path / graph
    shutil.copytree(FIXTURES / graph, path)
    file = path / 'project.edi'
    for key, value in items.items():
        token = value
        if isinstance(value, bool):
            token = 'true' if value else 'false'
        if isinstance(value, list):
            token = '"' + ' '.join(value) + '"'
        file.write_text(file.read_text() + f'\n_report.{key} {token}\n')
    return path


def reporter(path):
    loaded = edi.Project.load(path)
    assert hasattr(loaded, 'report'), (
        'The actual Python project exposes the stored report category and report methods'
    )
    return loaded


def document(loaded, **overrides):
    return json.loads(loaded.report.model(**overrides).to_json())


def labels(model):
    correlations = model.get('correlations')
    if correlations is None and isinstance(model.get('analysis'), dict):
        correlations = model['analysis'].get('correlations')
    assert correlations is not None, 'The report exposes the actual filtered correlation chart'
    return [name.split('.')[-2] for name in correlations['labels']]


@pytest.mark.parametrize(
    ('graph', 'threshold', 'expected'),
    [
        ('pairs', None, ['P1', 'P2', 'P3', 'P4']),
        ('pairs', 0.95, ['P1', 'P2', 'P3', 'P4']),
        ('pairs', 0.99, ['P1', 'P2']),
        ('pairs', 0.0, ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']),
        ('clique', 0.9, ['A', 'B', 'C']),
        ('clique', 0.0, ['A', 'B', 'C', 'D']),
    ],
)
def test_shared_threshold_filter_keeps_ties_and_restores_saved_selection(
    tmp_path, graph, threshold, expected
):
    items = {} if threshold is None else {'correlation_threshold': threshold}
    path = input_project(tmp_path, graph, **items)
    loaded = reporter(path)
    assert labels(document(loaded)) == expected, (
        'The report uses the hand-derived automatic or explicit strongest-correlation threshold, '
        'keeping boundary ties whole in fit order'
    )
    saved = tmp_path / 'saved'
    loaded.save_as(saved)
    assert labels(document(reporter(saved))) == expected, (
        'A saved threshold restores exactly the same correlated parameters and complete ties'
    )


def test_explicit_false_native_zero_and_empty_overrides_replace_stored_options_without_writes(
    tmp_path,
):
    path = input_project(
        tmp_path,
        graph='nontrivial',
        html_offline=True,
        x_axis='d_spacing',
        correlation_threshold=0.9,
        excluded=['reflections'],
    )
    loaded = reporter(path)
    loaded.calculate()
    original = (path / 'project.edi').read_bytes()
    stored = (
        loaded.report.html_offline,
        loaded.report.x_axis,
        loaded.report.correlation_threshold,
        list(loaded.report.excluded),
    )
    implicit = document(loaded)
    override = document(
        loaded, offline=False, x_axis='native', correlation_threshold=0.0, excluded=[]
    )
    assert labels(implicit) == ['A', 'B', 'C'], (
        'Omitted overrides retain the stored nontrivial threshold selection'
    )
    assert not external_scripts(loaded.report.as_html()), (
        'Omitted offline overrides retain embedded chart libraries'
    )
    assert 'Reflections' not in loaded.report.as_html(), (
        'The stored exclusion removes the Reflections subsection'
    )
    assert labels(override) == ['A', 'B', 'C', 'D', 'E', 'F'], (
        'An explicit zero override selects every correlated parameter rather '
        'than using stored or automatic filtering'
    )
    assert override['experiments'][0]['pattern']['x']['title'] == '2θ (°)', (
        'An explicit native override replaces a stored d-spacing axis for this run'
    )
    assert implicit['experiments'][0]['pattern']['x']['title'] == 'd (Å)', (
        'An omitted axis override retains the project-owned d-spacing option'
    )
    assert (
        loaded.report.html_offline,
        loaded.report.x_axis,
        loaded.report.correlation_threshold,
        list(loaded.report.excluded),
    ) == stored, 'Effective per-run options leave every stored project report field unchanged'
    assert (path / 'project.edi').read_bytes() == original, (
        'Resolving and building one report never writes project.edi'
    )
    out = tmp_path / 'online.html'
    loaded.report.save_html(
        out, offline=False, x_axis='native', correlation_threshold=0.0, excluded=[]
    )
    assert out.exists(), 'Explicit per-run options produce an actual HTML report file'
    text = out.read_text()
    assert external_scripts(text), (
        'An explicit false offline override produces online library references'
    )
    assert 'Reflections' in text, (
        'An empty exclusion override restores the stored excluded Reflections subsection'
    )
    assert (path / 'project.edi').read_bytes() == original, (
        'Writing HTML with overrides never rewrites the model options'
    )


def test_cli_override_flags_leave_project_options_and_bytes_unchanged(tmp_path):
    path = input_project(
        tmp_path,
        graph='nontrivial',
        html_offline=True,
        x_axis='d_spacing',
        correlation_threshold=0.9,
        excluded=['reflections'],
    )
    original = (path / 'project.edi').read_bytes()
    target = tmp_path / 'cli-online.html'
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'report',
            str(path),
            '--output',
            str(target),
            '--online',
            '--x-axis',
            'native',
            '--correlation-threshold',
            '0',
            '--include-all',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0 and target.is_file(), (
        'The CLI accepts explicit online/native/zero/include-all overrides '
        'and writes the requested report'
    )
    assert (path / 'project.edi').read_bytes() == original, (
        'The CLI report command never writes its per-run overrides into project.edi'
    )
    text = target.read_text()
    assert external_scripts(text) and 'Reflections' in text, (
        'The CLI applies false offline and empty exclusions rather than '
        'retaining the stored settings'
    )
