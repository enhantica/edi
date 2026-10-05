"""Template-file persistence and setter invariants from the scan declaration.

Fixture measured points come from the D20 files, parameters from the saved
model. No fitted number is used as a correctness expectation.
"""

from __future__ import annotations

import importlib
import re
import shlex
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE = 'edi'
FIXTURE = ROOT / 'tests/fixtures/scan_template/project'
FILES = ['all594687.dat', 'all594791.dat', 'all594842.dat']


def load(tmp_path, declaration=None):
    project_dir = tmp_path / 'project'
    shutil.copytree(FIXTURE, project_dir)
    if declaration is not None:
        path = project_dir / 'analysis/analysis.edi'
        path.write_text(path.read_text() + f'\n_sequential_fit.template_file {declaration}\n')
    return importlib.import_module(MODULE).Project.load(project_dir)


def template_owner(project):
    candidates = [project, project.analysis]
    for owner in list(candidates):
        if hasattr(owner, 'sequential_fit'):
            candidates.insert(0, owner.sequential_fit)
    for owner in candidates:
        if hasattr(owner, 'template_file'):
            return owner
    pytest.fail('Template dataset: the Python library must expose a template_file setter')


def parameters(project):
    return [(float(p.value), p.uncertainty, p.free) for p in project.parameters]


def numeric_rows(path):
    rows = []
    for line in path.read_text().splitlines():
        try:
            columns = tuple(map(float, line.split()))
        except ValueError:
            continue
        if len(columns) == 3:
            rows.append(columns)
    assert rows, 'Template dataset: independent measured-data files must contain numeric rows'
    return rows


def serialized_data(project, destination):
    project.save_as(destination)
    text = (destination / 'experiments/d20.edi').read_text()
    lines = text.splitlines()
    first = next(i for i, line in enumerate(lines) if line.startswith('_data.'))
    while first < len(lines) and (lines[first].startswith('_data.') or not lines[first].strip()):
        first += 1
    rows = []
    for line in lines[first:]:
        if not line.strip():
            continue
        if line.startswith(('_', 'loop_', 'data_')):
            break
        tokens = shlex.split(line)
        rows.append(tuple(map(float, tokens[:3])))
    return rows


def template_tag(destination):
    text = (destination / 'analysis/analysis.edi').read_text()
    values = [
        shlex.split(line)[1]
        for line in text.splitlines()
        if line.startswith('_sequential_fit.template_file ')
    ]
    assert len(values) == 1, 'Template dataset: save writes one template_file field'
    return values[0]


@pytest.mark.parametrize('filename', FILES)
def test_template_setter_selects_scan_data_without_changing_parameters(tmp_path, filename):
    project = load(tmp_path)
    before = parameters(project)
    owner = template_owner(project)
    owner.template_file = filename
    expected = numeric_rows(FIXTURE / 'experiments/d20_scan' / filename)
    saved = tmp_path / 'saved'
    actual = serialized_data(project, saved)
    assert actual == expected, (
        'Template dataset: selection copies every measured value and uncertainty exactly'
    )
    assert parameters(project) == before, (
        'Template dataset: selection leaves values, uncertainties and free flags unchanged'
    )
    assert Path(template_tag(saved)).name == filename, (
        'Template dataset: save names the selected dataset'
    )
    reopened = importlib.import_module(MODULE).Project.load(saved)
    assert Path(template_owner(reopened).template_file).name == filename, (
        'Template dataset: save and reopen retain the selected dataset'
    )


@pytest.mark.parametrize('outside', ['outside.dat', '../outside.dat', 'project.edi'])
def test_template_setter_refuses_files_outside_the_declared_scan_atomically(tmp_path, outside):
    project = load(tmp_path)
    owner = template_owner(project)
    owner.template_file = FILES[1]
    before = parameters(project)
    selected = owner.template_file
    with pytest.raises((ValueError, RuntimeError), match=re.escape(outside)):
        owner.template_file = outside
    assert owner.template_file == selected, (
        'Template dataset: an invalid selection names the file and leaves the template unchanged'
    )
    assert parameters(project) == before, 'Template dataset: refusal preserves every parameter'


def test_template_field_loads_and_legacy_projects_remain_compatible(tmp_path):
    project = load(tmp_path, FILES[1])
    assert Path(template_owner(project).template_file).name == FILES[1], (
        'Template dataset: the loader reads the new field from the analysis block'
    )
    project.save_as(tmp_path / 'saved')
    assert Path(template_tag(tmp_path / 'saved')).name == FILES[1], (
        'Template dataset: a loaded declaration survives serialization'
    )


def test_legacy_scan_without_template_field_preserves_model(tmp_path):
    project = load(tmp_path)
    before = parameters(project)
    saved = tmp_path / 'saved'
    project.save_as(saved)
    reopened = importlib.import_module(MODULE).Project.load(saved)
    assert parameters(reopened) == before, (
        'Template dataset: files without the optional template selection retain their model'
    )


def test_loader_refuses_outside_template_file(tmp_path):
    with pytest.raises((ValueError, RuntimeError), match=r'outside\.dat'):
        load(tmp_path, 'outside.dat')
