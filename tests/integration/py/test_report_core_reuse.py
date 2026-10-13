"""Supplement behavioral renderer seams with the shared-core ownership contract."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def code(path):
    assert path.is_file(), (
        'The planned shared core component must exist before the ownership check'
    )
    text = path.read_text()
    return re.sub(r'//[^\n]*|/\*[\s\S]*?\*/', '', text)


@pytest.mark.parametrize(
    'call', ['present_pattern', 'present_structure', 'default_view', 'scene_drawing']
)
def test_report_builder_reaches_the_existing_presentation_and_drawing_functions(call):
    source = code(ROOT / 'core/src/report_model.cpp')
    assert re.search(r'\b' + call + r'\s*\(', source), (
        'The model builder must call the existing core presentation and drawing contract, '
        'rather than create another renderer convention'
    )


@pytest.mark.parametrize(
    ('function', 'view'),
    [
        ('correlation_matrix', 'correlation_view_model.cpp'),
        ('evolution_series', 'evolution_view_model.cpp'),
    ],
)
def test_live_tab_and_builder_both_reach_the_same_core_filter_or_series(function, view):
    for path in [ROOT / 'core/src/report_model.cpp', ROOT / 'app/src' / view]:
        assert re.search(r'\b' + function + r'\s*\(', code(path)), (
            'The live tab and report builder must share the core correlation/evolution function'
        )


def test_report_model_header_remains_free_of_qt_and_html_rendering():
    source = code(ROOT / 'core/include/edi/report_model.hpp')
    assert not re.search(r'\b(?:QString|QObject|QVariant|QQuickItem|QTextDocument)\b', source), (
        'The versioned report model must remain usable without Qt'
    )
    assert not re.search(r'#include\s*[<"](?:Qt|[^">]*report_html)', source), (
        'A report data model must not depend on a Qt or HTML renderer'
    )
