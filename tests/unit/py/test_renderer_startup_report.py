"""A startup report cannot hide project warnings or malformed diagnostics."""

import pytest

from tests.fixtures.fast_chart_redraws.startup import split_renderer_reports


@pytest.mark.parametrize(
    ('line', 'api', 'renderer', 'software'),
    [
        ('Software, software rendering (no GPU)', 'Software', '', True),
        ('Metal, hardware rendering', 'Metal', '', False),
        ('Direct3D 11, hardware rendering', 'Direct3D 11', '', False),
        ('Vulkan, hardware rendering', 'Vulkan', '', False),
        ('OpenGL, renderer Apple M2, hardware rendering', 'OpenGL', 'Apple M2', False),
        (
            'OpenGL, renderer llvmpipe (LLVM 23.1.1, 256 bits), software rendering (no GPU)',
            'OpenGL',
            'llvmpipe (LLVM 23.1.1, 256 bits)',
            True,
        ),
    ],
)
def test_complete_report_retains_backend_identity(line, api, renderer, software):
    reports, diagnostics = split_renderer_reports('edi: graphics: ' + line + '\n')
    assert reports == [{'api': api, 'renderer': renderer, 'software': software}], (
        'A complete startup report retains its independently supplied backend identity'
    )
    assert not diagnostics, 'Only the complete declared renderer report is exempt from stderr'


@pytest.mark.parametrize(
    'line',
    [
        'edi: graphics: , hardware rendering\n',
        'edi: graphics: OpenGL, hardware rendering\n',
        'edi: graphics: Software, hardware rendering\n',
        'edi: graphics: Metal, software rendering (no GPU)\n',
        'edi: graphics: OpenGL, renderer , hardware rendering\n',
        'edi: graphics: Software, renderer project failed, software rendering (no GPU)\n',
        'edi: graphics: Software, software rendering (no GPU), project warning\n',
        'warning: edi: graphics: Software, software rendering (no GPU)\n',
        'edi: project load failed\n',
        '\n',
    ],
)
def test_lookalikes_remain_diagnostics(line):
    reports, diagnostics = split_renderer_reports(line)
    assert reports == [], 'An incomplete, contradictory or prefixed line is no renderer report'
    assert diagnostics == line, 'Malformed reports and unrelated diagnostics remain byte-for-byte'


def test_project_diagnostic_beside_report_is_preserved():
    warning = 'edi: legacy experiment type was inferred\n'
    reports, diagnostics = split_renderer_reports(
        'edi: graphics: Software, software rendering (no GPU)\r\n' + warning
    )
    assert len(reports) == 1, (
        'One complete startup report is recognised beside a project diagnostic'
    )
    assert diagnostics == warning, 'A startup report cannot conceal an adjacent project diagnostic'
