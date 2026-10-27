"""Independent Python formatting reaches real report, repr and persistence consumers."""

import json
import re
import shutil
from pathlib import Path

import edi
import pytest

from tests.fixtures.dictionary_display.constrained import project_input
from tests.fixtures.dictionary_display.reference import display

ROOT = Path(__file__).resolve().parents[3]
INPUT = ROOT / 'tests/fixtures/loop_parameter_ids/line-segment'


def model(tmp_path):
    source = tmp_path / 'input'
    shutil.copytree(INPUT, source)
    experiment = source / 'experiments/bank.edi'
    experiment.write_text(
        experiment.read_text() + '\n_absorption.type cylinder-hewat\n_absorption.mu_r 0.0361\n'
    )
    return edi.Project.load(source)


@pytest.mark.parametrize(
    ('member', 'value', 'digits'),
    [
        ('length_a', 3.890915, 4),
        ('length_b', 4.12345678, 4),
        ('angle_beta', 91.234567, 3),
    ],
)
def test_python_repr_and_report_share_the_dictionary_format(tmp_path, member, value, digits):
    project = model(tmp_path)
    parameter = getattr(project.structures['phase'].cell, member)
    parameter.value = value
    expected = format(value, f'.{digits}f')
    token = re.compile(r'(?<![0-9.])' + re.escape(expected) + r'(?![0-9.eE])')
    assert token.search(repr(parameter)), (
        'Python parameter repr uses the complete dictionary-formatted token'
    )
    document = json.loads(project.report.model().to_json())
    category = next(row for row in document['structures'][0]['categories'] if row['id'] == 'cell')
    label = {'length_a': 'a', 'length_b': 'b', 'angle_beta': 'β'}[member]
    row = next(row for row in category['rows'] if row['label'] == label)
    assert row['text'] == expected, (
        'The report model cell row has the exact independent Python format'
    )
    assert token.search(project.report.as_html()), (
        'The HTML consumer retains the complete dictionary-formatted token'
    )
    assert parameter.value == value, (
        'Rendering in every Python and report consumer leaves the stored double unchanged'
    )


def test_display_operations_never_change_saved_scientific_bytes(tmp_path):
    model(tmp_path)
    source = tmp_path / 'input'
    record = source / 'project.edi'
    # Both independent saves advance the same future input clock by exactly one second.
    # This controls the writer's clock without masking even one saved byte.
    record.write_text(
        record.read_text()
        + (
            '\n_metadata.created "01 Jan 2099 00:00:00"\n'
            '_metadata.last_modified "01 Jan 2099 00:00:00"\n'
        )
    )
    control = edi.Project.load(source)
    project = edi.Project.load(source)
    for owner in [control, project]:
        owner.structures['phase'].cell.length_a.value = 3.890915
        owner.calculate()
    before = tmp_path / 'before'
    after = tmp_path / 'after'
    control.save_as(before)
    parameter = project.structures['phase'].cell.length_a
    original = parameter.value
    repr(parameter)
    project.report.model().to_json()
    project.report.as_html()
    assert parameter.value.hex() == original.hex(), (
        'Display never feeds rounded text back into its parameter before Save'
    )
    project.save_as(after)
    left = {p.relative_to(before): p.read_bytes() for p in before.rglob('*.edi')}
    right = {p.relative_to(after): p.read_bytes() for p in after.rglob('*.edi')}
    assert left == right, 'Display operations preserve every saved file byte and path'
    assert parameter.value.hex() == float('3.89092').hex(), (
        'Save adopts the fixed input 3.890915 rounded independently to six significant digits'
    )


def test_constrained_value_without_su_saves_without_binary_noise(tmp_path):
    project = edi.Project.load(project_input(tmp_path / 'input'))
    project.analysis.calculate()
    assert project.structures['phase'].atom_sites['B'].occupancy.value == pytest.approx(0.42), (
        'The independent complement constraint really reaches the dependent occupancy'
    )
    destination = tmp_path / 'saved'
    project.save_as(destination)
    text = (destination / 'structures/phase.edi').read_text()
    line = next(line for line in text.splitlines() if line.startswith('B '))
    assert '0.42000000000000004' not in line, (
        'A dependent occupancy is written with fifteen significant digits'
    )
    assert ' 0.42 ' in line, (
        'The constrained complement is actually written in its noise-free spelling'
    )
    document = json.loads(project.report.model().to_json())
    assert document['structures'], 'The persistence witness also reaches a real structure report'


@pytest.mark.parametrize(
    ('rule', 'value', 'su', 'expected', 'report_expected'),
    [
        ('iucr_19', 1.54249, 0.01532, '1.542(16)', '1.542(16)'),
        ('iucr_19', 2.16352, 0.00481, '2.164(5)', '2.164(5)'),
        ('iucr_99', 2.16352, 0.00481, '2.1635(49)', '2.164(5)'),
    ],
)
@pytest.mark.parametrize('surface', ['repr', 'model', 'html'])
def test_repr_follows_project_rule_and_report_always_uses_iucr(
    tmp_path, rule, value, su, expected, report_expected, surface
):
    source = tmp_path / 'input'
    shutil.copytree(INPUT, source)
    metadata = source / 'project.edi'
    metadata.write_text(metadata.read_text() + '\n_su_format.rule ' + rule + '\n')
    project = edi.Project.load(source)
    parameter = project.structures['phase'].cell.length_a
    parameter.value = value
    parameter.uncertainty = su
    parameter.free = True
    if surface == 'repr':
        assert expected in repr(parameter), (
            'Python repr follows the selected project IUCr uncertainty rule'
        )
    elif surface == 'model':
        assert report_expected in project.report.model().to_json(), (
            'The report model always uses the IUCr worked-example spelling'
        )
    else:
        assert report_expected in project.report.as_html(), (
            'The HTML report always uses IUCr even when the project selects two uncertainty digits'
        )


@pytest.mark.parametrize(
    ('uid', 'value', 'kind', 'digits'),
    [
        ('cell.length_a', 3.890915, 'fixed', 4),
        ('atom_site.fract_x', 0.33333, 'fixed', 5),
        ('atom_site.occupancy', 0.5823456, 'fixed', 4),
        ('instrument.setup_wavelength', 1.49412345, 'fixed', 5),
        ('linked_structure.scale', 1234567.8, 'significant', 5),
        ('background.intensity', 0.000012345678, 'significant', 5),
        ('peak.broad_gauss_u', 0.123456789, 'significant', 5),
        ('absorption.mu_r', 0.036123456, 'fixed', 4),
        ('preferred_orientation.march_r', 0.923456, 'fixed', 4),
    ],
)
def test_every_numeric_category_reaches_repr_report_and_html(tmp_path, uid, value, kind, digits):
    project = model(tmp_path)
    structure = project.structures['phase']
    experiment = project.experiments['bank']
    category, member = uid.split('.')
    owners = {
        'cell': structure.cell,
        'atom_site': structure.atom_sites['A'],
        'instrument': experiment.instrument,
        'linked_structure': experiment.linked_structures['phase'],
        'background': experiment.background[0],
        'peak': experiment.peak,
        'absorption': experiment.absorption,
        'preferred_orientation': experiment.preferred_orientation['phase'],
    }
    parameter = getattr(owners[category], member)
    parameter.value = value
    parameter.uncertainty = None
    parameter.free = False
    expected = display(value, kind, digits)
    token = re.compile(r'(?<![0-9.])' + re.escape(expected) + r'(?![0-9.eE])')
    assert token.search(repr(parameter)), (
        'Each numeric category reaches the complete independently formatted repr token'
    )
    document = json.loads(project.report.model().to_json())
    parts = (
        document['structures'] if category in {'cell', 'atom_site'} else document['experiments']
    )
    categories = [
        group for part in parts for group in part['categories'] if group['id'] == category
    ]
    assert categories, 'Every displayed numeric category has its own report category'
    assert token.search(json.dumps(categories, ensure_ascii=False)), (
        'The corresponding report category contains its independently formatted token'
    )
    assert token.search(project.report.as_html()), (
        'Each numeric category reaches its complete independently formatted HTML token'
    )
    assert parameter.value == value, 'The consumer chain preserves every original input double'
