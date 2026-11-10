"""Hidden acceptance gates for 's core/adapter/binding contract."""

# ruff: noqa: PLC0415
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tests.model_calculation import calculate_on_grid

ROOT = Path(__file__).resolve().parents[3]
ALLOWED_CRYSTA_HEADERS = {
    'model.hpp',
    'pattern.hpp',
    'scattering.hpp',
    'parameter.hpp',
    'symmetry.hpp',
    'partype.hpp',
    'experiment_builder.hpp',
    'reflections.hpp',
    'fit.hpp',
    'residual.hpp',
    'recompute.hpp',  # : public CachedForwardModel anchor.
    'fit_report.hpp',  # : the ratified shared machine emitter, library-owned by crysta.
    'cell_symmetry.hpp',  # : public symmetry-completion map consumed by the adapter.
}


def test_e02_parameter_state_and_nontrivial_model_round_trip() -> None:
    import edi

    assert {'Project', 'StructureFactory', 'ExperimentFactory', 'Parameter'} <= set(edi.__all__)
    parameter = edi.Parameter(7.25, uncertainty=0.125, free=True)
    assert parameter.value == 7.25
    assert parameter.uncertainty == 0.125, (
        'the public parameter uncertainty must preserve its assigned value'
    )
    assert parameter.free is True

    structure = edi.StructureFactory.from_dict({
        'cell': {
            'length_a': {'value': 7.1},
            'length_b': {'value': 8.2},
            'length_c': {'value': 9.3},
            'angle_alpha': {'value': 78.5},
            'angle_beta': {'value': 91.25},
            'angle_gamma': {'value': 103.75},
        },
        'space_group': {'name_h_m': 'F d -3 m', 'coord_system_code': '2'},
        'atom_sites': [
            {
                'id': 'Na1',
                'type_symbol': 'Na',
                'fract': [0.137, 0.281, 0.419],
                'occupancy': 0.73,
                'adp_iso': 1.27,
            }
        ],
        'scattering_lengths_fm': {'Na': 3.63},
    })
    experiment = edi.ExperimentFactory.from_dict({
        'peak': {
            'type': 'tof-jorgensen',
            'cutoff_fwhm': 17.5,
            'broad_gauss_sigma_2': {
                'value': 14.2,
                'uncertainty': 0.31,
                'free': True,
            },
        },
        'instrument': {
            'calib_d_to_tof_offset': {'value': -11.3},
            'calib_d_to_tof_linear': {'value': 20123.4},
            'calib_d_to_tof_quadratic': {'value': -1.375},
            'setup_twotheta_bank': 137.2,
        },
        'linked_structure': {'scale': {'value': 1.7}},
        'background': [[10000.0, 2.0], [50000.0, 5.0]],
    })
    project = edi.Project(name='adapter-round-trip')
    project.structure = structure
    project.experiment = experiment
    assert not hasattr(project, 'adapter_snapshot')
    assert project.structure.space_group.name_h_m == 'F d -3 m'
    assert project.structure.space_group.coord_system_code == '2'
    assert project.structure.cell.length_a.value == 7.1
    assert project.structure.atom_sites[0].fract_x.value == 0.137
    assert project.structure.scattering_lengths_fm == {'Na': 3.63}
    assert project.experiment.instrument.calib_d_to_tof_quadratic.value == -1.375
    assert project.experiment.peak.broad_gauss_sigma_2.value == 14.2
    assert project.experiment.peak.broad_gauss_sigma_2.uncertainty == 0.31, (
        'the project peak uncertainty must preserve its assigned value'
    )
    assert project.experiment.peak.broad_gauss_sigma_2.free is True
    d_spacing = 2.35
    converted_tof = (
        project.experiment.instrument.calib_d_to_tof_offset.value
        + project.experiment.instrument.calib_d_to_tof_linear.value * d_spacing
        + project.experiment.instrument.calib_d_to_tof_quadratic.value * d_spacing**2
    )
    assert converted_tof == -11.3 + 20123.4 * d_spacing - 1.375 * d_spacing**2


def test_e02_cpp_adapter_conversion_probe() -> None:
    from conftest import corpus_case_dir

    build = (
        ROOT
        / 'build'
        / ('ci-consumer' if os.environ.get('EDI_USE_CONSUMER_BUILD') == '1' else 'ci')
    )
    candidates = [
        build / 'core/e02_adapter_probe',
        build / 'core/e02_adapter_probe.exe',
        build / 'e02_adapter_probe',
        build / 'e02_adapter_probe.exe',
    ]
    probe = next((path for path in candidates if path.is_file()), None)
    assert probe is not None, (
        'core-build must compile tests/unit/cpp/e02_adapter_probe.cpp as e02_adapter_probe; '
        'give only that target core/src on its private include path'
    )
    result = subprocess.run(
        [str(probe), str(corpus_case_dir('ncaf-wish-3bank-s5') / 'project')],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_e02_nondefault_scattering_map_changes_calculation() -> None:
    import edi

    from conftest import corpus_case_dir

    project_path = corpus_case_dir('ncaf-wish-3bank-s5') / 'project'
    baseline_project = edi.Project.load(project_path)
    baseline_project.structure.scattering_lengths_fm = {
        'Na': 3.6300,
        'Ca': 4.7000,
        'Al': 3.4490,
        'F': 5.6540,
    }
    tof = np.linspace(18000.0, 76000.0, 257)
    baseline = calculate_on_grid(edi, baseline_project, tof)

    counterfactual_project = edi.Project.load(project_path)
    scattering = dict(baseline_project.structure.scattering_lengths_fm)
    scattering['Na'] = -37.25
    counterfactual_project.structure.scattering_lengths_fm = scattering
    counterfactual = calculate_on_grid(edi, counterfactual_project, tof)

    assert counterfactual.shape == baseline.shape
    assert np.array_equal(np.isnan(counterfactual), np.isnan(baseline)), (
        ' scattering edits preserve the excluded-row NaN positions'
    )
    included = ~np.isnan(baseline)
    assert included.any(), 'E02 scattering witnesses must retain included calculated points'
    assert np.max(np.abs(counterfactual[included] - baseline[included])) > 1.0, (
        'E02 the nondefault scattering map changes included intensities by more than one'
    )


def test_e02_factories_reject_nested_model_typos() -> None:
    import edi

    with pytest.raises(KeyError, match=r'cell.*alpah'):
        edi.StructureFactory.from_dict({'cell': {'alpah': 91.0}})
    with pytest.raises(KeyError, match=r'atom_site.*biso'):
        edi.StructureFactory.from_dict({
            'atom_sites': [{'id': 'Na1', 'type_symbol': 'Na', 'biso': 1.25}]
        })
    with pytest.raises(KeyError, match=r'peak.*sigam2'):
        edi.ExperimentFactory.from_dict({'peak': {'sigam2': {'value': 14.2}}})
    with pytest.raises(KeyError, match=r'parameter spec.*essd'):
        edi.ExperimentFactory.from_dict({
            'instrument': {'calib_d_to_tof_linear': {'value': 20123.4, 'essd': 0.2}}
        })
