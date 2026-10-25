"""Keep Structure availability tied to Qt's actual 3D capability."""

import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture, qt_reference


@pytest.fixture(scope='module')
def structure_captures(request):
    selected = {
        item.callspec.params['backend']
        for item in request.session.items
        if item.module is request.module and hasattr(item, 'callspec')
    }
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    result = {}
    for backend in sorted(selected):
        prefix = ['env', 'QT_QUICK_BACKEND=software'] if backend == 'software' else []
        result[backend] = capture([
            *prefix,
            binary,
            '-input',
            ROOT / 'tests/system/app/StructureBackend.qml',
            '-o',
            '-,txt',
            'StructureBackend::test_structure_capability',
        ])
    return result


@pytest.mark.parametrize('backend', ['graphics-api', 'software'])
def test_structure_view_matches_actual_backend_capability(structure_captures, backend):
    status, output = structure_captures[backend]
    observed = qt_reference(output)
    if backend == 'software':
        assert observed['api'] == 'Software', 'The software control must use Qt Quick Software'
    else:
        assert observed['api'] in {'OpenGL', 'Direct3D11', 'Direct3D12', 'Vulkan', 'Metal'}, (
            'The graphics capture must initialize a Qt Quick 3D capable API'
        )
    assert status == 0, 'The actual Structure capability actor must pass: ' + output
    assert 'PASS   : edi_app::StructureBackend::test_structure_capability()' in output, (
        'Both Structure capability cases must execute their real view assertions without skipping'
    )
    assert '::StructureBackend::cleanupTestCase()' in output, (
        'Both Structure capability processes must reach cleanup'
    )
