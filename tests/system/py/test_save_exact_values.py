"""Exact symmetry constants and independent ordinary decimal-save controls."""

import importlib
import re
from fractions import Fraction
from html.parser import HTMLParser

import gemmi
import pytest

from tests.fixtures.project_save.review2 import bank_angle, ordinary_position, special_position
from tests.integration.py.test_anisotropic_adps import loop_rows

ENGINE = importlib.import_module('edi')


def number(value):
    return float(getattr(value, 'value', value))


def decimal_cell(text, tag):
    match = re.search(r'(?m)^' + re.escape(tag) + r'\s+(\S+)', text)
    assert match is not None, 'The written witness retains its independently named numeric item'
    return match[1]


class ReportRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, _attrs):
        if tag == 'tr':
            self.row = []
        elif tag in {'td', 'th'} and self.row is not None:
            self.cell = []

    def handle_data(self, text):
        if self.cell is not None:
            self.cell.append(text)

    def handle_endtag(self, tag):
        if tag in {'td', 'th'} and self.cell is not None:
            self.row.append(''.join(self.cell).strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def report_coordinates(project):
    render = project.report.as_html if hasattr(project.report, 'as_html') else project.report.html
    parser = ReportRows()
    parser.feed(render() if callable(render) else render)
    columns = next((row for row in parser.rows if {'x', 'y', 'z'} <= set(row)), None)
    assert columns is not None, 'The real HTML report exposes its fractional-coordinate columns'
    row = next((row for row in parser.rows if row and row[0] == 'A'), None)
    assert row is not None, 'The real HTML report retains the independently authored atom A'
    return [row[columns.index(name)] for name in ('x', 'y', 'z')]


@pytest.mark.parametrize('operation', ['save', 'save-as'])
@pytest.mark.parametrize('surface', ['file', 'adopted', 'reopened', 'report', 'cif'])
def test_nonterminating_special_positions_remain_exact_on_every_saved_surface(
    tmp_path, operation, surface
):
    source = special_position(tmp_path / 'input')
    project = ENGINE.Project.load(source)
    expected = [float(Fraction(1, 3)), float(Fraction(2, 3)), float(Fraction(1, 4))]
    destination = source if operation == 'save' else tmp_path / 'saved'
    project.save() if operation == 'save' else project.save_as(destination)
    if surface == 'file':
        row = loop_rows((destination / 'structures/phase.edi').read_text(), '_atom_site')[0]
        tokens = [row['_atom_site.' + name] for name in ('fract_x', 'fract_y', 'fract_z')]
        assert all('/' not in token and '(' not in token for token in tokens), (
            'Special positions remain decimal file tokens without invented uncertainties'
        )
        actual = [float(token) for token in tokens]
    elif surface in {'adopted', 'reopened'}:
        owner = project if surface == 'adopted' else ENGINE.Project.load(destination)
        atom = owner.structures['phase'].atom_sites[0]
        actual = [number(getattr(atom, name)) for name in ('fract_x', 'fract_y', 'fract_z')]
    elif surface == 'report':
        actual = [float(Fraction(token)) for token in report_coordinates(project)]
    else:
        project.report.save_cif()
        paths = list((destination / 'reports').glob('*.cif'))
        assert len(paths) == 1, 'The exact-position gate reaches one real CIF report'
        blocks = gemmi.cif.read_file(str(paths[0]))
        block = next(block for block in blocks if block.find_value('_cell.length_a'))
        actual = [
            gemmi.cif.as_number(block.find_values('_atom_site.' + name)[0])
            for name in ('fract_x', 'fract_y', 'fract_z')
        ]
    assert [value.hex() for value in actual] == [value.hex() for value in expected], (
        'Every saved surface decodes to the exact canonical International Tables '
        'thirds and quarter'
    )
    gamma = project.structures['phase'].cell.angle_gamma.value
    assert gamma.hex() == float(120).hex(), (
        'A symmetry-fixed near-integer angle adopts its exact canonical 120 degrees'
    )
    assert (
        float(
            decimal_cell((destination / 'structures/phase.edi').read_text(), '_cell.angle_gamma')
        ).hex()
        == float(120).hex()
    ), 'The file writes canonical 120 rather than near-integer computation noise'


@pytest.mark.parametrize('operation', ['save', 'save-as'])
@pytest.mark.parametrize('surface', ['file', 'adopted', 'reopened'])
def test_an_ordinary_fixed_coordinate_keeps_the_six_digit_rule(tmp_path, operation, surface):
    source = ordinary_position(tmp_path / 'input')
    project = ENGINE.Project.load(source)
    assert (
        project.structures['phase'].atom_sites[0].fract_x.value.hex() == float('0.123456789').hex()
    ), 'The ordinary fixed control starts at its exact authored precision'
    destination = source if operation == 'save' else tmp_path / 'saved'
    project.save() if operation == 'save' else project.save_as(destination)
    if surface == 'file':
        row = loop_rows((destination / 'structures/phase.edi').read_text(), '_atom_site')[0]
        actual = float(row['_atom_site.fract_x'])
    else:
        owner = project if surface == 'adopted' else ENGINE.Project.load(destination)
        actual = owner.structures['phase'].atom_sites[0].fract_x.value
    assert actual.hex() == float('0.123457').hex(), (
        'An ordinary fixed coordinate follows six significant digits '
        'rather than the symmetry exception'
    )


@pytest.mark.parametrize('operation', ['save', 'save-as'])
@pytest.mark.parametrize('surface', ['file', 'adopted', 'reopened'])
@pytest.mark.parametrize('exact', [False, True], ids=['normal', 'all-exact'])
def test_bank_angle_file_adoption_and_reopen_honor_exact_fallback(
    tmp_path, operation, surface, exact
):
    source = bank_angle(tmp_path / 'input', exact=exact)
    project = ENGINE.Project.load(source)
    destination = source if operation == 'save' else tmp_path / 'saved'
    project.save() if operation == 'save' else project.save_as(destination)
    expected = float('94.90931761529106' if exact else '94.9093')
    if surface == 'file':
        actual = float(
            decimal_cell(
                (destination / 'experiments/bank.edi').read_text(),
                '_instrument.setup_twotheta_bank',
            )
        )
    else:
        owner = project if surface == 'adopted' else ENGINE.Project.load(destination)
        actual = number(owner.experiments['bank'].instrument.setup_twotheta_bank)
    assert actual.hex() == expected.hex(), (
        'The setting is six digits normally and the exact original double '
        'in the all-exact save fallback'
    )
