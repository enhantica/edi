"""one-loader discriminator behavior across real project files."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / 'tests/fixtures/e02_t2_ncaf_5bank/project'


def _rewrite_experiment(experiment: Path, mode: str) -> None:
    text = experiment.read_text(encoding='utf-8')
    marker = 'loop_\n_data.'
    assert text.count(marker) == 1, (
        'the fit-ready source must carry exactly one measured-data loop before discrimination'
    )
    without_data = text.partition(marker)[0].rstrip() + '\n'
    range_grid = (
        '\n_data_range.time_of_flight_min 1000.5\n'
        '_data_range.time_of_flight_max 1002.0\n'
        '_data_range.time_of_flight_step 0.75\n'
    )
    if mode == 'calculation-only':
        text = without_data + range_grid
    elif mode == 'neither':
        text = without_data
    else:
        text = text.rstrip() + range_grid
    experiment.write_text(text, encoding='utf-8')


def _project_variant(tmp_path: Path, mode: str) -> tuple[Path, tuple[Path, ...], Path]:
    destination = tmp_path / mode
    shutil.copytree(PROJECT, destination)
    experiments = tuple(sorted((destination / 'experiments').glob('*.edi')))
    assert experiments, 'the  discriminator fixture must carry an experiment'
    assert mode in {'calculation-only', 'mixed', 'neither', 'both'}, (
        'the discriminator fixture mode must name one of the four project variants'
    )
    if mode == 'calculation-only':
        for experiment in experiments:
            _rewrite_experiment(experiment, mode)
    elif mode == 'mixed':
        _rewrite_experiment(experiments[0], 'calculation-only')
    else:
        _rewrite_experiment(experiments[0], mode)
    return destination, experiments, experiments[0]


def test_c11_t48_project_load_is_the_only_loader_and_accepts_fit_ready_data() -> None:
    assert not hasattr(edi.Project, 'load_complete'), (
        'the retired load_complete spelling must be absent from the Edi Project surface'
    )
    data = edi.Project.load(PROJECT).experiments[0].data
    assert data is not None, 'Project.load must accept a fit-ready measured-data project'
    assert len(data.axis()) > 0, (
        'a fit-ready Project.load must retain a non-empty measured-data axis'
    )
    assert len(data.intensity_meas) == len(data.axis()), (
        'a fit-ready Project.load must retain one measured intensity per axis point'
    )


def test_c11_t48_project_load_accepts_calculation_only_range_grid(tmp_path: Path) -> None:
    source, experiment_files, _range_file = _project_variant(tmp_path, 'calculation-only')
    project = edi.Project.load(source)
    assert len(project.experiments) == len(experiment_files), (
        'the calculation project must retain every range-only experiment in the fixture'
    )
    for experiment in project.experiments:
        data = experiment.data
        assert data is not None, 'every calculation-only range grid must load as a data node'
        assert list(data.axis()) == pytest.approx([1000.5, 1001.25, 1002.0], abs=1.0e-12), (
            'each non-trivial _data_range min/max/step must generate the declared axis'
        )
        assert len(data.intensity_meas) == len(data.intensity_meas_su) == 0, (
            'every calculation-only grid must carry no measured intensities or uncertainties'
        )
    _require_saved_profiles(project, source, tmp_path / 'saved-calculation-only')


def test_c11_t48_project_load_refuses_neither_category_and_names_file(tmp_path: Path) -> None:
    source, _experiment_files, experiment_file = _project_variant(tmp_path, 'neither')
    with pytest.raises(edi.IoError, match=re.escape(str(experiment_file))):
        edi.Project.load(source)


def test_c11_t48_project_load_refuses_both_categories(tmp_path: Path) -> None:
    source, _experiment_files, _experiment_file = _project_variant(tmp_path, 'both')
    with pytest.raises(edi.IoError, match='declares both'):
        edi.Project.load(source)


def test_c11_t48_project_load_preserves_mixed_data_and_range_project(tmp_path: Path) -> None:
    source, experiment_files, _range_file = _project_variant(tmp_path, 'mixed')
    project = edi.Project.load(source)
    assert len(project.experiments) == len(experiment_files), (
        'Mixed projects: load every measured bank and the range-only bank from the fixture'
    )
    grid = project.experiments[0].data
    assert list(grid.axis()) == pytest.approx([1000.5, 1001.25, 1002.0], abs=1.0e-12), (
        'Mixed projects: the explicitly constructed range-only bank retains its declared grid'
    )
    assert len(grid.intensity_meas) == len(grid.intensity_meas_su) == 0, (
        'Mixed projects: the range-only bank must not acquire invented measured observations'
    )
    for experiment in list(project.experiments)[1:]:
        data = experiment.data
        assert len(data.axis()) == len(data.intensity_meas) == len(data.intensity_meas_su) > 0, (
            'Mixed projects: each saved measured bank retains one intensity and sigma per point'
        )
    _require_saved_profiles(project, source, tmp_path / 'saved-mixed')


def _require_saved_profiles(project, source: Path, destination: Path) -> None:
    # Round-trip invariant, not an independent numerical reference for measured profiles.
    def profiles(value):
        return [
            (
                experiment.name,
                list(experiment.data.axis()),
                list(experiment.data.intensity_meas),
                list(experiment.data.intensity_meas_su),
            )
            for experiment in value.experiments
        ]

    before = profiles(project)
    project.save_as(destination)
    # A mixed project retains its measured banks and the range representation of its
    # calculation-only banks; the range-only assertion also applies to the mixed case.
    files = tuple(sorted((destination / 'experiments').glob('*.edi')))
    assert len(files) == len(before), 'Saving range grids must retain every experiment block'
    range_files = [
        path
        for path in files
        if '_data_range.time_of_flight_min' in path.read_text(encoding='utf-8')
    ]
    assert len(range_files) == sum(not profile[2] for profile in before), (
        'Saving mixed projects must retain a declared range for every unmeasured bank'
    )
    for path in range_files:
        text = path.read_text(encoding='utf-8')
        assert (
            '_data_range.time_of_flight_min' in text and '_data_range.time_of_flight_step' in text
        ), 'Saved calculation grids must retain their declared range representation'
        assert not re.search(r'(?m)^_data\.(?:id|intensity_meas|intensity_meas_su)\b', text), (
            'Saved calculation grids must never invent measured-data rows'
        )
    shutil.rmtree(source)
    reopened = edi.Project.load(destination)
    assert profiles(reopened) == before, (
        'Saving mixed and range-only projects: reopen every name, axis, intensity and sigma '
        'solely from the saved project after removing its original source'
    )
