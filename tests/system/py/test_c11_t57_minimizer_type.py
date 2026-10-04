"""gate 7a: declared solver fallback and lossless persistence.

Oracle: owner decision 2026-09-26. Numeric comparison is a fallback-path
invariant, not a correctness claim for the minimizer itself.
"""

import os
import re
import shlex
import shutil
import warnings
from pathlib import Path

import edi
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
CORPUS = Path(os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting'))
IMPORTS = (
    'pd-neut-tof_ncaf-wish-2bank_start-3',
    'pd-neut-tof_si-sepd_start-2',
    'pd-neut-tof_si-sepd_start-5',
    'pd-neut-cwl_lbco-hrpt_start-4',
    'pd-neut-cwl_cosio-d20_start-4',
    'pd-neut-cwl_cosio-d20_start-1',
    'pd-neut-cwl_lbco-hrpt_start-2',
)


def staged(tmp_path, token):
    path = tmp_path / 'input'
    shutil.copytree(CORPUS / 'cosio-d20-s1/project', path)
    analysis = path / 'analysis/analysis.edi'
    source = re.sub(r'(?m)^_minimizer\.(?:type|max_iterations)\s+.*\n?', '', analysis.read_text())
    source += '\n_minimizer.max_iterations 1\n'
    if token is not None:
        source += f'_minimizer.type "{token}"\n'
    analysis.write_text(source)
    return path


@pytest.mark.parametrize(
    'token', [None, 'crysta', 'lmfit (leastsq)', 'bumps', 'future-engine', 'CRYSTA']
)
def test_declared_type_fits_warns_and_round_trips(tmp_path, capfd, token):
    source = staged(tmp_path, token)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        project = edi.Project.load(source)
        project.analysis.fit()
        project.analysis.calculate()
    output = capfd.readouterr()
    diagnostics = output.out + output.err + '\n'.join(str(item.message) for item in caught)
    if token in {None, 'crysta'}:
        assert not re.search(
            r'(?i)(warn|unsupported).*minimizer|minimizer.*(warn|unsupported)', diagnostics
        ), ' absent/default minimizer must fit without an unsupported-minimizer warning'
    else:
        assert token in diagnostics and re.search(r'(?i)warn|unsupported', diagnostics), (
            ' unsupported minimizer must warn and name the written value'
        )
    actual = np.array(project.experiments[0].data.intensity_calc)
    # Refit the same initial project with an explicit default: a foreign selector
    # must not silently select a different implementation or skip fitting.
    analysis = source / 'analysis/analysis.edi'
    explicit_default = re.sub(r'(?m)^_minimizer.type.*\n?', '', analysis.read_text())
    analysis.write_text(explicit_default + '\n_minimizer.type crysta\n')
    default = edi.Project.load(source)
    default.analysis.fit()
    default.analysis.calculate()
    np.testing.assert_array_equal(
        actual,
        default.experiments[0].data.intensity_calc,
        err_msg=' fallback must execute the same crysta fit',
    )
    for index in range(2):
        saved = tmp_path / f'saved-{index}'
        project.save_as(saved)
        rows = [
            shlex.split(line)
            for line in (saved / 'analysis/analysis.edi').read_text().splitlines()
            if line.startswith('_minimizer.type')
        ]
        assert rows == ([] if token is None else [['_minimizer.type', token]]), (
            ' save must retain the declared type and must not add an absent type'
        )
        project = edi.Project.load(saved)


@pytest.mark.parametrize('project_id', IMPORTS)
def test_upstream_imports_declare_crysta(project_id):
    path = ROOT / 'docs/user/cli' / project_id / 'project/analysis/analysis.edi'
    rows = [
        shlex.split(line)
        for line in path.read_text().splitlines()
        if line.startswith('_minimizer.type')
    ]
    assert rows == [['_minimizer.type', 'crysta']], (
        ' seven diffraction-lib imports must explicitly declare the supported minimizer'
    )
