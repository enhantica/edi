"""Owner amendments: library-input controls and the no-web-view dependency boundary."""

from __future__ import annotations

import re
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / 'tests/fixtures/e04_t1'


def web_dependency(text):
    text = re.sub(r'/\*.*?\*/|//[^\n]*|#[^\n]*', '', text, flags=re.DOTALL)
    return re.search(r'(?i)(?:Qt[56]?(?:::|[.])?)?Web(?:Engine\w*|View\w*)', text)


@pytest.mark.parametrize(
    'source',
    [
        'import QtWebView',
        'import QtWebEngine 1.0',
        'target_link_libraries(edi_app PRIVATE Qt6::WebEngineQuick)',
        'find_package(Qt6 COMPONENTS WebView)',
        'set(extra WebEngineCore)\ntarget_link_libraries(edi_app ${extra})',
    ],
)
def test_web_dependency_escape_controls(source):
    assert web_dependency(source), (
        'owner report: imports, links and indirect component lists must refuse web modules'
    )


def test_no_web_view_is_imported_or_linked():
    sources = [ROOT / 'CMakeLists.txt', ROOT / 'pixi.toml']
    sources += [
        p
        for directory in ('app', 'cmake')
        for p in (ROOT / directory).rglob('*')
        if p.suffix in {'.qml', '.cmake', '.cpp', '.hpp', '.h'} or p.name == 'CMakeLists.txt'
    ]
    # Inspect generated link inputs too when a build is available, catching a transitive base link.
    sources += list((ROOT / 'build/app').rglob('link.txt'))
    sources += list((ROOT / 'build/app').glob('build.ninja'))
    for path in sources:
        assert not web_dependency(path.read_text()), (
            'owner report: no WebEngine/WebView import or linked component in '
            f'{path.relative_to(ROOT)}'
        )


@pytest.mark.parametrize(
    ('path', 'warning'),
    [
        ('tests/fixtures/e04_t1/xray-project', ''),
        ('tests/fixtures/e04_t1/warning-project', 'legacy-e04-warning-witness'),
        ('docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/project', 'crysta (lm)'),
    ],
)
def test_independent_project_inputs_observe_actual_library_warning_channel(path, warning, capfd):
    # capfd captures the C++ library's fd 2, unlike capsys or Qt's message handler.
    project = edi.Project.load(ROOT / path)
    assert project is not None, (
        'owner amendments: every independent input is a valid library project'
    )
    captured = capfd.readouterr()
    expected = (
        f'Warning: unsupported _minimizer.type "{warning}" - using crysta' if warning else ''
    )
    assert captured.err.strip() == expected, (
        'review-4 F1: the actual library stderr diagnostic matches the committed token'
    )
    assert not captured.out, 'review-4 F1: the loader warning is not a stdout diagnostic'


def test_xray_project_retains_c15_t1_structure_and_nondefault_sources():
    original = (ROOT / 'tests/fixtures/c15_t1_xray/model.edi').read_text()
    structure, _ = original.split('data_experiment', 1)
    frozen = (FIXTURES / 'xray-project/structures/structure.edi').read_text()
    assert frozen.replace('_edi.schema_version 3\n', '') == structure, (
        'owner X-ray record: the structure is the independent committed  LiF fixture'
    )
    experiment = (FIXTURES / 'xray-project/experiments/experiment.edi').read_text()
    for declaration in (
        '_experiment_type.radiation_probe xray',
        '_scattering_source.xray_form_factor it1992',
        '_scattering_source.xray_dispersion sasaki1989',
    ):
        assert declaration in experiment, (
            'owner X-ray record: exercise a declared nondefault X-ray path'
        )
