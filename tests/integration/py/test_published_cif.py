"""Check published CIF values and compatibility through the structure factory."""

import re
import warnings
from pathlib import Path

import edi as engine
import pytest

pytestmark = pytest.mark.filterwarnings('ignore:crysta.schema.cif_items_not_read')

FIXTURES = Path(__file__).resolve().parents[2] / 'fixtures/published_cif'
CALCITE = """data_calcite
_cell_length_a {a}
_cell_length_b {a}
_cell_length_c {c}
_cell_angle_alpha {alpha}
_cell_angle_beta {alpha}
_cell_angle_gamma {gamma}
_space_group_name_H-M_alt '{symbol}'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Ca1 Ca .137 .243 .351
"""


@pytest.mark.parametrize(
    ('suffix', 'setting', 'metric'),
    [
        (' H', 'h', (4.99, 17.06, 90, 120)),
        (' R', 'r', (6.37, 6.37, 46.1, 46.1)),
        (' :H', 'h', (4.99, 17.06, 90, 120)),
        (' :R', 'r', (6.37, 6.37, 46.1, 46.1)),
    ],
)
def test_calcite_space_group_suffix_selects_the_declared_axes(suffix, setting, metric):
    # The reported H declaration uses a space before H. The other setting and
    # its control follow International Tables for Crystallography, group 167.
    a, c, alpha, gamma = metric
    text = CALCITE.format(a=a, c=c, alpha=alpha, gamma=gamma, symbol='R -3 c' + suffix)
    structure = engine.StructureFactory.from_cif_str(text)
    assert structure.space_group.it_number == 167, 'Calcite imports as space group 167'
    assert structure.space_group.coord_system_code.lower() == setting, (
        'The declaration selects the corresponding hexagonal or rhombohedral basis'
    )
    assert structure.cell.angle_gamma.value == pytest.approx(gamma), (
        'Selecting the setting preserves the declared metric'
    )


def test_unquoted_publication_text_preserves_the_following_model_values():
    text = (FIXTURES / '1000007.cif').read_text(encoding='utf-8')
    text = text.replace(
        '_cell_length_a',
        '_chemical_name_common Y-substituted lithium and iron oxide\n_cell_length_a',
    )
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        structure = engine.StructureFactory.from_cif_str(text)
    assert any('_chemical_name_common' in str(item.message) for item in captured), (
        'Unconsumed publication text is reported under its own CIF name'
    )
    assert structure.cell.length_a.value == pytest.approx(9.73970), (
        'The unquoted prose stops at the next named CIF value'
    )
    assert structure.atom_sites['Mg'].fract_y.value == pytest.approx(0.90808), (
        'The atom loop following the prose still contains the published coordinates'
    )


def test_published_cell_and_site_values_are_preserved():
    structure = engine.StructureFactory.from_cif_path(FIXTURES / '1000003.cif')
    site = next(site for site in structure.atom_sites if site.id == 'Sr1')
    assert structure.cell.length_a.value == pytest.approx(7.9661), (
        'The cell uses the reported length from the published CIF'
    )
    assert site.fract_x.value == pytest.approx(0.8273), (
        'The strontium site retains its published fractional coordinate'
    )
    assert site.occupancy.value == 1, 'The explicit strontium occupancy is preserved'


def test_missing_occupancy_is_filled_and_reported_for_each_published_site():
    labels = {'Mg', 'Ca', 'Si', 'O1', 'O2', 'O3'}
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        structure = engine.StructureFactory.from_cif_path(FIXTURES / '1000007.cif')
    assert {site.id for site in structure.atom_sites} == labels, (
        'The six published diopside sites remain present'
    )
    assert all(site.occupancy.value == 1 for site in structure.atom_sites), (
        'A missing occupancy column supplies unit occupancy for every site'
    )
    reported = {
        site
        for item in captured
        for site in re.findall(r"site '([^']+)' occupancy = 1(?:\b|$)", str(item.message))
        if 'taken as a default' in str(item.message)
    }
    assert reported == labels, 'The import reports each site whose occupancy it supplied'
    assert structure.atom_sites['Mg'].adp_iso.value == pytest.approx(0.00393), (
        'Defaulting occupancy keeps the explicit Uiso value'
    )


def test_published_site_with_no_label_or_coordinates_is_refused_by_name():
    with pytest.raises(ValueError, match=r'_atom_site_label|_atom_site_fract_[xyz]'):
        engine.StructureFactory.from_cif_path(FIXTURES / '1010067.cif')
