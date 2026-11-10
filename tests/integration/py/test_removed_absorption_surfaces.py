"""The removed absorption parameter cannot remain on a public product surface."""

import json
from pathlib import Path

import pytest

from tests.fixtures.removed_absorption.surfaces import violations

ROOT = Path(__file__).resolve().parents[3]
SCOPES = {
    'parameters': (
        'core/include/edi/model.hpp',
        'core/include/edi/categories.hpp',
        'core/include/edi/parameter_spec.hpp',
        'core/include/edi/selectors.hpp',
    ),
    'python_surface': (
        'data/python-surface.json',
        'lib/src/model_views.hpp',
        'lib/src/model_views_registry.hpp',
        'lib/src/bindings.cpp',
        'lib/edi',
    ),
    'census': ('data/category-census.json',),
    'gui': ('app/qml', 'app/src'),
    'documentation': ('docs/user', 'website/surfaces/docs', 'docs/dev/features.md'),
    'examples_and_tutorials': ('examples', 'app/examples', 'app/tutorials'),
    'generators': (
        'tools/cli_projects',
        'tools/docs/app_builtin_tutorials.py',
        'tools/data/build_collection.py',
        'website/render_parameter_reference.py',
    ),
}


@pytest.mark.parametrize('group', SCOPES)
def test_removed_absorption_field_is_absent_from_every_public_surface(group):
    found = violations(ROOT, SCOPES[group])
    assert not found, (
        'The removed absorption field must be absent from every declared public surface: '
        + '; '.join(found)
    )


@pytest.mark.parametrize('group', SCOPES)
def test_public_surface_census_reaches_each_declared_scope(tmp_path, group):
    for name in SCOPES[group]:
        path = tmp_path / name
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            content = (
                json.dumps({'public': {}, 'classification': {'members': {}}})
                if path.suffix == '.json'
                else 'clean'
            )
            path.write_text(content)
        else:
            path.mkdir(parents=True, exist_ok=True)
            (path / 'clean.md').write_text('clean')
    assert not violations(tmp_path, SCOPES[group]), (
        'A clean public surface must pass before exercising its escape'
    )
    first = tmp_path / SCOPES[group][0]
    if first.is_dir():
        first /= 'probe.edi'
    if first.suffix == '.json':
        content = {'public': {'CylinderHewatAbsorption': {'members': ['abscor2']}}}
        first.write_text(json.dumps(content))
    else:
        first.write_text('retained _absorption.abscor2 0.025')
    assert violations(tmp_path, SCOPES[group]), (
        'Every surface group must reject a retained declaration, including documentation and GUI'
    )


@pytest.mark.parametrize(
    'suffix',
    ['.pcr', '.inp', '.new', '.PCR', '.prf', '.out', '.sum', '.edi', '.md', '.json', '.ipynb'],
)
def test_only_fullprof_input_formats_are_exempt(tmp_path, suffix):
    scope = tmp_path / 'public'
    scope.mkdir()
    (scope / 'clean.md').write_text('clean')
    path = scope / ('probe' + suffix)
    text = 'COMM FullProf control input\n!Job Npr Nph\n! ABS: ABSCOR1 ABSCOR2\n'
    path.write_text(json.dumps({'text': text}) if suffix in {'.json', '.ipynb'} else text)
    found = violations(tmp_path, ['public'])
    assert bool(found) == (suffix.lower() not in {'.pcr', '.inp', '.new'}), (
        'Only FullProf control-input formats may retain their second absorption column'
    )


@pytest.mark.parametrize('section', ['public', 'classification'])
def test_python_census_decodes_escaped_names_and_ignores_only_retired_metadata(tmp_path, section):
    path = tmp_path / 'python-surface.json'
    data = {
        'public': {},
        'classification': {'members': {}},
        'removed': {'CylinderHewatAbsorption.abscor2': {'reason': 'removed'}},
    }
    path.write_text(json.dumps(data))
    assert not violations(tmp_path, [path.name]), (
        'Historical removal metadata must not impersonate a live public declaration'
    )
    row = {'CylinderHewatAbsorption': {'members': ['abscor2']}}
    if section == 'public':
        data['public'] = row
    else:
        data['classification']['members'] = {'CylinderHewatAbsorption': {'abscor2': {}}}
    path.write_text(json.dumps(data).replace('abscor2', r'abscor\u0032'))
    assert violations(tmp_path, [path.name]), (
        'Escaped JSON names in either live Python declaration section must be detected'
    )


def test_missing_public_scope_cannot_silently_pass(tmp_path):
    with pytest.raises(AssertionError, match='must exist'):
        violations(tmp_path, ['missing'])


@pytest.mark.parametrize('suffix', ['.pcr', '.inp', '.new'])
def test_a_fullprof_extension_cannot_hide_a_renamed_project(tmp_path, suffix):
    scope = tmp_path / 'public'
    scope.mkdir()
    path = scope / ('project' + suffix)
    path.write_text('data_experiment\n_absorption.abscor2 0.025\n')
    assert violations(tmp_path, ['public']), (
        'The input exemption must prove FullProf control syntax, not just a file extension'
    )


@pytest.mark.parametrize('suffix', ['.pcr', '.inp', '.new'])
def test_multipattern_fullprof_inputs_keep_their_own_column(tmp_path, suffix):
    scope = tmp_path / 'public'
    scope.mkdir()
    (scope / 'clean.md').write_text('clean')
    (scope / ('five-banks' + suffix)).write_text(
        'A five-bank TOF example\nNPATT 5 1 1 1 1 1\nW_PAT .2 .2 .2 .2 .2\n'
        '!Job Npr Nba Nex\n-1 13 28 2\n! ABS: ABSCOR1 ABSCOR2\n'
    )
    assert not violations(tmp_path, ['public']), (
        'FullProf multi-pattern control inputs have a title and NPATT/W_PAT headers'
    )
