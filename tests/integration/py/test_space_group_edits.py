"""Space-group identity edits select the new group's default setting."""

import edi
import pytest


@pytest.mark.parametrize('route', ['name', 'number'])
def test_changing_space_group_replaces_old_setting_and_resolves_identity(route):
    group = edi.SpaceGroup()
    group.name_h_m = 'F d -3 m'
    group.coord_system_code = '1'
    group.it_number = 227
    if route == 'name':
        group.name_h_m = 'P n m a'
    else:
        group.it_number = 62
    assert ''.join(group.name_h_m.split()) == 'Pnma', (
        'Editing either identity field must set the new Hermann-Mauguin name'
    )
    assert group.it_number == 62, 'Editing the space-group name must resolve its IT number'
    assert group.coord_system_code == 'abc', (
        'A new space group must use its own default coordinate-system code'
    )


def test_changing_only_the_setting_keeps_the_space_group_identity():
    group = edi.SpaceGroup()
    group.name_h_m = 'F d -3 m'
    group.it_number = 227
    group.coord_system_code = '1'
    group.coord_system_code = '2'
    assert ''.join(group.name_h_m.split()) == 'Fd-3m', (
        'A setting edit must preserve the space-group name'
    )
    assert group.it_number == 227, 'A setting edit must preserve the IT number'
    assert group.coord_system_code == '2', 'The chosen coordinate-system code must remain editable'
