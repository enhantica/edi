"""Latest-fit uncertainties and undo, using a small rational polynomial model."""

import importlib
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import corpus_case_dir
from tests.fixtures.saved_spelling.reference import saved_pair
from tests.integration.py.test_anisotropic_adps import loop_rows

ROOT = Path(__file__).resolve().parents[3]
ENGINE = importlib.import_module('edi')


def local_cli():
    return [sys.executable, '-m', 'edi']


def vehicle(root, mode):
    source = corpus_case_dir('constraint-covariance') / 'project'
    shutil.copytree(source, root)
    bank = root / 'experiments/bank.edi'
    measured = bank.read_text().split('_data.intensity_meas_su\n', 1)[1]
    observations = [
        tuple(map(float, line.split()[:2])) for line in measured.splitlines() if line.strip()
    ]
    if mode == 'multiphase':
        structure = root / 'structures/phase.edi'
        (root / 'structures/other.edi').write_text(
            structure.read_text().replace('data_phase', 'data_other')
        )
        bank.write_text(bank.read_text().replace('phase 0\n', 'phase 0\nother 0\n'))
    analysis = root / 'analysis/analysis.edi'
    text = analysis.read_text()
    if mode == 'joint':
        bank = root / 'experiments/bank.edi'
        (root / 'experiments/other.edi').write_text(
            bank.read_text().replace('data_bank', 'data_other')
        )
        text = text.replace('_fitting_mode.type single', '_fitting_mode.type joint')
        text += '\nloop_\n_joint_fit.experiment_id\n_joint_fit.weight\nbank 1\nother 1\n'
    if mode in {'sequential', 'independent'}:
        text = text.replace('_fitting_mode.type single', f'_fitting_mode.type {mode}')
        text += '\n_sequential_fit.data_dir experiments/scan\n_sequential_fit.file_pattern *.dat\n'
        folder = root / 'experiments/scan'
        folder.mkdir()
        for index in range(2):
            (folder / f'{index}.dat').write_text(
                'XYDATA\n' + ''.join(f'{x:.17g} {y:.17g} 1\n' for x, y in observations)
            )
    analysis.write_text(text)
    return ENGINE.Project.load(root)


def bank_experiment(project):
    return next(experiment for experiment in project.experiments if experiment.name == 'bank')


def assert_file_uncertainties(directory):
    for path in (directory / 'structures').glob('*.edi'):
        atoms = loop_rows(path.read_text(), '_atom_site')
        assert all('(' not in row['_atom_site.adp_iso'] for row in atoms), (
            'Fixed independent ADPs must be written bare without a disk uncertainty'
        )
    # The authored constraint c = a - b names bank.background.3.coef only.
    coefficients = loop_rows((directory / 'experiments/bank.edi').read_text(), '_background')
    assert '(' in coefficients[2]['_background.coef'], (
        'The authored constrained dependent must keep its propagated uncertainty as v(su) on disk'
    )


def assert_loaded_dependents(project, loaded):
    before = bank_experiment(project)
    after = bank_experiment(loaded)
    actual = after.background_terms[2].coef
    assert not actual.free, 'A saved dependent bracket must not become a free flag'
    original = before.background_terms[2].coef
    _, written_su = saved_pair(original.value, original.uncertainty)
    assert actual.uncertainty == pytest.approx(written_su, rel=5e-6), (
        'Dependent uncertainty reloads at independently derived written precision'
    )


def assert_no_su(project, *, reloaded=False):
    fixed = project.structures[0].atom_sites[0].adp_iso
    if reloaded:
        # The retained numeric grammar loads a bare fixed value with present zero s.u.
        assert fixed.uncertainty == 0.0, (
            'A bare fixed value must reload with zero s.u. under the retained numeric grammar'
        )
    else:
        assert fixed.uncertainty is None, (
            'The latest fit must clear an unrelated fixed parameter s.u. in memory'
        )
    parameters = bank_experiment(project).background_terms
    assert parameters[2].coef.uncertainty is not None, (
        'A constrained dependent must retain the uncertainty propagated from the current fit'
    )
    assert math.isfinite(parameters[2].coef.uncertainty), 'A propagated uncertainty must be finite'


@pytest.mark.parametrize('mode', ['single', 'joint', 'multiphase', 'sequential', 'independent'])
def test_every_fit_path_clears_fixed_su_and_keeps_dependent_su(tmp_path, mode):
    project = vehicle(tmp_path / 'input', mode)
    project.structures[0].atom_sites[0].adp_iso.uncertainty = 8.75
    project.analysis.fit()
    assert_no_su(project)
    project.save_as(tmp_path / 'saved')
    assert_file_uncertainties(tmp_path / 'saved')
    reopened = ENGINE.Project.load(tmp_path / 'saved')
    assert_no_su(reopened, reloaded=True)
    assert_loaded_dependents(project, reopened)
    structure = next((tmp_path / 'saved/structures').glob('*.edi')).read_text()
    assert '8.75' not in structure, (
        'Saved fixed parameters must not retain their stale uncertainty'
    )


@pytest.mark.parametrize('mode', ['single', 'joint', 'multiphase', 'sequential', 'independent'])
def test_unchecking_free_then_fitting_clears_su_and_undo_restores_it(tmp_path, mode):
    project = vehicle(tmp_path / 'input', mode)
    project.analysis.fit()
    parameter = bank_experiment(project).background_terms[0].coef
    before = parameter.uncertainty
    dependent_before = bank_experiment(project).background_terms[2].coef.uncertainty
    assert dependent_before is not None and dependent_before > 0, (
        'The prior fit must supply a nonzero propagated dependent uncertainty'
    )
    assert before is not None, 'The first fit must supply an uncertainty'
    assert before > 0, 'The first fit must supply a nonzero uncertainty'
    if mode in {'sequential', 'independent'}:
        _, before = saved_pair(parameter.value, before)
        dependent = bank_experiment(project).background_terms[2].coef
        _, dependent_before = saved_pair(dependent.value, dependent_before)
        next_scan = tmp_path / 'next-scan'
        project.save_as(next_scan)
        for ledger in (next_scan / 'analysis').glob('*.csv'):
            ledger.unlink()
        project = ENGINE.Project.load(next_scan)
        parameter = bank_experiment(project).background_terms[0].coef
        assert parameter.uncertainty == pytest.approx(before, rel=5e-6), (
            'A fresh scan input retains the prior uncertainty at independently spelled precision'
        )
    parameter.free = False
    project.analysis.fit()
    assert parameter.uncertainty is None, (
        'The next fit must clear an uncertainty after free is unchecked'
    )
    project.save_as(tmp_path / 'saved')
    reloaded = ENGINE.Project.load(tmp_path / 'saved')
    assert bank_experiment(reloaded).background_terms[0].coef.uncertainty == 0.0, (
        'A cleared fixed uncertainty must reload as zero under the retained bare-value grammar'
    )
    # Before: CLI undo saved the fixed s.u. and expected a reload to recover it.
    # After: fixed independent values serialize bare; inspect the restored live memory.
    undo = getattr(reloaded, '_undo_fit', None)
    assert callable(undo), 'The public model must expose its existing in-memory fit undo'
    undo()
    restored = bank_experiment(reloaded).background_terms[0].coef
    assert not restored.free, 'Undo must retain the fixed independent parameter state'
    assert restored.uncertainty == pytest.approx(before, rel=5e-6), (
        'Fit undo must restore the cleared fixed uncertainty in memory'
    )
    assert bank_experiment(reloaded).background_terms[2].coef.uncertainty == pytest.approx(
        dependent_before, rel=5e-6
    ), 'Undo must restore the prior propagated dependent uncertainty before it is saved as v(su)'
    reloaded.save_as(tmp_path / 'undone')
    copied = ENGINE.Project.load(tmp_path / 'undone')
    assert bank_experiment(copied).background_terms[0].coef.uncertainty == 0.0, (
        'Saving after undo must write a fixed independent value bare, omitting its live s.u.'
    )
    assert_file_uncertainties(tmp_path / 'undone')
    assert_loaded_dependents(reloaded, copied)


def test_cli_fit_clears_fixed_uncertainty_on_disk(tmp_path):
    project = vehicle(tmp_path / 'input', 'single')
    project.structures[0].atom_sites[0].adp_iso.uncertainty = 8.75
    project.save_as(tmp_path / 'cli')
    assert (
        ENGINE.Project.load(tmp_path / 'cli').structures[0].atom_sites[0].adp_iso.uncertainty
        == 0.0
    ), 'The CLI input must already write a fixed independent value bare under the file contract'
    result = subprocess.run(
        [*local_cli(), 'fit', str(tmp_path / 'cli')],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, 'The CLI must execute the same declared polynomial fit'
    assert_no_su(ENGINE.Project.load(tmp_path / 'cli'), reloaded=True)
    assert_file_uncertainties(tmp_path / 'cli')
