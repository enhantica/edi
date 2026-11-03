"""Execute the PbSO4 approximation with labelled regression pins, not parity."""

import hashlib
from contextlib import contextmanager
from dataclasses import asdict
from unittest.mock import patch

import edi
import jupytext
import nbformat
import numpy as np
import pytest
from edi import verification as verify
from nbmake.nb_run import NotebookRun
from test_xray_doublet_pages import FIXTURE, ROOT, case_data

FREE_SHAPE = (
    'broad_gauss_u',
    'broad_gauss_v',
    'broad_gauss_w',
    'mixing_eta_0',
    'mixing_eta_1',
    'asym_beba_a0',
    'asym_beba_b0',
    'asym_beba_a1',
    'asym_beba_b1',
)


def check_start(experiment):
    instrument = experiment.instrument
    assert type(instrument).__name__ == 'CwlPdXrayInstrument', (
        'The round-robin page must calculate the X-ray CW experiment'
    )
    for name, value in (
        ('setup_wavelength', 1.54056),
        ('setup_wavelength_2', 1.5444),
        ('setup_wavelength_2_to_1_ratio', 0.5),
    ):
        assert getattr(instrument, name).value == pytest.approx(value), (
            'The round-robin page must retain the independent FullProf doublet'
        )
    peak = experiment.peak
    for name in FREE_SHAPE:
        assert getattr(peak, name).free, (
            'The approximation must fit the Caglioti widths, mixing and four BeBa coefficients'
        )
    for name, value in zip(FREE_SHAPE[-4:], (0.41356, 0.0, -1.26777, 0.0), strict=True):
        assert getattr(peak, name).value == pytest.approx(value), (
            'The BeBa start must use issue 166 mapping of the independent pbsox coefficients'
        )


def reference_intensity(profile):
    lines = (FIXTURE / 'round-robin/pbsox.bac').read_text().splitlines()
    start, step = [float(value) for value in lines[0].split()[:2]]
    background = np.array([float(value) for line in lines[1:] for value in line.split()])
    grid = start + step * np.arange(len(background)) + 0.00363
    return profile[:, 1] - np.interp(profile[:, 0], grid, background)


@contextmanager
def notebook_contract():
    page = ROOT / 'docs/dev/verification/pd-xray-cwl_PbSO4_round-robin.py'
    assert page.is_file(), 'The round-robin case requires an executing verification page'
    prose = page.read_text().lower()
    assert 'regression pin' in prose and 'parity' in prose, (
        'The approximate round-robin model must label its bounds and parity exclusion'
    )
    manifest, stem, profile = case_data('round-robin')
    oracle = reference_intensity(profile)
    loader, measured = verify.load_fullprof_calc_profile, verify.set_reference_as_measured
    agreement, fit = verify.assert_patterns_agree, edi.Analysis.fit
    state = {}

    def load(project, filename, bac, zero):
        assert filename == f'{stem}.prf' and bac == f'{stem}.bac', (
            'The round-robin page must read its independent FullProf profile and background'
        )
        directory = ROOT / 'knowledge/verification/fullprof' / project
        for name, digest in manifest['files'].items():
            assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest, (
                'Every round-robin FullProf asset must retain its original external bytes'
            )
        assert 'diffraction-lib' in (directory / 'PROVENANCE.md').read_text(), (
            'The round-robin page must name the external FullProf source'
        )
        x, y = loader(project, filename, bac, zero)
        np.testing.assert_allclose(
            np.column_stack((x, y)),
            np.column_stack((profile[:, 0], oracle)),
            rtol=0,
            atol=1e-9,
            err_msg='Round-robin fitting must use the independent background-subtracted profile',
        )
        state['loaded'] = True
        return x, y

    def measure(experiment, x, y):
        state['experiment'] = experiment
        return measured(experiment, x, y)

    def fitting(analysis, *args, **kwargs):
        assert state.get('loaded'), 'The page must load its independent target before fitting'
        check_start(state['experiment'])
        result = fit(analysis, *args, **kwargs)
        state['fitted'] = True
        return result

    def compare(triples, **kwargs):
        assert state.get('fitted') and triples, 'The page must execute its fitted regression pins'
        experiment = state['experiment']
        for _label, reference, candidate in triples:
            np.testing.assert_allclose(
                reference,
                verify.restrict_to_included(experiment, oracle),
                rtol=0,
                atol=1e-9,
                err_msg='Regression pins must compare against independent FullProf intensities',
            )
            np.testing.assert_array_equal(
                candidate,
                verify.restrict_to_included(experiment, experiment.data.intensity_calc),
                err_msg='Regression pins must compare the live fitted calculation',
            )
        assert 'tolerances' in kwargs and all(
            np.isfinite(value) for value in asdict(kwargs['tolerances']).values()
        ), 'The approximate model requires explicit finite regression bounds'
        result = agreement(triples, **kwargs)
        state['compared'] = True
        return result

    with (
        patch.object(verify, 'load_fullprof_calc_profile', side_effect=load),
        patch.object(verify, 'set_reference_as_measured', side_effect=measure),
        patch.object(verify, 'assert_patterns_agree', side_effect=compare),
        patch.object(verify, 'plot_pattern_comparison'),
        patch.object(edi.Analysis, 'fit', fitting),
    ):
        yield state
    assert state.get('compared'), 'The round-robin page must reach its actual regression assertion'


def test_round_robin_page_executes_fitted_shape_and_its_regression_pins(tmp_path):
    page = ROOT / 'docs/dev/verification/pd-xray-cwl_PbSO4_round-robin.py'
    assert page.is_file(), 'The round-robin case requires an executing verification page'
    notebook = jupytext.read(page)
    original_cells = [(cell.cell_type, cell.source) for cell in notebook.cells]
    # Documentation fits execute in the same notebook kernel as the declared nbmake
    # task. The hidden system node never fits; its in-process I20 sentinel stays armed.
    # The only extra cells install operand probes and check completion. Every original
    # page cell, including the real fit and assertion, is executed without replacement.
    bootstrap = (
        'import os, sys\n'
        f'os.chdir({str(ROOT)!r})\n'
        f'sys.path.insert(0, {str(ROOT)!r})\n'
        f'sys.path.insert(0, {str(ROOT / "lib")!r})\n'
        'import edi\n'
        f'assert edi.__file__.startswith({str(ROOT)!r}), '
        '"The notebook must import the selected repository"\n'
        f'sys.path.insert(0, {str(ROOT / "tests/system/py")!r})\n'
        'from test_xray_round_robin_page import notebook_contract\n'
        '_page_contract = notebook_contract()\n'
        '_page_contract.__enter__()'
    )
    notebook.cells.insert(0, nbformat.v4.new_code_cell(bootstrap))
    notebook.cells.append(nbformat.v4.new_code_cell('_page_contract.__exit__(None, None, None)'))
    assert [(cell.cell_type, cell.source) for cell in notebook.cells[1:-1]] == original_cells, (
        'The documentation runner must execute every original page cell unchanged'
    )
    path = tmp_path / (page.stem + '.ipynb')
    nbformat.write(notebook, path)
    result = NotebookRun(path, default_timeout=10, kernel='python3').execute()
    assert result.error is None, (
        'The actual documentation notebook must reach its fitted independent operands '
        'and regression pins: ' + str(result.error)
    )
    executed = [cell for cell in result.nb.cells if cell.cell_type == 'code']
    assert all(cell.execution_count is not None for cell in executed), (
        'Every original executable page cell and the completion probe must run'
    )
