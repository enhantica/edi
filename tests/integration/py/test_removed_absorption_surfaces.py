"""The removed absorption parameter cannot remain on a public product surface."""

import json
from pathlib import Path

import pytest

from tests.fixtures.removed_absorption.surfaces import (
    FROZEN_STAMP_DATA,
    compiled_violations,
    violations,
)

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


def test_compiled_test_sources_and_included_fixtures_have_no_retired_typed_field():
    found = compiled_violations(ROOT, ['tests'])
    assert not found, (
        'All C++ test sources, included fixtures and headers use the active typed domain: '
        + '; '.join(found)
    )


@pytest.mark.parametrize(
    'suffix', ['.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx', '.inc', '.ipp', '.tpp']
)
def test_compiled_inventory_reaches_every_source_form_and_retains_legacy_data(tmp_path, suffix):
    source = tmp_path / ('witness' + suffix)
    legacy = (
        '// old.absorption.abscor2 remains an input spelling\n'
        '/* &AbsorptionBase::abscor2 is historical prose */\n'
        'const char* ordinary = "_absorption.abscor2 0.025";\n'
        'const auto raw = u8R"legacy(_absorption.abscor2 "quoted" 0.025)legacy";\n'
        "const char quote = '\\'';\n"
    )
    source.write_text(legacy)
    assert not compiled_violations(tmp_path, [source.name]), (
        'Legacy reader strings, raw input blocks and comments are preserved as data'
    )
    for access in (
        'bank.absorption.abscor2;',
        'auto& layer=bank.absorption;layer.abscor2;',
        'auto slot=&edi::AbsorptionBase::abscor2;',
        '#define RETIRED_SLOT abscor2\n',
        'auto& layer=bank.absorption;layer.abs\\\ncor2;',
    ):
        source.write_text(legacy + access)
        assert compiled_violations(tmp_path, [source.name]) == [source.name], (
            'Every C++ source form rejects direct, aliased, member-pointer and macro field escapes'
        )


def test_frozen_reference_is_only_unchanged_historical_data(tmp_path):
    original = ROOT / FROZEN_STAMP_DATA
    frozen = tmp_path / FROZEN_STAMP_DATA
    frozen.parent.mkdir(parents=True)
    frozen.write_bytes(original.read_bytes())
    consumer = tmp_path / 'tests/consumer.cpp'
    consumer.write_text('int active_domain;\n')
    assert not compiled_violations(tmp_path, ['tests']), (
        'The immutable old codec remains valid reference data without becoming compiled code'
    )
    consumer.write_text(
        '#include "fixtures/assistant_dev_integration/prechange_stamp_codec.inc"\n'
    )
    assert compiled_violations(tmp_path, ['tests']) == ['tests/consumer.cpp'], (
        'A caller cannot compile the historical snapshot to bypass the current-domain inventory'
    )
    consumer.write_text('int active_domain;\n')
    frozen.write_bytes(original.read_bytes() + b'\n')
    assert compiled_violations(tmp_path, ['tests']) == [FROZEN_STAMP_DATA], (
        'A modified historical snapshot cannot inherit the immutable-reference exception'
    )


def test_active_stamp_codec_projects_only_the_retired_historical_slot():
    frozen = (
        ROOT / 'tests/fixtures/assistant_dev_integration/prechange_stamp_codec.inc'
    ).read_bytes()
    projected = (
        ROOT / 'tests/fixtures/assistant_dev_integration/active_stamp_codec.inc'
    ).read_bytes()
    prefix, body = projected.split(b'\n', 1)
    assert prefix.startswith(b'// Active-domain projection'), (
        'The compiled codec explicitly identifies its current-domain reference projection'
    )
    retired = b'    put_optional_parameter(out, experiment.absorption.abscor2, scope);\n'
    assert frozen.count(retired) == 1, (
        'The accepted historical codec contains exactly the one explicitly retired slot'
    )
    assert body == frozen.replace(retired, b''), (
        'All other historical codec bytes remain independent of the current producer'
    )


@pytest.mark.parametrize('suffix', ['.md', '.png', '.dat', '.json', '.ipynb'])
@pytest.mark.parametrize('spelling', ['abscor2', 'ABSCOR_2', 'ab\u017fcor 2'])
def test_binary_prefilter_cannot_hide_unicode_case_or_mislabeled_text(tmp_path, suffix, spelling):
    scope = tmp_path / 'public'
    scope.mkdir()
    path = scope / ('probe' + suffix)
    text = (
        json.dumps({'text': spelling}, ensure_ascii=True)
        if suffix in {'.json', '.ipynb'}
        else spelling
    )
    path.write_bytes(text.encode())
    assert violations(tmp_path, ['public']) == [str(path.relative_to(tmp_path))], (
        'The byte prefilter preserves Unicode casefolding, escaped JSON and all file suffixes'
    )


def test_clean_binary_files_remain_in_the_nonexempt_surface_census(tmp_path):
    scope = tmp_path / 'public'
    scope.mkdir()
    (scope / 'image.png').write_bytes(bytes(range(256)) * 10)
    assert violations(tmp_path, ['public']) == [], (
        'Clean binary files remain in the nonexempt surface census.'
    )
