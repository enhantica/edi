"""Structure type and magnetic categories through rendered application controls."""

import os
from unittest import mock

import pytest

from tests.fixtures.magnetic_type.inputs import generate
from tests.integration.app.native_actor import NativeActor

CASES = [
    'a_create_defaults_to_crystal',
    'b_magnetic_cif_selects_magnetic',
    'c_switch_to_magnetic_uses_the_grey_group',
    'd_return_to_crystal_requires_confirmation',
    'e_bns_fields_are_linked_and_searchable',
    'f_setting_shows_the_nontrivial_transform',
    'g_crystal_system_is_read_only',
    'h_derived_symbols_are_read_only_on_extra',
    'i_parent_is_always_on_extra',
    'j_sites_show_the_published_wyckoff_positions_and_fit_freedom',
]
NATIVE_FILE = 'tst_magnetic_structure_type.qml'
NATIVE_SELECTORS = {
    f'test_magnetic_structure_controls[{case}]': 'MagneticStructureType::test_' + case
    for case in CASES
}


@pytest.fixture(scope='module')
def actor(request, tmp_path_factory):
    selected = [
        item.name
        for item in request.session.items
        if getattr(item, 'module', None) is request.module
    ]
    assert selected == [name for name in NATIVE_SELECTORS if name in selected], (
        'Magnetic structure actors preserve Qt function order in the shared native host'
    )
    inputs = generate(tmp_path_factory.mktemp('magnetic-types'))
    with mock.patch.dict(os.environ, {'EDI_ACCEPTANCE_REFERENCE': str(inputs)}):
        native = NativeActor(
            tmp_path_factory.mktemp('magnetic-type-owner'),
            NATIVE_FILE,
            [NATIVE_SELECTORS[name] for name in selected],
            timeout=40,
        )
        try:
            yield native
        finally:
            native.close()


@pytest.mark.parametrize('case', CASES)
def test_magnetic_structure_controls(case, actor):
    actor.run('MagneticStructureType::test_' + case)
