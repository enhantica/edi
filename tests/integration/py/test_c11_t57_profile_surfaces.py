"""page/reference and edi binding seams; engine physics lives in crysta C++."""

import ast
import hashlib
import json
import re
from pathlib import Path

import edi
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / 'tests/fixtures/c11_t57_profiles'
MANIFEST = json.loads((FIXTURES / 'manifest.json').read_text())
DESTINATIONS = {
    'fcj': 'pd-neut-cwl_lab6-echidna_fcj-asymmetry',
    'beba': 'pd-neut-cwl_pbso4_beba-asymmetry',
    'tof': 'pd-neut-tof_fe_pseudo-voigt',
}
TOKENS = {
    'fcj': 'cwl-thompson-cox-hastings',
    'beba': 'cwl-pseudo-voigt-berar-baldinozzi-asymmetry',
    'tof': 'tof-pseudo-voigt',
}


@pytest.mark.parametrize('kind', [*TOKENS, 'beba_limit'])
def test_selected_profile_loads_calculates_and_survives_save(tmp_path, kind):
    limit = kind == 'beba_limit'
    kind = 'beba' if limit else kind
    text = (FIXTURES / kind / 'model.edi').read_text()
    if limit:
        text += '\n_peak.asym_beba_limit 40\n'
    structure, experiment = text.split('data_experiment', 1)
    # The native model fixture is schema-less; the edi project seam requires it.
    structure = structure.replace('data_structure\n', 'data_structure\n_edi.schema_version 3\n')
    experiment = '\n_edi.schema_version 3\n' + experiment
    (tmp_path / 'structures').mkdir()
    (tmp_path / 'experiments').mkdir()
    (tmp_path / 'structures/structure.edi').write_text(structure)
    axis = 'time_of_flight' if kind == 'tof' else 'two_theta'
    grid = np.loadtxt(FIXTURES / kind / 'reference.tsv')[::7, 0]
    experiment = (
        'data_experiment'
        + experiment
        + f'\nloop_\n_data.{axis}\n_data.intensity_meas\n_data.intensity_meas_su\n'
    )
    experiment += ''.join(f'{value:.17g} 0 1\n' for value in grid)
    (tmp_path / 'experiments/experiment.edi').write_text(experiment)
    try:
        project = edi.Project.load(tmp_path)
    except (edi.IoError, ValueError, RuntimeError) as error:
        pytest.fail(f' missing edi capability {TOKENS[kind]}: {error}')
    project.analysis.calculate()
    before = np.array(project.experiments[0].data.intensity_calc)
    assert before.shape == grid.shape and np.isfinite(before).all(), (
        ' edi must return the selected engine profile on the declared grid'
    )
    saved = tmp_path / 'saved'
    project.save_as(saved)
    emitted = '\n'.join(path.read_text() for path in (saved / 'experiments').glob('*.edi'))
    if limit:
        assert re.search(r'(?m)^_peak\.asym_beba_limit\s+40(?:\.0*)?\s*$', emitted), (
            ' save must retain the declared BeBa asymmetry limit angle'
        )
    assert TOKENS[kind] in emitted, ' save must retain the selected profile type'
    reloaded = edi.Project.load(saved)
    reloaded.analysis.calculate()
    np.testing.assert_array_equal(
        before,
        reloaded.experiments[0].data.intensity_calc,
        err_msg=' selected profile must survive the edi save/load seam',
    )


@pytest.mark.parametrize('kind', TOKENS)
def test_page_exists_with_independent_reference(kind):
    row = MANIFEST['pages'][kind]
    page = ROOT / 'docs/dev/verification' / (row['page'] + '.py')
    assert page.is_file(), ' missing capability: executable verification page ' + row['page']
    text = page.read_text()
    tree = ast.parse(text)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert any(ast.unparse(call.func).endswith('assert_patterns_agree') for call in calls), (
        ' every page must execute its reference agreement assertion'
    )
    assert not any(
        'xfail' in ast.unparse(call.func) or 'skip' in ast.unparse(call.func) for call in calls
    ), ' delivered verification pages must execute, never expected-fail or skip'
    assert 'fp2k' not in '\n'.join(ast.unparse(node) for node in tree.body), (
        ' a gate consumes committed references and must never regenerate them with fp2k'
    )
    directory = ROOT / 'knowledge/verification/fullprof' / DESTINATIONS[kind]
    for name, digest in row.get('comparison_files', row['files']).items():
        path = directory / name
        assert path.is_file(), ' missing vendored upstream reference: ' + str(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, (
            ' references must equal the declared upstream or authored AsyLim=180 artifacts'
        )
    provenance = directory / 'PROVENANCE.md'
    assert provenance.is_file() and 'diffraction-lib' in provenance.read_text(), (
        ' every independent reference must name its source'
    )
    if kind == 'beba':
        assert all(word in text.lower() for word in ('cryspy', 'fullprof', 'convention')), (
            ' BeBa page must explain its cryspy oracle and FullProf convention divergence'
        )
        comparisons = [
            ast.unparse(call).lower()
            for call in calls
            if ast.unparse(call.func).endswith('assert_patterns_agree')
        ]
        assert any('fullprof' in comparison for comparison in comparisons), (
            ' amended BeBa page must compare the fitted or mapped profile to FullProf'
        )
        assert '166' in text and 'inferred' in text.lower(), (
            ' page must qualify the FullProf differences as inferred in upstream issue 166'
        )


def test_c33_filename_difference_adds_exactly_the_owned_pages():
    # Independent pre-task filename inventory ( shipped set).
    before = {
        'pd-neut-tof_diamond_dream',
        'pd-neut-cwl_LaB6_basic',
        'pd-neut-cwl_LaB6_absorption',
        'pd-neut-cwl_LBCO_basic',
        'pd-neut-cwl_PbSO4_basic',
        'pd-neut-cwl_Y2O3_isotropic-adp',
        'pd-neut-cwl_LaB6_11B',
        'pd-neut-tof_Si_jorgensen',
        'pd-neut-tof_Si_jorgensen-von-dreele',
        'pd-neut-tof_Si_jorgensen-von-dreele-size-strain',
        'pd-neut-tof_NCAF_jorgensen-von-dreele',
    }
    expected = {row['page'] for row in MANIFEST['pages'].values()}
    after = {path.stem for path in (ROOT / 'docs/dev/verification').glob('*.py')}
    #  adds its independently gated page; preserve the  set obligation.
    after.discard('pd-xray-cwl_LiF_single')
    #  owns its added page; keep 's original page obligation exact.
    after.discard('pd-xray-cwl_LiF_single_polarization')
    after.discard('pd-neut-cwl_LBCO_preferred-orientation')
    # ADR-0078 adds its separately gated tied-Biso page; keep this task's delta exact.
    after.discard('pd-neut-cwl_cosio-d20_biso-tied')
    assert after - before == expected and before <= after, (
        ' C33 counter must derive from exactly the three owned added filenames'
    )
