"""Template-file persistence and setter invariants from the scan declaration.

Fixture measured points come from the D20 files, parameters from the saved
model. No fitted number is used as a correctness expectation.
"""

from __future__ import annotations

import importlib
import re
import shlex
import shutil
import struct
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
        if declaration in FILES:
            experiment = project_dir / 'experiments/d20.edi'
            prefix = experiment.read_text().split('loop_\n_data.', 1)[0]
            expected = numeric_rows(project_dir / 'experiments/d20_scan' / declaration)
            experiment.write_text(
                prefix
                + 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
                + '\n'.join(' '.join(repr(value) for value in row) for row in expected)
                + '\n'
            )
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


def parameters(project, *, identity=False):
    return [
        (
            p.name,
            p.is_attached() if identity else None,
            float(p.value),
            p.uncertainty,
            p.free,
            p.units,
            p.description,
            p.min_value,
            p.max_value,
            p.start_value,
            p.start_uncertainty,
            p.user_constrained,
            p.symmetry_constrained,
        )
        for p in project.parameters
    ]


def live_data(project):
    data = project.experiments[0].data
    return list(zip(data.two_theta, data.intensity_meas, data.intensity_meas_su, strict=True))


def data_bytes(rows):
    return b''.join(struct.pack('=ddd', *row) for row in rows)


def assert_data(project, expected):
    assert data_bytes(live_data(project)) == data_bytes(expected), (
        'Template dataset: all live measured columns retain the exact source double bytes'
    )


def assert_tag(value, filename, project_dir):
    tag = Path(value)
    scan = project_dir / 'experiments/d20_scan'
    if tag.is_absolute():
        target = tag
    elif tag.parts[:2] == ('experiments', 'd20_scan'):
        target = project_dir / tag
    else:
        target = scan / tag
    assert target.resolve() == (scan / filename).resolve(), (
        'Template dataset: the full tag resolves to the selected dataset, '
        'never a same-basename outsider'
    )


def numeric_rows(path):
    rows = []
    for line in path.read_text().splitlines():
        try:
            columns = tuple(map(float, line.split()))
        except ValueError:
            continue
        if len(columns) == 3:
            # Independent ASCII import convention: diffraction-lib bragg_pd.py,
            # commit 0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf.
            x, y, sigma = columns
            rows.append((round(x, 4), y, 1.0 if sigma < 0.0001 else sigma))
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
    handles = list(project.parameters)
    before = parameters(project, identity=True)
    owner = template_owner(project)
    owner.template_file = filename
    expected = numeric_rows(FIXTURE / 'experiments/d20_scan' / filename)
    assert_data(project, expected)
    saved = tmp_path / 'saved'
    actual = serialized_data(project, saved)
    assert actual == expected, (
        'Template dataset: selection copies every measured value and uncertainty exactly'
    )
    assert all(p.is_attached() for p in handles), (
        'Template dataset: existing parameter handles remain attached'
    )
    assert parameters(project, identity=True) == before, (
        'Template dataset: selection preserves parameter identity, attributes and dependence'
    )
    assert_tag(template_tag(saved), filename, saved)
    reopened = importlib.import_module(MODULE).Project.load(saved)
    assert_tag(template_owner(reopened).template_file, filename, saved)
    assert_data(reopened, expected)
    assert parameters(reopened) == parameters(project), (
        'Template dataset: save and reopen preserve the complete persisted parameter state'
    )


OUTSIDE = [
    'missing.dat',
    '../outside.dat',
    'excluded.txt',
    'nested/' + FILES[0],
    '../other/' + FILES[0],
    './nested/../excluded.txt',
]


def readable_refusal_files(project_dir):
    source = FIXTURE / 'experiments/d20_scan' / FILES[0]
    for relative in [
        'experiments/outside.dat',
        'experiments/d20_scan/excluded.txt',
        'experiments/d20_scan/nested/' + FILES[0],
        'experiments/other/' + FILES[0],
    ]:
        destination = project_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


@pytest.mark.parametrize('outside', OUTSIDE)
def test_template_setter_refuses_files_outside_the_declared_scan_atomically(tmp_path, outside):
    project = load(tmp_path)
    readable_refusal_files(tmp_path / 'project')
    owner = template_owner(project)
    owner.template_file = FILES[1]
    handles = list(project.parameters)
    before = parameters(project, identity=True)
    data = data_bytes(live_data(project))
    selected = owner.template_file
    with pytest.raises((ValueError, RuntimeError), match=re.escape(outside)):
        owner.template_file = outside
    assert owner.template_file == selected, (
        'Template dataset: an invalid selection names the file and leaves the tag unchanged'
    )
    assert all(p.is_attached() for p in handles), (
        'Template dataset: existing parameter handles remain attached'
    )
    assert parameters(project, identity=True) == before, (
        'Template dataset: refusal preserves parameter identity and every mutable attribute'
    )
    assert data_bytes(live_data(project)) == data, (
        'Template dataset: refusal preserves all measured columns before and after save'
    )
    saved = tmp_path / 'saved'
    project.save_as(saved)
    reopened = importlib.import_module(MODULE).Project.load(saved)
    assert_tag(template_owner(reopened).template_file, FILES[1], saved)
    assert data_bytes(live_data(reopened)) == data, (
        'Template dataset: refused selections cannot corrupt the reopened data copy'
    )


def test_template_field_loads_and_legacy_projects_remain_compatible(tmp_path):
    project = load(tmp_path, FILES[1])
    assert_tag(template_owner(project).template_file, FILES[1], tmp_path / 'project')
    expected = numeric_rows(FIXTURE / 'experiments/d20_scan' / FILES[1])
    assert_data(project, expected)
    before = parameters(project)
    project.save_as(tmp_path / 'saved')
    assert_tag(template_tag(tmp_path / 'saved'), FILES[1], tmp_path / 'saved')
    reopened = importlib.import_module(MODULE).Project.load(tmp_path / 'saved')
    assert_data(reopened, expected)
    assert parameters(reopened) == before, (
        'Template dataset: field-load save and reopen preserve the template model'
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


@pytest.mark.parametrize('outside', OUTSIDE)
def test_loader_refuses_outside_template_file(tmp_path, outside):
    directory = tmp_path / 'project'
    shutil.copytree(FIXTURE, directory)
    readable_refusal_files(directory)
    analysis = directory / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text() + f'\n_sequential_fit.template_file {outside}\n')
    before = {
        p.relative_to(directory): p.read_bytes() for p in directory.rglob('*') if p.is_file()
    }
    with pytest.raises((ValueError, RuntimeError), match=re.escape(outside)):
        importlib.import_module(MODULE).Project.load(directory)
    after = {p.relative_to(directory): p.read_bytes() for p in directory.rglob('*') if p.is_file()}
    assert after == before, 'Template dataset: a refused field-load cannot rewrite project files'
