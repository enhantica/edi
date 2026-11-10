"""ADR-0108: fit retention keeps literal opaque declarations on genuine corpus data."""

import shutil

import edi as api

from tests.conftest import corpus_case_dir
from tests.fixtures.magnetic_pnma import iso_lexemes


def test_fit_retention_preserves_raw_lexemes_and_second_save(tmp_path):
    # This is the real cosio-d20-s1 corpus, copied intact apart from opaque metadata
    # and a one-iteration bound. It is a retention gate, not a fit-quality oracle.
    source = corpus_case_dir('cosio-d20-s1') / 'project'
    root = tmp_path / 'input'
    shutil.copytree(source, root)
    structures = sorted((root / 'structures').glob('*.edi'))
    assert len(structures) == 1, 'ADR-0108 this retained-record witness has one genuine structure'
    opaque, expected = iso_lexemes.declarations()
    structures[0].write_text(structures[0].read_text() + '\n' + opaque)
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text().replace(
            '_minimizer.max_iterations 1000', '_minimizer.max_iterations 1'
        )
    )
    project = api.Project.load(root)
    project.analysis.fit()
    assert list(project.structure.iso_declarations) == expected, (
        'ADR-0108 a fit result retains source lexemes instead of decoded values'
    )
    for index in range(2):
        target = tmp_path / ('saved' + str(index))
        project.save_as(target)
        saved = next((target / 'structures').glob('*.edi')).read_text()
        for token in iso_lexemes.TOKENS:
            assert '\n' + token + '\n' in saved, (
                'ADR-0108 fit-retained writer emits each independently authored token verbatim'
            )
        project = api.Project.load(target)
        assert list(project.structure.iso_declarations) == expected, (
            'ADR-0108 retained native reload distinguishes missing and literal markers'
        )
