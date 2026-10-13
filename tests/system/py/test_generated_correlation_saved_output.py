"""Real fit completion complements the deterministic full-loop serialization witness."""

import shutil

import edi
import pytest

from tests.conftest import corpus_case_dir
from tests.fixtures.shared_correlations.freeze_saved import HERE, hashes, loop_bytes


@pytest.mark.parametrize('case', ['single', 'scan'])
def test_real_fit_emits_every_pinned_single_or_template_correlation_row(tmp_path, case):
    source = tmp_path / 'source'
    shutil.copytree(HERE / (case + '-input'), source)
    corpus_id = {'single': 'lbco-hrpt-s2', 'scan': 'cosio-d20-scan-3f'}[case]
    corpus_project = corpus_case_dir(corpus_id) / 'project'
    for directory in ['structures', 'experiments']:
        assert hashes(source / directory) == hashes(corpus_project / directory), (
            'The declared disposable fit site must retain its pinned corpus physical inputs'
        )
    assert b'_fit_parameter_correlation.' not in (source / 'analysis/analysis.edi').read_bytes(), (
        'The real generated-output witness must start without saved expected correlation rows'
    )
    project = edi.Project.load(source)
    fitted = project.fit() if case == 'single' else project.fit_sequential()
    assert fitted.status == edi.FitStatus.DONE, (
        'The original producer input must complete its genuine single or sequential fit'
    )
    destination = tmp_path / 'saved'
    project.save_as(destination)
    actual = loop_bytes((destination / 'analysis/analysis.edi').read_bytes())
    expected = (HERE / (case + '-correlations.edi')).read_bytes()
    actual_rows = [row.split() for row in actual.decode().splitlines() if ' deterministic ' in row]
    expected_rows = [
        row.split() for row in expected.decode().splitlines() if ' deterministic ' in row
    ]
    assert actual_rows and len(actual_rows) == len(expected_rows), (
        'Actual fit settlement and saving must emit every original producer pair'
    )
    for produced, pinned in zip(actual_rows, expected_rows, strict=True):
        assert produced[:4] + produced[5:] == pinned[:4] + pinned[5:], (
            'Actual generated rows must keep every id, source, ordered endpoint and template file'
        )
        # Crysta ADR-0057: SIMD/platform fit comparison; exact spelling is separately pinned
        # by the deterministic frozen numeric-state conversion and writer witness.
        wanted = float(pinned[4])
        assert abs(float(produced[4]) - wanted) <= max(5e-9 * abs(wanted), 5e-10), (
            'Actual generated coefficients must meet the declared cross-platform fit tolerance'
        )
