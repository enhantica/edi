"""Public constraint behaviour from the grammar, algebra and saved-file contract."""

from __future__ import annotations

import json
import math
import re
import runpy
import warnings
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
MATERIALIZE = runpy.run_path(str(ROOT / 'tests/fixtures/constraint_expressions/project.py'))[
    'materialize'
]
ALIASES = [('a', 'phase.atom_site.A.adp_iso'), ('b', 'phase.atom_site.B.adp_iso')]


def assert_code(error, code):
    assert any(str(item.code) == code for item in error.diagnostics), (
        'a refusal must carry its stable code in the structured diagnostics'
    )


def model(tmp_path, expressions=(), **kwargs):
    return engine.Project.load(MATERIALIZE(tmp_path, ALIASES, expressions, **kwargs))


def pair(project):
    return tuple(site.adp_iso for site in project.structure.atom_sites)


def add(project, expression):
    assert hasattr(project.analysis, 'constraints'), (
        'analysis must expose the core constraint collection'
    )
    project.analysis.constraints.create(expression=expression)


@pytest.mark.parametrize(
    ('expression', 'expected'),
    [
        ('b = 2*a + 1', 1.6),
        ('b = 1-a', 0.7),
        ('b = a / .5', 0.6),
        ('b = -(-a) + +2.5e-1', 0.55),
        ('b = sqrt(a*a + .16)', 0.5),
        ('b = 2 ** 3 ** 2', 512.0),
        ('b = -a**2 + 1', 0.91),
        ('b = a**(1+1)', 0.09),
        ('b = sin(a)', math.sin(0.3)),
        ('b = cos(a)', math.cos(0.3)),
        ('b = exp(a)', math.exp(0.3)),
        ('b = log(a) + 2', math.log(0.3) + 2),
        ('b = abs(-a)', 0.3),
        ('b = acos(a)', math.acos(0.3)),
        ('b = erfc(a)', math.erfc(0.3)),
        ('b = abs(0)', 0.0),
        ('b = 1.2', 1.2),
    ],
    ids=lambda value: re.sub(r'[^A-Za-z0-9_.-]', '_', str(value)),
)
def test_loaded_expression_matches_closed_form(tmp_path, expression, expected):
    project = model(tmp_path, [expression])
    project.analysis.calculate()
    assert pair(project)[1].value == pytest.approx(expected, rel=2e-14, abs=2e-14), (
        'loaded expressions must evaluate with the declared precedence and double arithmetic'
    )
    assert pair(project)[1].user_constrained, 'a declared target must be marked user-constrained'


def test_angle_units_require_the_explicit_degree_conversion(tmp_path):
    aliases = [*ALIASES, ('gamma', 'phase.cell.angle_gamma')]
    directory = MATERIALIZE(tmp_path, aliases, ['b = a * sin(gamma * pi / 180)'])
    source = directory / 'structures/phase.edi'
    source.write_text(source.read_text().replace('angle_gamma 90', 'angle_gamma 37'))
    project = engine.Project.load(directory)
    project.analysis.calculate()
    assert pair(project)[1].value == pytest.approx(0.3 * math.sin(math.radians(37)), abs=2e-14), (
        'a nonzero degree-valued cell angle must convert explicitly before radian trigonometry'
    )


@pytest.mark.parametrize(
    'rhs',
    [
        "__import__('os')",
        'a.__class__',
        'lambda',
        'a;1',
        "'text'",
        'exec(a)',
        'tan(a)',
        'unknown',
        'a[0]',
        'a = 1',
        'a == 1',
        'a < 1',
        'a and 1',
        'a | 1',
        'a & 1',
        'a**a',
        '1_000',
        '0x1p3',
        'nan',
        'inf',
        'e',
        'sin(a,1)',
        'sin()',
        '',
        '(a',
        'a)',
    ],
    ids=lambda value: re.sub(r'[^A-Za-z0-9_.-]', '_', str(value)),
)
def test_interpreter_and_non_grammar_tokens_are_named_refusals(tmp_path, rhs):
    with pytest.raises(engine.ValidationError) as failure:
        model(tmp_path, ['b = ' + rhs])
    code = (
        'constraint_reference'
        if rhs in {'lambda', 'unknown', 'nan', 'inf', 'e'}
        else 'constraint_syntax'
    )
    assert_code(failure.value, 'crysta.domain.' + code)
    message = str(failure.value)
    assert 'column' in message.lower(), 'a grammar refusal must locate its offending token'
    if rhs.strip():
        assert any(token in message for token in (rhs, rhs.split('(')[0], rhs[:1])), (
            'a grammar refusal must name the offending token rather than a generic parse failure'
        )


@pytest.mark.parametrize(
    ('aliases', 'expressions', 'code', 'names'),
    [
        (ALIASES, ['a = b', 'b = a'], 'constraint_cycle', ('a', 'b')),
        (ALIASES, ['a = a'], 'constraint_cycle', ('a',)),
        (ALIASES, ['b = a', 'b = 2*a'], 'constraint_target', ('b',)),
        (ALIASES, ['absent = a'], 'constraint_reference', ('absent',)),
        (
            [('a', 'phase.atom_site.missing.adp_iso'), ALIASES[1]],
            ['b = a'],
            'constraint_reference',
            ('missing',),
        ),
        (
            [('a', 'phase.atom_site.A.type_symbol'), ALIASES[1]],
            ['b = a'],
            'constraint_reference',
            ('type_symbol',),
        ),
        (
            [('a', 'phase.cell.length_a'), ('b', 'phase.cell.length_b')],
            ['b = a'],
            'constraint_target',
            ('b',),
        ),
    ],
    ids=lambda value: re.sub(r'[^A-Za-z0-9_.-]', '_', str(value)),
)
def test_graph_and_reference_refusals_identify_the_participants(
    tmp_path, aliases, expressions, code, names
):
    with pytest.raises(engine.ValidationError) as failure:
        engine.Project.load(
            MATERIALIZE(
                tmp_path,
                aliases,
                expressions,
                symmetry=code == 'constraint_target' and 'cell' in aliases[0][1],
            )
        )
    assert_code(failure.value, 'crysta.domain.' + code)
    for name in names:
        assert name in str(failure.value), (
            'a refused relation must identify every offending participant'
        )


@pytest.mark.parametrize(
    'rhs',
    ['1/0', 'sqrt(-a)', 'sqrt(0)', 'log(0)', 'acos(1)', 'exp(1000)'],
    ids=lambda value: re.sub(r'[^A-Za-z0-9_.-]', '_', str(value)),
)
def test_nonfinite_value_or_slope_refuses_the_strict_load(tmp_path, rhs):
    with pytest.raises(engine.ValidationError) as failure:
        model(tmp_path, ['b = ' + rhs])
    assert_code(failure.value, 'crysta.domain.constraint_value')
    assert 'b' in str(failure.value), (
        'a domain error must name the relation that cannot be evaluated'
    )


def test_create_inspect_remove_and_default_id(tmp_path):
    project = engine.Project.load(MATERIALIZE(tmp_path))
    a, b = pair(project)
    assert hasattr(project.analysis, 'aliases'), 'analysis must expose aliases through the core'
    aliases = project.analysis.aliases
    aliases.create(id='a', param=a)
    aliases.create(id='b', param=b)
    assert aliases['a'].parameter_unique_name == 'phase.atom_site.A.adp_iso', (
        'alias creation must capture the owning datablock, row id and dictionary name'
    )
    assert aliases['a'].param.value == pytest.approx(0.3, rel=0, abs=0), (
        'an alias must resolve back to its live parameter'
    )
    add(project, 'b = 2*a + 1')
    constraint = project.analysis.constraints['b']
    assert constraint.id == 'b', 'omitting the constraint id must use the left alias'
    assert constraint.expression == 'b = 2*a + 1', (
        'the saved expression must retain its original text'
    )
    assert constraint.lhs_alias == 'b', 'constraint inspection must expose the left alias'
    assert constraint.rhs_expr.strip() == '2*a + 1', (
        'constraint inspection must expose the right expression'
    )
    project.analysis.calculate()
    assert b.value == pytest.approx(1.6), (
        'a newly created constraint must be applied by calculation'
    )
    project.analysis.constraints.remove('b')
    project.analysis.calculate()
    assert not b.user_constrained, 'removing the relation must clear its derived dependence mark'
    b.free = True
    assert b.free, 'removing a relation must make its former target independently selectable'


@pytest.mark.parametrize(
    'name', ['sin', 'pi'], ids=lambda value: re.sub(r'[^A-Za-z0-9_.-]', '_', str(value))
)
def test_reserved_alias_names_are_refused(tmp_path, name):
    project = engine.Project.load(MATERIALIZE(tmp_path))
    assert hasattr(project.analysis, 'aliases'), (
        'aliases must have the declared public creation API'
    )
    with pytest.raises((ValueError, RuntimeError), match='reserved'):
        project.analysis.aliases.create(id=name, param=pair(project)[0])


def test_chain_is_topological_and_direct_target_writes_are_replaced(tmp_path):
    aliases = [*ALIASES, ('c', 'bank.background.right.intensity')]
    project = engine.Project.load(MATERIALIZE(tmp_path, aliases, ['c = 3*b + 2', 'b = 2*a + 1']))
    a, b = pair(project)
    for value in (0.41, 0.19, 0.41):
        a.value = value
        b.value = 5.5
        project.analysis.calculate()
        assert b.value == pytest.approx(2 * value + 1), (
            'calculation must overwrite a direct dependent edit'
        )
        assert project.experiment.background[1].intensity.value == pytest.approx(6 * value + 5), (
            'chains must follow dependency order even when declarations appear in reverse order'
        )


def free_case(tmp_path, source, *, loaded=False):
    directory = MATERIALIZE(
        tmp_path,
        ALIASES,
        ['b = 2*a + 1'] if source == 'user' else [],
        symmetry=source != 'user',
        dependent_free=loaded and source != 'position',
    )
    if source == 'position':
        path = directory / 'structures/phase.edi'
        text = path.read_text().replace('P m -3 m', 'I 21 3')
        text = text.replace('Biso 0 0 0', 'Biso .25193 .25193 .25193')
        if loaded:
            text = text.replace(
                'A La a Biso .25193 .25193 .25193', 'A La a Biso .25193 .25193() .25193'
            )
        path.write_text(text)
    return engine.Project.load(directory)


def free_pair(project, source):
    if source == 'user':
        return pair(project)
    if source == 'position':
        atom = project.structure.atom_sites[0]
        return atom.fract_x, atom.fract_y
    return project.structure.cell.length_a, project.structure.cell.length_b


@pytest.mark.parametrize(
    'source',
    ['user', 'cell', 'position'],
    ids=lambda value: re.sub(r'[^A-Za-z0-9_.-]', '_', str(value)),
)
def test_python_free_flag_warns_without_redirecting_to_a_leader(tmp_path, source):
    project = free_case(tmp_path, source)
    leader, dependent = free_pair(project, source)
    leader.free = False
    before = leader.value
    with pytest.warns(UserWarning, match='crysta.domain.dependent_free_ignored'):
        dependent.free = True
    assert not dependent.free, 'a dependent free request must be ignored'
    assert not leader.free, 'an ignored dependent flag must not select its leader'
    assert leader.value == before, 'an ignored flag must never free or change its leader'
    assert len(project.free_parameters) == 0, 'a dependent must add no free or descent column'


@pytest.mark.parametrize(
    'source',
    ['user', 'cell', 'position'],
    ids=lambda value: re.sub(r'[^A-Za-z0-9_.-]', '_', str(value)),
)
def test_loaded_brackets_warn_and_save_dependents_bare(tmp_path, source):
    with pytest.warns(UserWarning, match='crysta.domain.dependent_free_ignored'):
        project = free_case(tmp_path / 'input', source, loaded=True)
    _, target = free_pair(project, source)
    assert not target.free, 'a loaded bracket must not free a dependent'
    project.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/structures/phase.edi').read_text()
    if source == 'position':
        line = next(line for line in text.splitlines() if line.startswith('A '))
        token = line.split()[5]
    elif source == 'user':
        line = next(line for line in text.splitlines() if line.startswith('B '))
        token = line.split()[-1]
    else:
        line = next(line for line in text.splitlines() if line.startswith('_cell.length_b '))
        token = line.split()[-1]
    assert '(' not in token, 'saving a dependent must omit brackets even with uncertainty'


def test_quoted_loops_round_trip_and_default_id_is_written(tmp_path):
    expression = 'b = 2*a + 2.5e-1'
    project = model(tmp_path / 'input', [expression])
    for index in range(2):
        destination = tmp_path / f'saved-{index}'
        project.save_as(destination)
        text = (destination / 'analysis/analysis.edi').read_text()
        assert '_alias.parameter_unique_name' in text, 'saving must retain the alias loop'
        assert '_constraint.id' in text, (
            'saving an omitted constraint id must materialize its left alias'
        )
        assert '"' + expression + '"' in text, (
            'an expression containing spaces must be one quoted loop value'
        )
        project = engine.Project.load(destination)
        assert project.analysis.constraints['b'].expression == expression, (
            'reload must preserve expression text verbatim'
        )
        assert pair(project)[1].value == pytest.approx(0.85), (
            'reload must retain the active relation'
        )
    first = (tmp_path / 'saved-0/analysis/analysis.edi').read_bytes()
    assert first == (tmp_path / 'saved-1/analysis/analysis.edi').read_bytes(), (
        'successive saves must preserve both complete analysis loops byte-for-byte'
    )


def test_background_address_uses_row_id_after_reordering(tmp_path):
    aliases = [('a', 'bank.background.right.intensity'), ('b', 'phase.atom_site.B.adp_iso')]
    directory = MATERIALIZE(tmp_path, aliases, ['b = a/10'])
    path = directory / 'experiments/bank.edi'
    project = engine.Project.load(directory)
    project.analysis.calculate()
    assert pair(project)[1].value == pytest.approx(0.9), (
        'the declared background key must resolve at its supplied row'
    )
    path.write_text(path.read_text().replace('left 20 3\nright 100 9', 'right 100 9\nleft 20 3'))
    project = engine.Project.load(directory)
    project.analysis.calculate()
    assert pair(project)[1].value == pytest.approx(0.9), (
        'background references must follow their stored key after row reordering'
    )


def test_projects_without_constraints_keep_the_pre_feature_writer_regression_pin(tmp_path):
    fixture = ROOT / 'tests/fixtures/constraint_expressions'
    snapshot = runpy.run_path(str(fixture / 'freeze_unconstrained.py'))['snapshot']
    expected = json.loads((fixture / 'unconstrained_regression.json').read_text())
    from tests.fixtures.table_display.stored_id_bytes import ordinal_copy  # noqa: PLC0415

    source = MATERIALIZE(tmp_path / 'input')
    project = engine.Project.load(source)
    project.save_as(tmp_path / 'saved')
    legacy = ordinal_copy(source, tmp_path / 'saved', tmp_path / 'ordinal-pin')
    assert snapshot(legacy) == expected, (
        'without relation loops saved files must retain their pre-feature regression bytes, '
        'normalizing only the two metadata clock fields'
    )


@pytest.mark.parametrize('entry', ['calculate', 'save'])
def test_invalid_independent_edit_is_refused_at_every_strict_entry(tmp_path, entry):
    project = model(tmp_path / 'input', ['b = 1/a'])
    pair(project)[0].value = 0
    action = (
        project.analysis.calculate
        if entry == 'calculate'
        else lambda: project.save_as(tmp_path / 'saved')
    )
    with pytest.raises(engine.ValidationError) as failure:
        action()
    assert_code(failure.value, 'crysta.domain.constraint_value')


def test_alias_creation_refuses_foreign_handles_and_duplicate_ids(tmp_path):
    project = engine.Project.load(MATERIALIZE(tmp_path / 'local'))
    foreign = engine.Project.load(MATERIALIZE(tmp_path / 'foreign'))
    aliases = project.analysis.aliases
    aliases.create(id='a', param=pair(project)[0])
    with pytest.raises((ValueError, RuntimeError)):
        aliases.create(id='a', param=pair(project)[1])
    assert len(aliases) == 1, 'duplicate creation must leave the original alias intact'
    with pytest.raises((ValueError, RuntimeError)):
        aliases.create(id='foreign', param=pair(foreign)[0])
    assert len(aliases) == 1, 'a handle from another project must never bind by matching values'


def test_space_group_edit_refreshes_dependence_and_clears_a_stale_free_flag(tmp_path):
    project = engine.Project.load(MATERIALIZE(tmp_path / 'triclinic'))
    cubic = engine.Project.load(MATERIALIZE(tmp_path / 'cubic', symmetry=True))
    # A category read is a retained handle, not a snapshot (ADR-0012).
    # Save the immutable identity so restoration really removes the cubic relations.
    original = project.structure.space_group.name_h_m
    project.structure.cell.length_b.free = True
    project.structure.space_group = cubic.structure.space_group
    with pytest.warns(UserWarning, match='crysta.domain.dependent_free_ignored'):
        project.analysis.calculate()
    assert project.structure.cell.length_b.symmetry_constrained, (
        'changing symmetry must refresh dependence before building any solved columns'
    )
    assert not project.structure.cell.length_b.free, (
        'a newly dependent field must lose its stale independent flag'
    )
    assert not project.structure.cell.length_a.free, (
        'refreshing symmetry must never redirect the stale flag to its leader'
    )
    project.structure.space_group.name_h_m = original
    assert project.structure.space_group.name_h_m == 'P 1', (
        'restoration must actually return the declaration to the independent triclinic group'
    )
    project.analysis.calculate()
    assert not project.structure.cell.length_b.symmetry_constrained, (
        'removing the symmetry relation must clear its stale dependence mark'
    )
    project.structure.cell.length_b.free = True
    assert project.structure.cell.length_b.free, (
        'the former symmetry follower must become independently selectable again'
    )


def test_disabled_relation_stays_declared_and_reenables_at_the_current_value(tmp_path):
    project = model(tmp_path, ['b = 2*a + 1'])
    relation = project.analysis.constraints['b']
    relation.enabled = False
    a, b = pair(project)
    a.value = 0.47
    b.value = 9
    project.analysis.calculate()
    assert len(project.analysis.constraints) == 1, (
        'disabling must preserve the declared constraint row'
    )
    assert b.value == 9, 'a disabled constraint must not overwrite an ordinary parameter'
    assert not b.user_constrained, 'a disabled relation must release its dependent mark'
    b.free = True
    assert b.free, 'a disabled target must be independently selectable'
    b.free = False
    relation.enabled = True
    project.analysis.calculate()
    assert b.value == pytest.approx(1.94), (
        'reenabling must apply the retained expression at the current independent value'
    )
    assert b.user_constrained, 'reenabling must restore the dependent mark'


def test_enabled_state_round_trips_and_all_enabled_keeps_the_reference_format(tmp_path):
    project = model(tmp_path / 'input', ['b = 2*a + 1'])
    relation = project.analysis.constraints['b']
    assert relation.enabled, 'an omitted enabled column must default to true'
    project.save_as(tmp_path / 'active')
    assert '_constraint.enabled' not in (tmp_path / 'active/analysis/analysis.edi').read_text(), (
        'an all-enabled project must retain the documented upstream loop format'
    )
    relation.enabled = False
    pair(project)[1].value = 9
    project.save_as(tmp_path / 'disabled')
    text = (tmp_path / 'disabled/analysis/analysis.edi').read_text()
    assert '_constraint.enabled' in text, 'a disabled row requires its state column'
    assert re.search(r'\bfalse\b', text), (
        'saving a disabled row must persist the explicit false state'
    )
    restored = engine.Project.load(tmp_path / 'disabled')
    assert not restored.analysis.constraints['b'].enabled, (
        'reopening must retain the disabled constraint instead of silently enabling it'
    )
    restored.analysis.calculate()
    assert pair(restored)[1].value == 9, 'reopening a disabled row must not apply it'
    restored.save_as(tmp_path / 'again')
    assert (tmp_path / 'again/analysis/analysis.edi').read_text() == text, (
        'disabled-state analysis serialization must be stable across another round trip'
    )
    restored.analysis.constraints['b'].enabled = True
    restored.save_as(tmp_path / 'reenabled')
    assert (
        '_constraint.enabled' not in (tmp_path / 'reenabled/analysis/analysis.edi').read_text()
    ), 'reenabling every row must return to the all-enabled reference format'


def test_loaded_disabled_target_keeps_its_ordinary_free_flag_without_warning(tmp_path):
    directory = MATERIALIZE(tmp_path, ALIASES, ['b = 2*a + 1'], dependent_free=True)
    path = directory / 'analysis/analysis.edi'
    path.write_text(
        path
        .read_text()
        .replace('_constraint.expression\n', '_constraint.expression\n_constraint.enabled\n')
        .replace('"b = 2*a + 1"\n', '"b = 2*a + 1" false\n')
    )
    with warnings.catch_warnings(record=True) as messages:
        warnings.simplefilter('always')
        project = engine.Project.load(directory)
        project.analysis.calculate()
    assert not any('dependent_free_ignored' in str(item.message) for item in messages), (
        'an inactive relation must not warn about its independently free target'
    )
    assert not project.analysis.constraints['b'].enabled, (
        'the core reader must preserve a disabled row from its boolean column'
    )
    assert pair(project)[1].free, 'an inactive target must retain its ordinary free flag'
    assert len(project.free_parameters) == 1, (
        'a disabled relation must leave its target in the independent free set'
    )
    assert pair(project)[1].value == pytest.approx(0.8), (
        'a loaded disabled expression must not complete its target'
    )


def test_disabled_edge_is_excluded_from_cycle_detection(tmp_path):
    directory = MATERIALIZE(tmp_path, ALIASES, ['a = b', 'b = a'])
    path = directory / 'analysis/analysis.edi'
    path.write_text(
        path
        .read_text()
        .replace('_constraint.expression\n', '_constraint.expression\n_constraint.enabled\n')
        .replace('"a = b"\n', '"a = b" true\n')
        .replace('"b = a"\n', '"b = a" false\n')
    )
    project = engine.Project.load(directory)
    project.analysis.calculate()
    assert pair(project)[0].value == pytest.approx(0.8), (
        'the active graph must omit disabled edges before sorting and detecting cycles'
    )
    assert len(project.analysis.constraints) == 2, (
        'omitting a disabled edge from evaluation must not delete its saved declaration'
    )
