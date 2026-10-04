"""P1: the project is the sole source of calculation and fit inputs.

This file is intentionally byte-identical in crysta and edi.  It is the
``s/crysta/edi/`` script: the checkout name selects the library, while every
model operation and assertion stays the same on both sides.

No calculated literal below claims physical correctness.  The gates use
model-declaration and physical invariants; FullProf profile agreement belongs
to P5's independently referenced notebook gate.
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from conftest import crysta_reference_source

ROOT = Path(__file__).resolve().parents[3]
LIB = importlib.import_module('edi')
SURFACE_MANIFEST = ROOT / 'data/python-surface.json'
PUBLIC_ROUTE_INVENTORY = Path(__file__).with_name('e09_t58_public_routes.txt')

MODEL_OPERATION_OPTIONS = frozenset({
    'self',
    'on_iteration',
    'on_start',
    'on_scan_start',
    'on_file_complete',
    'should_cancel',
})


def _crysta_root() -> Path:
    """Resolve the corpus producer without assuming a sibling checkout."""
    candidates = []
    override = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
    if override:
        candidates.append(Path(override).resolve().parents[1])
    candidates.extend((ROOT, crysta_reference_source()))
    for candidate in candidates:
        if (candidate / 'tests/fitting/manifest.yml').is_file():
            return candidate
    message = "the  input gates require crysta's committed fitting corpus"
    raise AssertionError(message)


def _case_project(case_id: str) -> Path:
    project = _crysta_root() / 'tests' / 'fitting' / case_id / 'project'
    assert project.is_dir(), f'missing committed corpus project {case_id!r}'
    return project


def _calculation_project(tmp_path: Path) -> Path:
    source = _crysta_root() / 'tests/fixtures/c11_t7_pbso4_fullprof/pbso4-reconstruction'
    assert source.is_dir(), 'missing committed PbSO4 calculation-only project'
    project = tmp_path / 'pbso4-calculation'
    shutil.copytree(source, project)
    structure_file = project / 'structures/pbso4_structure.edi'
    structure = structure_file.read_text(encoding='utf-8')
    quoted = structure.replace('_space_group.name_h_m P n m a', '_space_group.name_h_m "P n m a"')
    assert quoted != structure, (
        'the calculation fixture must contain the unquoted space-group spelling being normalized'
    )
    structure_file.write_text(quoted, encoding='utf-8')
    experiment_file = project / 'experiments/pbso4_experiment.edi'
    experiment = experiment_file.read_text(encoding='utf-8')
    typed_background = experiment.replace(
        'loop_\n_background.position',
        '_background.type line-segment\n\nloop_\n_background.position',
    )
    assert typed_background != experiment, (
        'the fixture must contain the background loop receiving its explicit model type'
    )
    experiment_file.write_text(typed_background, encoding='utf-8')
    return project


def _calculate(project: Any) -> list[np.ndarray]:
    """Run the reference-shaped no-argument method and read results from the model."""
    returned = project.analysis.calculate()
    assert returned is None, 'Analysis.calculate writes results into the model and returns None'
    patterns = []
    for experiment in project.experiments:
        data = experiment.data
        assert data is not None, (
            'every calculated experiment must retain model-owned data for axis and result access'
        )
        axis = np.asarray(data.axis(), dtype=np.float64)
        calculated = np.asarray(data.intensity_calc, dtype=np.float64)
        assert calculated.shape == axis.shape, (
            'model-owned calculated intensity must align one-for-one with the declared axis'
        )
        assert calculated.size > 2, (
            'the calculation fixture must exercise a non-trivial multi-point pattern'
        )
        assert np.all(np.isfinite(calculated)), (
            'model-owned calculated intensity must contain only usable finite values'
        )
        patterns.append(calculated.copy())
    return patterns


def _set_number(owner: Any, name: str, value: float) -> None:
    """Set the common model spelling across a float/Parameter representation seam."""
    current = getattr(owner, name)
    if hasattr(current, 'value'):
        current.value = value
    else:
        setattr(owner, name, value)


def _signatures(function: Any) -> str:
    while True:
        wrapped = (getattr(function, '__kwdefaults__', None) or {}).get('_entry')
        if not callable(wrapped) or wrapped is function:
            break
        function = wrapped
    entries = getattr(function, '__nb_signature__', None)
    if entries:
        return '\n'.join(str(entry[0]) for entry in entries)
    try:
        return str(inspect.signature(function))
    except (TypeError, ValueError):
        return ''


def _surface_routes() -> set[str]:
    authority = json.loads(SURFACE_MANIFEST.read_text(encoding='utf-8'))['public']
    routes = set(authority)
    routes.update(
        f'{name}.{member}'
        for name, record in authority.items()
        for member in record.get('members', [])
    )
    return routes


def _route_classifications() -> dict[str, str]:
    rows = [
        line.split('\t')
        for line in PUBLIC_ROUTE_INVENTORY.read_text(encoding='utf-8').splitlines()
        if line and not line.startswith('#')
    ]
    assert all(len(row) == 2 for row in rows), (
        'every reviewed public route must carry exactly one tab-separated classification'
    )
    classified = dict(rows)
    assert len(classified) == len(rows), (
        'the reviewed public route inventory must not hide a duplicate classification'
    )
    assert set(classified.values()) <= {'model-operation', 'other-public'}, (
        'every reviewed route must use an explicit  classification'
    )
    return classified


def _overload_parameters(overload: str) -> set[str]:
    opening = overload.find('(')
    closing = overload.find(') ->', opening)
    if closing == -1:
        closing = overload.rfind(')')
    assert opening != -1, 'every public model operation overload must open its call syntax'
    assert closing > opening, 'every public model operation overload must close its call syntax'
    raw_parameters = overload[opening + 1 : closing]
    tokens = []
    token_start = 0
    depth = 0
    for index, character in enumerate(raw_parameters):
        if character in '[(':
            depth += 1
        elif character in '])':
            depth -= 1
        elif character == ',' and depth == 0:
            tokens.append(raw_parameters[token_start:index])
            token_start = index + 1
    tokens.append(raw_parameters[token_start:])
    return {
        token.split(':', 1)[0].split('=', 1)[0].strip()
        for token in tokens
        if token.strip() not in {'', '/', '*'}
    }


def _assert_public_inventory_is_classified() -> dict[str, str]:
    discovered_routes = _surface_routes()
    classifications = _route_classifications()
    classified_routes = set(classifications)
    assert discovered_routes == classified_routes, (
        'every public name and member from the committed surface authority must have a reviewed '
        f' classification; missing={sorted(discovered_routes - classified_routes)!r}, '
        f'stale={sorted(classified_routes - discovered_routes)!r}'
    )
    return classifications


def _assert_model_operation_overloads(classifications: dict[str, str]) -> None:
    model_operations = {
        route
        for route, classification in classifications.items()
        if classification == 'model-operation'
    }
    for route in sorted(model_operations):
        owner_name, member_name = route.split('.', 1)
        operation = getattr(getattr(LIB, owner_name), member_name)
        assert callable(operation), (
            f'{route} is classified as a model operation and must remain callable'
        )
        signature = _signatures(operation)
        assert signature, f'{route} must expose inspectable overloads'
        overloads = signature.splitlines()
        assert overloads, f'{route} must retain at least one public overload'
        for overload in overloads:
            unexpected = _overload_parameters(overload) - MODEL_OPERATION_OPTIONS
            assert not unexpected, (
                f'{route} must read model state from its bound project; public overload '
                f'{overload!r} re-accepts {sorted(unexpected)!r}'
            )


def test_project_calculation_accepts_no_second_source_of_truth(tmp_path: Path) -> None:
    project = LIB.Project.load(_calculation_project(tmp_path))
    analysis = project.analysis

    rejected_calls = (
        lambda: analysis.calculate([20.0, 30.0]),
        lambda: analysis.calculate(tof_grid=[20.0, 30.0]),
        lambda: analysis.calculate(setup_twotheta_bank=144.845),
        lambda: analysis.calculate(cutoff_fwhm=0.5),
        lambda: analysis.calculate(scattering={'Pb': -37.25}),
        lambda: project.calculate([20.0, 30.0]),
    )
    for call in rejected_calls:
        with pytest.raises(TypeError):
            call()

    _calculate(project)


def _assert_packet_module_routes() -> None:
    # Packet-named non-public and retired module routes remain an independent classification
    # layer beside the complete manifest-derived public inventory above.
    forbidden_parameters = {
        'compute_pattern': ('scattering', 'tof_grid', 'setup_twotheta_bank', 'cutoff_fwhm'),
        'apply_exclusions': ('regions',),
        'fit_problem': ('max_iterations',),
    }
    required_model_parameter = {
        'compute_pattern': {'project'},
        'apply_exclusions': {'project', 'experiment'},
    }
    project_only = {'free_from_model'}
    retired = {'load_neutron_scattering'}

    public = set(LIB.__all__)
    for name in retired:
        assert name not in public, (
            f'{name} must leave the declared public surface when its alternate input route retires'
        )
        assert not hasattr(LIB, name), (
            f'{name} must be retired, not hidden behind an alias or shim'
        )

    for name, forbidden in forbidden_parameters.items():
        if not hasattr(LIB, name):
            continue
        signature = _signatures(getattr(LIB, name))
        assert signature, f'{name} must expose an inspectable signature'
        assert '*args' not in signature, f'{name} hides an input route: {signature}'
        assert '**kwargs' not in signature, f'{name} hides an input route: {signature}'
        parameter_names = {
            token.split(':', 1)[0].split('=', 1)[0].strip()
            for token in signature.replace('(', ',').split(',')
        }
        for parameter in forbidden:
            assert parameter not in parameter_names, (
                f'{name} re-accepts model state through {parameter}: {signature}'
            )
        if name in required_model_parameter:
            assert parameter_names & required_model_parameter[name], (
                f'{name} survives only when it takes the project model: {signature}'
            )

    for name in project_only:
        if LIB.__name__ == 'crysta':
            assert hasattr(LIB, name), f"{name} is crysta's existing model-only target shape"
        if not hasattr(LIB, name):
            continue
        signature = _signatures(getattr(LIB, name))
        parameters = []
        for overload in signature.splitlines():
            assert '(' in overload, (
                f'{name} must expose parseable project-only call syntax: {signature}'
            )
            assert ')' in overload, (
                f'{name} must close its parseable project-only call syntax: {signature}'
            )
            raw = overload.split('(', 1)[1].split(')', 1)[0]
            parameters.append(
                tuple(
                    token.split(':', 1)[0].split('=', 1)[0].strip()
                    for token in raw.split(',')
                    if token.strip() not in {'', '/', '*'}
                )
            )
        assert parameters, f'{name} must expose a callable project-only overload: {signature}'
        assert all(names == ('project',) for names in parameters), (
            f'the public {name} entry point must remain project-only: {signature}'
        )

    # The scalar helpers are classified for completeness but deliberately not inspected:
    # they are genuine mathematics rather than alternate routes for project state.


def test_survey_is_complete_and_model_state_cannot_reenter_signatures() -> None:
    """Derive the whole public inventory, classify it, then inspect model operations."""
    _assert_model_operation_overloads(_assert_public_inventory_is_classified())
    _assert_packet_module_routes()


def test_declared_grid_is_the_grid_that_is_calculated(tmp_path: Path) -> None:
    fine_root = _calculation_project(tmp_path)
    coarse_root = tmp_path / 'coarse'
    shutil.copytree(fine_root, coarse_root)
    experiment_file = coarse_root / 'experiments/pbso4_experiment.edi'
    source = experiment_file.read_text(encoding='utf-8')
    changed = source.replace('_data_range.two_theta_step 0.1', '_data_range.two_theta_step 0.37')
    assert changed != source, (
        'the grid fixture must contain the step replaced by the non-trivial counterfactual'
    )
    experiment_file.write_text(changed, encoding='utf-8')

    fine = LIB.Project.load(fine_root)
    coarse = LIB.Project.load(coarse_root)
    fine_pattern = _calculate(fine)[0]
    coarse_pattern = _calculate(coarse)[0]
    coarse_axis = np.asarray(coarse.experiment.data.axis(), dtype=np.float64)

    assert coarse_axis[1] - coarse_axis[0] == pytest.approx(0.37), (
        'the model-declared non-default grid step must determine the calculated axis spacing'
    )
    assert coarse_pattern.size == coarse_axis.size, (
        'the model-owned result must retain one intensity for every declared grid point'
    )
    assert coarse_pattern.size < fine_pattern.size, (
        'a coarser model-declared grid must reduce the calculated result length'
    )


def test_declared_cutoff_changes_the_computed_result(tmp_path: Path) -> None:
    project_root = _calculation_project(tmp_path)
    narrow = LIB.Project.load(project_root)
    wide = LIB.Project.load(project_root)
    _set_number(narrow.experiment.peak, 'cutoff_fwhm', 0.5)
    _set_number(wide.experiment.peak, 'cutoff_fwhm', 30.0)

    narrow_pattern = _calculate(narrow)[0]
    wide_pattern = _calculate(wide)[0]

    assert float(narrow.experiment.peak.cutoff_fwhm) == pytest.approx(0.5), (
        'the narrow calculation must retain its non-default cutoff in the project model'
    )
    assert float(wide.experiment.peak.cutoff_fwhm) == pytest.approx(30.0), (
        'the comparison calculation must retain its wide cutoff in the project model'
    )
    assert not np.array_equal(narrow_pattern, wide_pattern), (
        'changing the project declaration must change the calculation; checking the stored '
        'value alone would reproduce the original silent-divergence defect'
    )


def test_declared_scattering_map_and_default_lookup_both_reach_calculation(
    tmp_path: Path,
) -> None:
    project_root = _calculation_project(tmp_path)
    defaulted = LIB.Project.load(project_root)
    explicit = LIB.Project.load(project_root)
    counterfactual = LIB.Project.load(project_root)

    # The explicit values are the FullProf/CrysFML values declared by the PbSO4 reference page.
    explicit.structure.scattering_lengths_fm = {'Pb': 9.405, 'S': 2.847, 'O': 5.803}
    counterfactual.structure.scattering_lengths_fm = {
        **explicit.structure.scattering_lengths_fm,
        'Pb': -37.25,
    }

    default_pattern = _calculate(defaulted)[0]
    explicit_pattern = _calculate(explicit)[0]
    counterfactual_pattern = _calculate(counterfactual)[0]

    assert default_pattern.shape == explicit_pattern.shape == counterfactual_pattern.shape, (
        'defaulted and declared scattering routes must preserve the project-declared result grid'
    )
    assert not np.array_equal(explicit_pattern, counterfactual_pattern), (
        'a declared non-default scattering length must be consumed from the structure model'
    )
