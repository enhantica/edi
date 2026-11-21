# SPDX-License-Identifier: BSD-3-Clause
"""Legacy declarations must not change the magnetic family's displacement ties.

Run with python -m pytest tests/fixtures/magnetic_family_loading/check_loader.py
--noconftest -o addopts= -q after building the native extension.
"""

import shutil
from pathlib import Path

import easydiffraction as edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'docs/user/cli/sc-neut-cwl_cosio-heidi/project/structures/cosio_2k5.edi'
COMPONENTS = ('11', '22', '33', '12', '13', '23')
VALUES = (0.003, 0.006, 0.009, 0.001, 0.002, 0.004)


def magnetic_text(declaration=''):
    text = SOURCE.read_text(encoding='utf-8')
    text = '\n'.join(line for line in text.splitlines() if not line.startswith('_space_group.'))
    text = text.replace('data_cosio_2k5\n', 'data_cosio_2k5\n' + declaration)
    return text.replace(
        'Co1 0.003() 0.003() 0.003() 0() 0() 0()',
        'Co1 0.003() 0.006() 0.009() 0.001() 0.002() 0.004()',
    )


@pytest.mark.parametrize(
    'declaration',
    [
        '',
        '_space_group.name_h_m "P n m a"\n_space_group.coord_system_code abc\n',
        '_space_group.name_h_m "P 1"\n',
        '_space_group.name_h_m "P 4/m m m"\n',
    ],
)
def test_bns_family_precedes_tensor_ties(declaration):
    structure = edi.StructureFactory.from_cif_str(magnetic_text(declaration))
    assert structure.space_group.name_h_m == 'P n m a'
    tensor = structure.atom_site_aniso[0]
    assert tuple(getattr(tensor, 'adp_' + c).value for c in COMPONENTS) == VALUES
    assert [s.wyckoff_letter for s in structure.atom_sites] == ['a', 'c', 'c', 'c', 'c', 'd']


def test_legacy_without_bns_keeps_matching_declared_family():
    text = magnetic_text('_space_group.name_h_m "P n m a"\n')
    text = '\n'.join(
        line for line in text.splitlines() if not line.startswith('_space_group_magn.')
    )
    structure = edi.StructureFactory.from_cif_str(text)
    assert structure.space_group.name_h_m == 'P n m a'
    assert structure.atom_site_aniso[0].adp_22.value == VALUES[1]


def test_missing_tensor_uses_resolved_family():
    text = magnetic_text('_space_group.name_h_m "P 1"\n')
    text = text.replace('Co1 0.003() 0.006() 0.009() 0.001() 0.002() 0.004()', '')
    structure = edi.StructureFactory.from_cif_str(text)
    tensor = next(t for t in structure.atom_site_aniso if t.id == 'Co1')
    assert tuple(getattr(tensor, 'adp_' + c).value for c in COMPONENTS) == pytest.approx(
        (0.003, 0.003, 0.003, 0, 0, 0), rel=1e-14, abs=1e-16
    )


def test_inconsistent_bns_transform_still_refuses():
    text = magnetic_text('_space_group.name_h_m "P n m a"\n')
    text += '\n_space_group_magn.transform_BNS_Pp_abc a,c,b;0,0,0\n'
    with pytest.raises(ValueError, match='BNS transform does not map'):
        edi.StructureFactory.from_cif_str(text)


def test_operators_without_table_family_still_refuse_anisotropy():
    text = magnetic_text('_space_group.name_h_m "P n m a"\n')
    # Inversion at an origin no tabulated setting holds: the BNS number cannot create a match.
    start = text.index('2 x+1/2,-y+1/2,-z+1/2,+1')
    end = text.index('\nloop_', start)
    text = text[:start] + '2 -x+1/3,-y,-z,+1\n' + text[end:]
    with pytest.raises(ValueError, match='cannot be anisotropic'):
        edi.StructureFactory.from_cif_str(text)


def test_legacy_project_calculates_and_round_trips(tmp_path):
    original = edi.Project.load(SOURCE.parents[1])
    original.calculate()
    expected = [list(bank.refln.intensity_calc) for bank in original.experiments]
    source = tmp_path / 'legacy'
    shutil.copytree(SOURCE.parents[1], source)
    (source / 'structures' / SOURCE.name).write_text(
        magnetic_text('_space_group.name_h_m "P 1"\n').replace(
            'Co1 0.003() 0.006() 0.009() 0.001() 0.002() 0.004()',
            'Co1 0.003() 0.003() 0.003() 0() 0() 0()',
        ),
        encoding='utf-8',
    )
    project = edi.Project.load(source)
    project.calculate()
    assert [list(bank.refln.intensity_calc) for bank in project.experiments] == expected
    project.save_as(tmp_path / 'saved')
    saved = (tmp_path / 'saved/structures' / SOURCE.name).read_text(encoding='utf-8')
    assert '_space_group.name_h_m' not in saved
    reopened = edi.Project.load(tmp_path / 'saved')
    reopened.calculate()
    assert [list(bank.refln.intensity_calc) for bank in reopened.experiments] == expected
