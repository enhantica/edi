"""Static app wiring checks retained while native app tests are disabled."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / 'app'


def source(path):
    text = (APP / path).read_text()
    return re.sub(r'//[^\n]*|/\*.*?\*/', '', text, flags=re.DOTALL)


def test_excluded_regions_are_in_the_basic_category_tier():
    text = source('src/category_list_model.cpp')
    assert re.search(r'QStringLiteral\("excluded_region"\)\s*,\s*\{\s*T::Basic\b', text), (
        'excluded regions must remain on the Experiment Basic tab'
    )
    page = source('qml/Pages/Experiment/ExperimentPage.qml')
    assert '"excluded_region": excludedRegionsContent' in page, (
        'the Basic category must retain its live excluded-regions editor'
    )


def test_cwl_gaussian_and_lorentzian_coefficients_have_distinct_rows():
    text = source('src/experiment_view_model.cpp')
    match = re.search(r'int peak_family\([^)]*\)\s*\{(.*?)\n\}', text, re.DOTALL)
    assert match, 'the profile row classifier must remain inspectable by the static layout gate'
    body = match.group(1)
    gaussian = re.search(r'if\s*\((.*?)\)\s*\{\s*return\s+1\s*;', body, re.DOTALL)
    assert gaussian and 'broad_gauss_' in gaussian.group(1), (
        'U, V and W must share their Gaussian row'
    )
    assert 'broad_lorentz_' not in gaussian.group(1), (
        'X and Y must not be folded into the U V W row'
    )
    assert re.search(r'if\s*\([^)]*"broad_lorentz_"[^;]*return\s+2\s*;', body, re.DOTALL), (
        'X and Y must share their separate Lorentzian row'
    )
    grid = source('qml/Components/ParameterGrid.qml')
    assert re.search(r'property int maxColumns:\s*[3-9]', grid), (
        'one row must have room for all three U V W fields'
    )
    peak = source('qml/Pages/Experiment/PeakGroup.qml')
    assert 'peakGaussian' in peak and 'peakLorentzian' in peak, (
        'the peak group must consume both live family rows'
    )


@pytest.mark.parametrize(
    ('category', 'component', 'collection'),
    [('alias', 'AliasesGroup', 'aliases'), ('constraint', 'ConstraintsGroup', 'constraints')],
)
def test_analysis_groups_read_core_rows_without_preview_data(category, component, collection):
    page = source('qml/Pages/Analysis/AnalysisPage.qml')
    assert f'"{category}"' in page and component + ' {' in page, (
        'Analysis must attach each declared relation group to its category'
    )
    group = source(f'qml/Pages/Analysis/{component}.qml')
    assert f'analysis.{collection}' in group, (
        'a relation table must consume the live analysis model'
    )
    assert not re.search(r'\bmodel\s*:\s*\[', group), (
        'preview rows must not replace a shipped table model'
    )
    adapter = source('src/analysis_view_model.cpp')
    assert f'project_.{collection}' in adapter, (
        'the analysis row model must enumerate edi core declarations'
    )
    assert not re.search(r'rows\.append\(\s*\{\s*(?:nullptr|0)\s*,', adapter), (
        'sample rows must never be injected into shipped analysis models'
    )


def test_load_warnings_reach_the_app_message_model():
    session = source('src/session.cpp')
    assert re.search(r'edi::load_project\([^;]*warnings\.append', session, re.DOTALL), (
        'project loading must collect the core warning sink into app messages'
    )
    assert re.search(r'warnings_->setMessages\(warnings\)', session), (
        'the replacement project must publish collected warnings to the Messages model'
    )


def test_preview_projects_cannot_be_bundled_as_application_resources():
    for path in (ROOT / 'app').rglob('*'):
        if path.is_file() and path.suffix in {'.qml', '.qrc', '.cmake'}:
            assert 'constraint_samples' not in path.read_text(), (
                'temporary look-check projects must not enter shipped application resources'
            )
    cmake = (ROOT / 'app/CMakeLists.txt').read_text()
    assert 'constraint_samples' not in cmake, (
        'the application packaging list must exclude the temporary relation samples'
    )
