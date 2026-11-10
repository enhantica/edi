"""Notebook figures retain the report model and its existing drawing module."""

import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from types import ModuleType

import pytest

from tests.integration.py.test_tutorial_empty_project import api

ROOT = Path(__file__).resolve().parents[3]


class Scripts(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.current = None
        self.scripts = []
        self.frames = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == 'iframe' and 'srcdoc' in dict(attrs):
            self.frames.append(dict(attrs)['srcdoc'])
        if tag == 'script':
            self.current = [dict(attrs), '']

    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.current is not None:
            self.scripts.append(self.current)
            self.current = None


def html(value):
    text = value if isinstance(value, str) else value._repr_html_()
    assert isinstance(text, str) and text.strip(), (
        'Notebook display must produce HTML for Jupyter and published docs'
    )
    parsed = Scripts(text)
    if parsed.frames:
        assert len(parsed.frames) == 1, 'Each notebook display must wrap exactly one report view'
        return Scripts(parsed.frames[0])
    return parsed


def model(scripts):
    candidates = [
        json.loads(text)
        for attrs, text in scripts.scripts
        if attrs.get('type') == 'application/json' and text.strip().startswith('{')
    ]
    documents = [
        value
        for value in candidates
        if value.get('schema_version') == 1 and 'experiments' in value and 'structures' in value
    ]
    assert len(documents) == 1, 'Notebook figures must consume the common versioned report model'
    return documents[0]


@pytest.mark.parametrize('case', ['pd-neut-cwl_lbco-hrpt', 'sc-neut-cwl_tb2ti2o7-heidi'])
def test_notebook_figures_share_report_data_and_drawing_code(case, monkeypatch):
    # This integration check covers report delivery without starting an optional IPython frontend.
    shell = ModuleType('IPython')
    shell.get_ipython = lambda: None
    frontend = ModuleType('IPython.display')
    frontend.display = lambda value: value
    monkeypatch.setitem(sys.modules, 'IPython', shell)
    monkeypatch.setitem(sys.modules, 'IPython.display', frontend)
    project = api().Project.load(ROOT / 'docs/user/cli' / case / 'project')
    assert hasattr(project, 'display'), (
        'Both powder and single-crystal projects need notebook displays'
    )
    report = html(project.report.as_html(offline=False, excluded=[]))
    expected = model(report)
    drawing = {text.strip() for attrs, text in report.scripts if attrs.get('type') == 'module'}
    assert drawing, (
        'The report must supply its common drawing module before comparing notebook figures'
    )
    figures = [
        ('experiments', project.display.pattern(expt_name=project.experiments[0].name)),
        ('structures', project.display.structure(struct_name=project.structures[0].name)),
        ('correlations', project.display.fit.correlations()),
    ]
    for group, figure in figures:
        rendered = html(figure)
        actual = model(rendered)
        if group == 'correlations':
            assert actual[group] == expected[group], (
                'The notebook correlation chart must retain the report correlation data'
            )
        else:
            fields = (
                ('pattern', 'single_crystal')
                if group == 'experiments'
                else ('scene', 'view', 'drawing', 'along', 'labels')
            )
            assert [item['id'] for item in actual[group]] == [
                item['id'] for item in expected[group]
            ], 'The notebook figure must retain the report experiment or structure identity'
            for displayed, reported in zip(actual[group], expected[group], strict=True):
                for field in fields:
                    assert displayed.get(field) == reported.get(field), (
                        f'The notebook {group} {field} must retain the report drawing data'
                    )
        modules = {
            text.strip() for attrs, text in rendered.scripts if attrs.get('type') == 'module'
        }
        assert drawing <= modules, (
            f'The notebook {group} must execute the same drawing code as the HTML report'
        )
