"""Hidden  gates for the schema epoch and parameter substrate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import edi
import pytest
from c11_t40_helpers import experiment_path, make_schema_2_case, make_schema_2_project

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
    absorption = experiment.absorption
    absorption_type = absorption.type
    if isinstance(absorption, edi.NoAbsorption):
        assert absorption_type in {None, 'none'}, (
            'the no-absorption family must retain its absent-or-none selector while walking'
        )
        assert not hasattr(absorption, 'abscor1') and not hasattr(absorption, 'abscor2'), (
            'the no-absorption family must not expose the cylinder-only abscor pair'
        )
        assert absorption.type == absorption_type, (
            'walking the no-absorption family must preserve its exact selector state'
        )
    else:
        assert isinstance(absorption, edi.CylinderHewatAbsorption), (
            'every parameter-bearing absorption must retain the registered cylinder family'
        )
        found.extend(
            (f'experiment.absorption.{name}', getattr(absorption, name))
            for name in ('abscor1', 'abscor2')
            if getattr(absorption, name) is not None
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


def test_c11_t40_every_reachable_parameter_has_surviving_metadata(
    tmp_path: Path,
) -> None:
    source = make_schema_2_project(tmp_path)
    experiment = experiment_path(source)
    cylinder_text = experiment.read_text(encoding='utf-8')
    no_absorption_text = ''.join(
        line
        for line in cylinder_text.splitlines(keepends=True)
        if not line.startswith('_absorption.')
    )
    #  F-d-ABS: parameters exist iff their typed family says so. Exercise the
    # shared cylinder fixture AND explicit/implicit none; never let fixture drift choose coverage.
    for selector, text, family, expected_count in (
        ('cylinder', cylinder_text, edi.CylinderHewatAbsorption, 46),
        ('none', no_absorption_text + '\n_absorption.type none\n', edi.NoAbsorption, 44),
        ('absent', no_absorption_text, edi.NoAbsorption, 44),
    ):
        experiment.write_text(text, encoding='utf-8')
        project = edi.Project.load(source)
        assert isinstance(project.experiment.absorption, family), (
            'each metadata walk must exercise its declared absorption family',
            selector,
        )
        parameters = _parameters(project)
        # Regression pins for the single-experiment vehicle, not correctness oracles.
        assert len(parameters) == expected_count, (
            'the metadata walker must retain all and only the parameters of its typed family',
            selector,
        )
        absorption_paths = {path for path, _ in parameters if '.absorption.' in path}
        expected_paths = (
            {'experiment.absorption.abscor1', 'experiment.absorption.abscor2'}
            if selector == 'cylinder'
            else set()
        )
        assert absorption_paths == expected_paths, (
            'only the cylinder family may contribute its complete absorption parameter pair',
            selector,
        )
        for path, parameter in parameters:
            assert isinstance(parameter, edi.Parameter), (
                'every walked parameter must retain the public Parameter type',
                path,
            )
            for attribute in ('units', 'description'):
                assert isinstance(getattr(parameter, attribute), str), (
                    'every walked parameter must retain textual metadata',
                    path,
                    attribute,
                )
            assert parameter.min_value <= parameter.max_value, (
                'every walked parameter must retain ordered bounds',
                path,
            )


def test_c11_t40_validator_fires_at_python_factory_and_file_boundaries(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    # This boundary gate needs a small valid project, not the full SEPD data set.
    malformed = make_schema_2_case(tmp_path / 'python', 'cwl_valid')
    project = edi.Project.load(malformed)
    site = project.structure.atom_sites[0]
    with pytest.raises((ValueError, TypeError), match=r'(?i)(occupancy|range|valid)'):
        site.occupancy = edi.Parameter(1.25)

    with pytest.raises((ValueError, TypeError), match=r'(?i)(length_a|range|valid)'):
        edi.StructureFactory.from_dict({'cell': {'length_a': -1.0}})

    path = next((malformed / 'structures').glob('*.edi'))
    text = path.read_text(encoding='utf-8')
    assert '_atom_site.occupancy' in text
    lines = text.splitlines()
    occupancy_index = lines.index('_atom_site.occupancy')
    first_row = next(
        index
        for index in range(occupancy_index + 1, len(lines))
        if lines[index] and not lines[index].startswith('_')
    )
    tokens = lines[first_row].split()
    loop_tags = lines[lines.index('loop_', 1) + 1 : first_row]
    column = loop_tags.index('_atom_site.occupancy')
    tokens[column] = '1.25'
    lines[first_row] = ' '.join(tokens)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    # : typed input still refuses above; saved finite values warn and survive.
    capfd.readouterr()
    loaded = edi.Project.load(malformed)
    warnings = capfd.readouterr().err
    assert (
        sum(
            'occupancy' in line and 'outside its admissible range' in line
            for line in warnings.splitlines()
        )
        == 1
    ), ' saved occupancy 1.25 emits exactly one range warning'
    assert loaded.structure.atom_sites[0].occupancy.value == 1.25, (
        ' whole-project load retains the exact out-of-range occupancy'
    )
    saved = tmp_path / 'occupancy-roundtrip'
    loaded.save_as(saved)
    capfd.readouterr()
    reopened = edi.Project.load(saved)
    assert reopened.structure.atom_sites[0].occupancy.value == 1.25, (
        ' save/reopen never clamps the saved occupancy'
    )
    assert 'occupancy' in capfd.readouterr().err, (
        ' save/reopen delivers the retained occupancy warning'
    )
    for token in ('nan', 'inf', '-inf', '1.25oops'):
        tokens[column] = token
        lines[first_row] = ' '.join(tokens)
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        with pytest.raises(edi.IoError):
            edi.Project.load(malformed)


@pytest.mark.parametrize('method_name', ['from_cif_str', 'from_cif_path'])
@pytest.mark.parametrize(
    ('name', 'columns', 'expected_value', 'expected_uncertainty'),
    [
        pytest.param(
            'b',
            [('_atom_site_B_iso_or_equiv', '0.50(2)')],
            0.5,
            0.02,
            id='b',
        ),
        pytest.param(
            'u',
            [('_atom_site_U_iso_or_equiv', '0.0050(2)')],
            # Independent cctbx-base 2025.11 adptbx.u_as_b(0.005),
            # adptbx.u_as_b(0.0002); frozen for offline testing.
            0.39478417604357435,
            0.015791367041742974,
            id='u',
        ),
        pytest.param(
            'u-without-uncertainty',
            [('_atom_site_U_iso_or_equiv', '0.005')],
            0.39478417604357435,
            0.0,
            id='u-without-uncertainty',
        ),
        pytest.param(
            'both',
            [
                ('_atom_site_B_iso_or_equiv', '0.50(2)'),
                ('_atom_site_U_iso_or_equiv', '0.009'),
            ],
            0.5,
            0.02,
            id='b-preferred-over-u',
        ),
    ],
)
def test_c11_t40_cif_adp_spellings_preserve_type_and_prefer_b(
    tmp_path: Path,
    method_name: str,
    name: str,
    columns: list[tuple[str, str]],
    expected_value: float,
    expected_uncertainty: float,
) -> None:
    text = _cif(columns)
    path = tmp_path / f'{name}.cif'
    path.write_text(text, encoding='utf-8')
    source = text if method_name == 'from_cif_str' else path
    site = getattr(edi.StructureFactory, method_name)(source).atom_sites[0]
    # Before: U-only columns implied Uiso. After: without a declared type,
    # Biso is the default and both U value and standard uncertainty convert.
    assert site.adp_type == 'Biso', (
        'an undeclared CIF site must default to Biso regardless of the B/U input spelling'
    )
    parameter = site.adp_iso
    assert parameter.value == pytest.approx(expected_value, abs=1.0e-12), (
        'undeclared U-only CIF values convert to Biso against cctbx; an explicit B column wins',
        name,
    )
    assert parameter.uncertainty == pytest.approx(expected_uncertainty, abs=1.0e-12), (
        'CIF standard uncertainty must follow the same independent U-to-B conversion as its value',
        name,
    )
