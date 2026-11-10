"""Hidden  gates for the schema epoch and parameter substrate."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import edi
import pytest
from c11_t40_helpers import experiment_path, make_schema_2_project

from conftest import project_record_datetime, tree_bytes_with_normalized_project_metadata

PEAK_PARAMETERS = (
    'broad_gauss_sigma_0',
    'broad_gauss_sigma_1',
    'broad_gauss_sigma_2',
    'broad_gauss_size',
    'broad_gauss_strain',
    'broad_lorentz_gamma_0',
    'broad_lorentz_gamma_1',
    'broad_lorentz_gamma_2',
    'broad_lorentz_size',
    'broad_lorentz_strain',
    'rise_alpha_0',
    'rise_alpha_1',
    'decay_beta_0',
    'decay_beta_1',
)


def test_c11_t40_schema_two_is_a_byte_fixed_point_except_last_modified(tmp_path: Path) -> None:
    """The two-load/two-save filesystem round trip belongs in the integration tier."""
    source = make_schema_2_project(tmp_path / 'source')
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    edi.Project.load(source).save_as(first)
    edi.Project.load(first).save_as(second)
    assert tree_bytes_with_normalized_project_metadata(
        first, 'last_modified'
    ) == tree_bytes_with_normalized_project_metadata(second, 'last_modified'), (
        'successive saves must preserve every path and byte except the project record field '
        'whose contract is to advance on every successful save'
    )

    first_record = (first / 'project.edi').read_bytes()
    second_record = (second / 'project.edi').read_bytes()
    assert project_record_datetime(first_record, 'last_modified') < project_record_datetime(
        second_record, 'last_modified'
    ), 'the fixed-point exception is specific: last_modified must advance strictly on re-save'

    all_text = '\n'.join(path.read_text(encoding='utf-8') for path in sorted(first.rglob('*.edi')))
    assert '_edi.schema_version 3' in all_text, (
        'the byte fixed point must preserve the current schema epoch declaration'
    )
    for current in (
        '_peak.broad_gauss_size ',
        '_peak.broad_gauss_strain ',
        '_peak.broad_lorentz_size ',
        '_peak.broad_lorentz_strain ',
    ):
        assert current in all_text, (
            f'the fixed-point output must retain the current schema-3 peak tag {current!r}'
        )
    assert not any(
        retired in all_text
        for retired in (
            '_peak.broad_gauss_size_g',
            '_peak.broad_gauss_strain_g',
            '_peak.broad_lorentz_size_l',
            '_peak.broad_lorentz_strain_l',
        )
    ), 'the fixed-point output must not resurrect any retired schema-1 peak spelling'


def _parameters(project: Any) -> list[tuple[str, Any]]:
    found = [
        (f'structure.cell.{name}', getattr(project.structure.cell, name))
        for name in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        )
    ]
    for site in project.structure.atom_sites:
        found.extend(
            (
                f'structure.atom_sites[{site.id}].{name}',
                getattr(site, name),
            )
            for name in ('fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso')
        )
    experiment = project.experiment
    found.extend(
        (f'experiment.peak.{name}', getattr(experiment.peak, name)) for name in PEAK_PARAMETERS
    )
    found.extend(
        (f'experiment.instrument.{name}', getattr(experiment.instrument, name))
        for name in (
            'setup_twotheta_bank',
            'calib_d_to_tof_offset',
            'calib_d_to_tof_linear',
            'calib_d_to_tof_quadratic',
        )
    )
    found.append(('experiment.linked_structure.scale', experiment.linked_structure.scale))
    found.extend(
        (f'experiment.absorption.{name}', getattr(experiment.absorption, name))
        for name in ('abscor1', 'abscor2')
        if getattr(experiment.absorption, name) is not None
    )
    found.extend(
        (f'experiment.background[{index}].intensity', point.intensity)
        for index, point in enumerate(experiment.background)
    )
    return found


def _cif(adp_columns: list[tuple[str, str]]) -> str:
    tags = '\n'.join(tag for tag, _value in adp_columns)
    values = ' '.join(value for _tag, value in adp_columns)
    return (
        'data_s14\n'
        "_space_group_name_H-M_alt 'P 1'\n"
        '_cell_length_a 5.0\n'
        '_cell_length_b 5.1\n'
        '_cell_length_c 5.2\n'
        '_cell_angle_alpha 90\n'
        '_cell_angle_beta 91\n'
        '_cell_angle_gamma 92\n\n'
        'loop_\n'
        '_atom_site_label\n'
        '_atom_site_type_symbol\n'
        '_atom_site_fract_x\n'
        '_atom_site_fract_y\n'
        '_atom_site_fract_z\n'
        '_atom_site_occupancy\n'
        f'{tags}\n'
        f'Ca Ca 0.0 0.1 0.2 1.0 {values}\n'
    )


def test_c11_t40_schema_two_refuses_a_retired_peak_tag(tmp_path: Path) -> None:
    source = make_schema_2_project(tmp_path / 'retired')
    path = experiment_path(source)
    path.write_text(
        path.read_text(encoding='utf-8').replace(
            '_peak.broad_gauss_size ', '_peak.broad_gauss_size_g ', 1
        ),
        encoding='utf-8',
    )
    with pytest.raises(edi.IoError, match=r'(?i)broad_gauss_size_g'):
        edi.Project.load(source)


@pytest.mark.parametrize('version', ['1', '5'])
def test_c11_t40_loader_refuses_unsupported_schema_epoch(tmp_path: Path, version: str) -> None:
    source = make_schema_2_project(tmp_path / version)
    path = experiment_path(source)
    original = path.read_text(encoding='utf-8')
    stamped, substitutions = re.subn(
        r'^_edi\.schema_version [23]$',
        f'_edi.schema_version {version}',
        original,
        count=1,
        flags=re.MULTILINE,
    )
    assert substitutions == 1 and stamped != original, (
        'the epoch-refusal vehicle must stamp the experiment datablock the loader validates; '
        'a corpus epoch change must not turn the mutation into a no-op'
    )
    path.write_text(stamped, encoding='utf-8')
    with pytest.raises(edi.IoError, match=rf'(?i)(schema|version).*{version}'):
        edi.Project.load(source)


def test_c34_t26_loader_accepts_computed_column_schema_epoch(tmp_path: Path) -> None:
    source = make_schema_2_project(tmp_path / 'schema-four')
    path = experiment_path(source)
    original = path.read_text(encoding='utf-8')
    stamped, substitutions = re.subn(
        r'^_edi\.schema_version [23]$',
        '_edi.schema_version 4',
        original,
        count=1,
        flags=re.MULTILINE,
    )
    assert substitutions == 1, ' schema-4 acceptance must exercise the experiment file'
    path.write_text(stamped, encoding='utf-8')
    assert edi.Project.load(source) is not None, (
        ' accepts schema 4 even when its optional computed categories are absent'
    )
