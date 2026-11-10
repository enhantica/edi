"""ADR-0108 token kinds and complete numbers through every native/CIF entrance."""

import math

import edi as api
import gemmi
import pytest

from tests.fixtures.magnetic_pnma import reference, token_inputs

# These registered synthetic parser probes need fit preparation, not a full measured pattern.
PROBE_EXPERIMENT = (reference.ROOT / 'compound-experiment.edi').read_text()


def stored_tokens(path, tag):
    return [value for block in gemmi.cif.read_file(str(path)) for value in block.find_values(tag)]


def loaded(source, route, root):
    if route.endswith('factory'):
        structure = api.StructureFactory.from_cif_str(source)
        assert structure is not None, 'The factory returns a structure for an admitted declaration'
        control = api.Project.load(
            reference.project(root / 'input', token_inputs.BASE, experiment=PROBE_EXPERIMENT)
        )
        control.structure = structure
        return control
    return api.Project.load(reference.project(root / 'input', source, experiment=PROBE_EXPERIMENT))


def saved_errors(project, root, case, kind, token):  # noqa: PLR0912 — lexical states and persistence stages
    project.save_as(root / 'saved')
    saved = root / 'saved/structures/cosio.edi'
    cells = stored_tokens(saved, case.tag)
    failures = []
    if (
        kind == 'valid'
        and case.kind in {'text', 'selector'}
        and not any(gemmi.cif.as_string(value) == case.good for value in cells)
    ):
        failures.append('a valid supplied value was replaced or discarded')
    if kind == 'valid' and case.family == 'moments':
        components = [
            float(
                gemmi.cif.as_string(
                    stored_tokens(saved, '_atom_site_moment.crystalaxis_' + axis)[0]
                )
            )
            for axis in 'xyz'
        ]
        if not all(
            math.isclose(given, expected, abs_tol=1e-10)
            for given, expected in zip(components, [1.5, 0, 0], strict=True)
        ):
            failures.append(
                'orthogonal-cell moment differs from independently specified (1.5,0,0)'
            )
    if kind == 'missing':
        if any(value not in {'?', '.'} and gemmi.cif.as_string(value) == token for value in cells):
            failures.append('bare missing marker became a supplied literal')
        if (
            case.family == 'form_factor'
            and case.kind == 'number'
            and any(abs(float(gemmi.cif.as_string(value))) > 0 for value in cells)
        ):
            failures.append('absent coefficient did not take declared zero')
    if kind == 'literal':
        if not any(
            value not in {'?', '.'} and gemmi.cif.as_string(value) == token[1:-1]
            for value in cells
        ):
            failures.append('quoted literal missing from saved declaration')
        again = api.Project.load(root / 'saved')
        again.save_as(root / 'second')
        if cells != stored_tokens(root / 'second/structures/cosio.edi', case.tag):
            failures.append('second save changes the held literal lexemes')
    if kind == 'valid' or (kind == 'literal' and case.kind == 'text'):
        again = api.Project.load(root / 'saved')
        again.save_as(root / 'second-valid')
        if cells != stored_tokens(root / 'second-valid/structures/cosio.edi', case.tag):
            failures.append('second save changes the held declared field')
        if len(again.structure.atom_site_moment):
            again.structure.atom_site_moment[0].crystalaxis_x.free = True
            try:
                again.fit(should_cancel=lambda: True)
            except (ValueError, RuntimeError, KeyError) as error:
                failures.append('valid declaration refused by fit preparation: ' + str(error))
    return failures


def admitted(source, route, root):
    project = loaded(source, route, root)
    project.analysis.calculate()
    return project


def observed_errors(source, route, root, case, kind, token):
    try:
        project = admitted(source, route, root)
    except (ValueError, RuntimeError, KeyError) as error:
        if (
            kind == 'valid'
            or (kind == 'literal' and case.kind == 'text')
            or (kind == 'missing' and case.missing_accepts)
        ):
            return ['valid supplied value refused: ' + str(error)]
        # A required missing value may refuse. Explicit invalid input must identify its boundary.
        if kind in {'invalid', 'literal'} and (
            case.tag.lower() not in str(error).lower() or token.strip('"\'') not in str(error)
        ):
            return ['refusal must name the tag and complete supplied value: ' + str(error)]
        return []
    if kind == 'invalid' or (kind == 'literal' and case.kind != 'text'):
        return ['invalid supplied token accepted or defaulted']
    return saved_errors(project, root, case, kind, token)


# Keep every probe and lifecycle assertion; separate the held-text lexical spellings
# so admitted literals plus second saves and fit preparation stay within this tier.
PROBES = [
    (route, case, group)
    for case in token_inputs.cases()
    for route in case.routes
    for group in (range(len(list(token_inputs.tokens(case)))) if case.kind == 'text' else (None,))
]


@pytest.mark.parametrize(
    ('route', 'case', 'group'),
    PROBES,
    ids=[
        f'{route}-{case.family}-{case.tag}-{case.variant}'
        + (f'-{list(token_inputs.tokens(case))[group][0]}-{group}' if group is not None else '')
        for route, case, group in PROBES
    ],
)
def test_each_magnetic_reader_honours_token_kind_and_complete_numbers(
    tmp_path, route, case, group
):
    errors = []
    reached = set()
    for serial, (kind, token) in enumerate(token_inputs.tokens(case)):
        if group is not None and serial != group:
            continue
        reached.add(kind)
        source = case.source.format(value=token)
        if route.startswith('cif'):
            source = token_inputs.cif(source)
        failures = observed_errors(source, route, tmp_path / str(serial), case, kind, token)
        errors.extend(f'{route} {case.tag} {token}: {failure}' for failure in failures)

    expected_kinds = (
        {list(token_inputs.tokens(case))[group][0]}
        if group is not None
        else {'valid', 'missing', 'literal'}
    )
    assert expected_kinds <= reached, (
        'Every declared lexical spelling actually reaches its supplied or missing probe'
    )
    assert not errors, (
        'ADR-0108 every supplied token retains its kind and complete declared type:\n'
        + '\n'.join(errors)
    )


@pytest.mark.parametrize('form', ['Cartn', 'spherical'])
@pytest.mark.parametrize('route', ['native-project', 'native-factory'])
def test_native_storage_refuses_unsupported_converted_moment_spellings(tmp_path, form, route):
    selected = next(
        case
        for case in token_inputs.cases()
        if case.family == 'moments' and form in case.tag and case.variant == 'selected'
    )
    source = selected.source.format(value=selected.good)
    with pytest.raises(
        (ValueError, RuntimeError, KeyError), match=r'(?i)(moment|unknown|Cartn|spherical)'
    ):
        admitted(source, route, tmp_path)


@pytest.mark.parametrize('form', ['Cartn', 'spherical'])
@pytest.mark.parametrize('route', ['cif-project', 'cif-factory'])
def test_a_supplied_moment_form_is_complete_even_beside_another_form(tmp_path, form, route):
    errors = []
    for index, (kind, source, tag) in enumerate(token_inputs.partial_moment_declarations(form)):
        try:
            model = admitted(token_inputs.cif(source), route, tmp_path / str(index))
        except (ValueError, RuntimeError, KeyError) as error:
            if kind == 'valid':
                errors.append('valid complete moment form refused: ' + str(error))
            elif '_atom_site_moment.' not in str(error):
                errors.append('incomplete declaration refusal lacks its moment tag: ' + str(error))
        else:
            if kind == 'invalid':
                errors.append('incomplete supplied form ignored or defaulted: ' + tag)
            else:
                values = [
                    getattr(model.structure.atom_site_moment[0], 'crystalaxis_' + axis).value
                    for axis in 'xyz'
                ]
                if not all(
                    math.isclose(a, b, abs_tol=1e-10)
                    for a, b in zip(values, [1.5, 0, 0], strict=True)
                ):
                    errors.append('complete form changes the independently stated moment')
    assert not errors, (
        'ADR-0108 each supplied moment form has all three values, including a redundant form: '
        + '\n'.join(errors)
    )
