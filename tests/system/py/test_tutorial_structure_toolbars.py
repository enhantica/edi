"""Owner 9d8a4cae6: structure controls, magnetic controls and Save image groups."""

import json
import re

import pytest
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.browser import observe_html
from tests.fixtures.tutorial_cases.contract import ROOT
from tests.fixtures.tutorial_cases.presentation import svg_documents, svg_identity
from tests.integration.py.test_tutorial_empty_project import api
from tests.integration.py.test_tutorial_report_basis import Scripts
from tests.system.py.test_tutorial_delivered_views import (
    delivered_views,  # noqa: F401 - shared real report fixture
)
from tests.system.py.test_tutorial_delivered_views import (
    test_every_delivered_view_places_save_image_rightmost_in_its_own_group as check_save_group,
)


@pytest.fixture(scope='module')
def structure_views(tmp_path_factory, delivered_views):  # noqa: F811 - shared module fixture
    folder = tmp_path_factory.mktemp('structure-toolbars')
    results = {'report-crystal': delivered_views['report']}
    for case, kind in [
        ('pd-neut-cwl_lbco-hrpt', 'crystal'),
        ('pd-neut-cwl_cosio-d20_2k', 'magnetic'),
    ]:
        project = api().Project.load(ROOT / 'docs/user/cli' / case / 'project')
        project.report.html_offline = True
        view = project.display.structure()
        parsed = Scripts(view._repr_html_())
        assert len(parsed.frames) == 1, (
            'Gate 9: the public structure display supplies its real view'
        )
        results['notebook-' + kind] = observe_html(parsed.frames[0], folder / ('notebook-' + kind))
        if kind == 'magnetic':
            results['report-' + kind] = observe_html(
                project.report.as_html(offline=True, excluded=['data', 'reflections']),
                folder / ('report-' + kind),
            )
    return results


def structure_buttons(magnetic):
    source = (ROOT / 'app/qml/Components/StructureToolbar.qml').read_text()
    result = []
    for match in re.finditer(r'ChartToolButton\s*\{(.*?)\n\s*\}', source, re.DOTALL):
        body = match[1]
        identity = re.search(r'objectName:\s*"structure.toolbar.([^"]+)"', body)
        icon = re.search(r'fontIcon:\s*"([^"]+)"', body)
        tips = re.findall(r'qsTr\("([^"]+)"\)', body)
        if not identity or not icon or not tips or identity[1] in {'save', 'saveImage'}:
            continue
        if identity[1] == 'moments' and not magnetic:
            continue
        if identity[1] == 'reset':
            result.extend({'icon': None, 'tips': ['View along ' + axis]} for axis in 'abc')
        result.append({'icon': icon[1], 'tips': tips})
    assert result, 'Gate 9: the structure toolbar is read from the independent app QML'
    return result


@pytest.mark.parametrize(
    'surface', ['report-crystal', 'notebook-crystal', 'report-magnetic', 'notebook-magnetic']
)
def test_structure_controls_order_icons_and_magnetic_controls_match_qml(surface, structure_views):
    figures = [
        item for item in structure_views[surface]['figures'] if 'structure-figure' in item['kind']
    ]
    assert len(figures) == 1 and figures[0]['canvas'], (
        'Gate 9: compare a real rendered structure view, including the magnetic case'
    )
    controls = figures[0]['controls']
    assert len(controls) >= 2 and [row['tag'] for row in controls[:2]] == ['SELECT', 'SELECT'], (
        'Gate 9: structure views begin with the app colour-scheme and atoms selectors'
    )
    assert controls[0]['options'] == ['Jmol', 'VESTA'], (
        'Gate 9: the first structure selector has the app colour schemes'
    )
    assert controls[1]['title'].startswith('Atoms:'), 'Gate 9: the second selector chooses atoms'
    magnetic = surface.endswith('magnetic')
    assert len(controls[1]['options']) == (5 if magnetic else 3), (
        'Gate 9: magnetic structures add the app magnetic atom choices'
    )
    wanted = structure_buttons(magnetic)
    buttons = [row for row in controls[2:] if row['title'] != 'Save image']
    assert len(buttons) == len(wanted), (
        'Gate 9: the structure view has the complete app control set'
    )
    references = json.loads((ROOT / 'tests/fixtures/tutorial_cases/glyphs.json').read_text())[
        'toolbar'
    ]
    for actual, expected in zip(buttons, wanted, strict=True):
        assert actual['title'] in expected['tips'], (
            'Gate 9: structure tooltips and control order match the app QML'
        )
        if expected['icon'] is None:
            assert actual['text'].strip() == expected['tips'][0][-1], (
                'Gate 9: the app axis controls draw their a, b and c letters'
            )
        else:
            icons = svg_documents(BeautifulSoup(actual['html'], 'html.parser'))
            reference = references[expected['icon']]
            assert len(icons) == 1 and svg_identity(icons[0]) == (
                reference['path_sha256'],
                reference['viewBox'],
            ), 'Gate 9: the structure toolbar uses each glyph from the shared app font'


@pytest.mark.parametrize('surface', ['notebook-crystal', 'report-magnetic', 'notebook-magnetic'])
def test_each_structure_view_has_the_separate_rightmost_save_image_group(surface, structure_views):
    check_save_group('report', {'report': structure_views[surface]})


@pytest.mark.parametrize(
    'component',
    [
        'PatternChart',
        'SingleCrystalChart',
        'CorrelationChart',
        'ScanViewChart',
        'EvolutionChart',
        'StructureView',
    ],
)
def test_every_app_view_reaches_a_save_image_control(component):
    folder = ROOT / 'app/qml/Components'
    seen = set()

    def closure(name):
        if name in seen or not (folder / (name + '.qml')).is_file():
            return ''
        seen.add(name)
        source = (folder / (name + '.qml')).read_text()
        return (
            source
            + '\n'
            + '\n'.join(closure(child) for child in re.findall(r'\b([A-Z]\w*)\s*\{', source))
        )

    source = closure(component)
    assert 'Save image' in source and 'camera' in source, (
        'Gate 9: each app chart and structure view reaches its own Save image toolbar control: '
        + component
    )
