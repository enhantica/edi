"""Browser protocol counterfactuals; actual packed-kit runs remain required for UI claims."""

import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.e04_t11_wasm.reopen import assert_documents

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    'script', ['web_saved_fit_controls.mjs', 'web_control_geometry_controls.mjs']
)
def test_saved_browser_reference_and_real_row_refuse_wrong_operands(script):
    node = shutil.which('node')
    assert node, 'Browser protocol controls must execute with the declared Node runtime'
    run = subprocess.run(
        [node, str(ROOT / 'tests/system/manual' / script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=4,
        check=False,
    )
    assert run.returncode == 0, (
        'Actual browser helpers must refuse wrong project, scientific and row-geometry operands: '
        + run.stdout
        + run.stderr
    )


def test_reopened_project_preserves_inputs_and_checks_the_written_model_calculation():
    project = b'_metadata.name sample\n_metadata.last_modified "yesterday"\n'
    structure = (
        b'loop_\n_atom_site.id\n_atom_site.fract_x\n_atom_site.fract_y\n'
        b'Al1 0.2520(3) 0.2519537810264925\n'
        b'_cell.length_a 10.250256\n_cell.length_b 10.2502559999999\n'
    )
    experiment = (
        b'_instrument.calib_d_to_tof_linear 4985.3(9)\n'
        b'loop_\n_data.id\n_data.intensity_meas\n_data.intensity_calc\n_data.calc_status\n'
        b'1 831.5585 760.5952590779875 incl\n'
    )
    before = {
        'project.edi': project,
        'analysis/analysis.edi': b'_fit_result.success true\n_fit_result.iterations 5\n',
        'structures/sample.edi': structure,
        'experiments/sample.edi': experiment,
        'README.md': b'Keep the project notes.\n',
    }
    expected = {
        **before,
        'structures/sample.edi': structure.replace(b'0.2519537810264925', b'0.252').replace(
            b'10.2502559999999', b'10.250256'
        ),
        'experiments/sample.edi': experiment.replace(b'760.5952590779875', b'761.25'),
    }
    after = {**expected, 'project.edi': project.replace(b'yesterday', b'today')}
    assert_documents(before, after, expected)
    changes = [
        ('project.edi', b'sample', b'other'),
        ('analysis/analysis.edi', b'iterations 5', b'iterations 6'),
        ('structures/sample.edi', b'0.2520(3)', b'0.2521(3)'),
        ('structures/sample.edi', b'0.2520(3)', b'0.2520(4)'),
        ('structures/sample.edi', b'0.252\n', b'0.253\n'),
        ('structures/sample.edi', b'10.250256', b'10.250257'),
        ('structures/sample.edi', b'Al1', b'Al2'),
        ('experiments/sample.edi', b'4985.3(9)', b'4985.4(9)'),
        ('experiments/sample.edi', b'831.5585', b'831.5586'),
        ('experiments/sample.edi', b'761.25', b'762.25'),
        ('experiments/sample.edi', b'761.25', b'nan'),
        ('experiments/sample.edi', b'1 831', b'2 831'),
        ('experiments/sample.edi', b'incl', b'excl'),
        ('README.md', b'notes', b'changes'),
    ]
    for name, old, new in changes:
        assert old in after[name], 'Every reopen escape must reach a saved-field operand'
        damaged = {**after, name: after[name].replace(old, new)}
        with pytest.raises(AssertionError):
            assert_documents(before, damaged, expected)
    for name in after:
        with pytest.raises(AssertionError):
            assert_documents(
                before, {key: value for key, value in after.items() if key != name}, expected
            )
    with pytest.raises(AssertionError):
        assert_documents(before, {**after, 'extra.edi': b'extra'}, expected)
    with pytest.raises(AssertionError):
        assert_documents(before, before, expected)
