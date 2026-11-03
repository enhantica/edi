"""Decimal save references; no product imports (ADR-0092)."""

import math
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import gemmi

from tests.fixtures.adp_site_symmetry.model import equivalent
from tests.fixtures.project_save.completion import (
    ANISOTROPIC,
    CELL,
    TENSOR,
    apply_declared,
    declared_relations,
    fixed_values,
    model_inputs,
)
from tests.fixtures.report_units.iucr_reference import rounded_pair
from tests.fixtures.saved_spelling.reference import NUMBER, decode

PAIRS = [
    (2.16352, 0.00481),
    (-2.16352, 0.00481),
    (1.54249, 0.01532),
    (0.4637, 0.0196),
    (54912.0, 1234.0),
    (0.000183461, 0.000087),
    (0.1234567, 0.00201),
]


def expected_pair(value, su, rule):
    return rounded_pair(value, su, rule or 'iucr_99')


def six_digits(value):
    number = Decimal(str(value))
    quantum = Decimal(1).scaleb(number.copy_abs().adjusted() - 5)
    return float(number.quantize(quantum, rounding=ROUND_HALF_UP))


def declared_rule(folder):
    path = Path(folder) / 'project.edi'
    match = (
        re.search(r'(?m)^_su_format\.rule\s+(\S+)', path.read_text()) if path.is_file() else None
    )
    return match[1].strip('"') if match else 'iucr_99'


def saved_triplet(value, uncertainty, free, rule='iucr_99'):
    """Independent Edi persisted state; bare fixed tokens read back as engaged zero."""
    if free and uncertainty is not None and math.isfinite(uncertainty) and uncertainty > 0:
        return (*expected_pair(value, uncertainty, rule), free)
    su = 0.0 if not free or uncertainty == 0 else None
    return six_digits(value), su, free


def tensor_readback(project, values, slots):
    """Tensor-zero presence and the existing independent Cartesian-trace relation."""
    derived = set()
    for structure in project.structures:
        cell = [values[slots[f'{structure.name}.cell.{field}']][0] for field in CELL]
        for site in structure.atom_sites:
            if site.adp_type not in ANISOTROPIC:
                continue
            indices = [
                slots[f'{structure.name}.atom_site_aniso.{site.id}.adp_{suffix}']
                for suffix in TENSOR
            ]
            for index in indices:
                value, su, free = values[index]
                if value == 0 and su == 0 and not free:
                    values[index] = (value, None, free)
            index = slots[f'{structure.name}.atom_site.{site.id}.adp_iso']
            values[index] = (
                equivalent({'cell': cell}, site.adp_type, [values[i][0] for i in indices]),
                values[index][1],
                values[index][2],
            )
            derived.add(index)
    return derived


def optional_written(optional, values, original, constrained):
    records = []
    for path, owner, field, fit_start in optional:
        index = original['slots'][path]
        value, su, free = original['completed_input'][index]
        present = value != 0 or su is not None or free or fit_start
        written = values[index]
        if not present:
            values[index] = (0.0, None, False)
        bracket = written[2] or (
            index in constrained and written[1] is not None and written[1] > 0
        )
        records.append((
            owner,
            field,
            present,
            (written[0], written[1] if bracket else None, bracket),
        ))
    return tuple(records)


def scalar_write(values, rule, graph, optional, slots):
    """One independent scalar write and its native/token readback projections."""
    written = []
    for index, (value, su, free) in enumerate(values):
        if index in graph and su is not None and math.isfinite(su) and su > 0:
            # ADR0024 preserves a constrained dependent's nonzero SU bracket;
            # its declaration clears the flag when the file is read.
            written.append((*expected_pair(value, su, rule), False))
        else:
            written.append(saved_triplet(value, su, free, rule))
    tokens = optional_written(
        optional, written, {'slots': slots, 'completed_input': values}, graph
    )
    return written, tokens


def loaded_values(project, written, slots):
    values = list(written)
    derived = tensor_readback(project, values, slots)
    return values, derived


def completed_values(project, loaded, slots, fixed, indices, graph):
    values = list(loaded)
    derived = tensor_readback(project, values, slots)
    for index, value in fixed.items():
        values[index] = (value, values[index][1], values[index][2])
    apply_declared(values, indices, graph, blocked=derived)
    tensor_readback(project, values, slots)
    return values


def saved_parameters(project, rule):
    """Project the public first-write/adopt/final-write sequence deterministically."""
    parameters, slots, lookups, optional, identity = model_inputs(project)
    original = [(p.value, p.uncertainty, p.free) for p in parameters]
    exact_input = list(original)
    indices, graph = declared_relations(identity, slots, lookups)
    fixed = fixed_values(project, slots)
    assert not (set(fixed) & set(graph)), (
        'A declared expression cannot replace a fixed symmetry target'
    )
    for index, value in fixed.items():
        exact_input[index] = (value, exact_input[index][1], exact_input[index][2])
    apply_declared(exact_input, indices, graph)
    stages = {}
    stages['first_written'], stages['first_tokens'] = scalar_write(
        exact_input, rule, graph, optional, slots
    )
    stages['first_loaded'], derived = loaded_values(project, stages['first_written'], slots)
    stages['adopted'] = completed_values(
        project, stages['first_loaded'], slots, fixed, indices, graph
    )
    stages['parameter_rewrite_required'] = original != stages['adopted']
    stages['final_written'], tokens = scalar_write(stages['adopted'], rule, graph, optional, slots)
    if not stages['parameter_rewrite_required']:
        assert (
            stages['final_written'] == stages['first_written'] and tokens == stages['first_tokens']
        ), 'Unchanged adoption has the same parameter/token projection whether calculated or not'
    stages['loaded'], derived = loaded_values(project, stages['final_written'], slots)
    stages['completed'] = completed_values(project, stages['loaded'], slots, fixed, indices, graph)
    assert stages['completed'] == stages['adopted'], (
        'A successful final Save readback completes to its adopted parameter state'
    )
    return stages, derived, identity, tokens


def require_optional_tokens(model, records):
    blocks = {}
    for owner, field, present, wanted in records:
        if owner not in blocks:
            path = Path(model.metadata.path) / 'experiments' / (owner + '.edi')
            blocks[owner] = gemmi.cif.read_file(str(path)).sole_block()
        token = blocks[owner].find_value('_instrument.' + field)
        assert (token is not None) is present, (
            'Optional instrument token presence follows its original meaningful declaration state'
        )
        if present:
            if re.fullmatch(NUMBER, token):
                actual = (float(token), None, False)
            else:
                value, su = decode(token)
                actual = (value, su, True)
            assert actual == wanted, (
                'Optional tokens retain exact independently projected value/SU/free syntax'
            )


def require_saved_parameters(parameters, reference, *, model, phase):
    projections, derived, identity, optional_tokens = reference
    assert phase in {'loaded', 'completed'}, (
        'The real caller explicitly names its publication boundary'
    )
    observed, _slots, _lookups, _optional, observed_identity = model_inputs(model)
    assert [id(p) for p in parameters] == [id(p) for p in observed], (
        'The supplied parameter population belongs to the exact declared current model'
    )
    assert observed_identity == identity, (
        'Save retains owned paths, setting, sites, types, aliases and declarations'
    )
    require_optional_tokens(model, optional_tokens)
    expected = projections[phase]
    actual = [(p.value, p.uncertainty, p.free) for p in parameters]
    assert len(actual) == len(expected), 'Save retains the complete model parameter population'
    for index, (got, wanted) in enumerate(zip(actual, expected, strict=True)):
        assert got[1:] == wanted[1:], (
            'Save retains independently projected uncertainty and free state'
        )
        if index in derived:
            assert math.isclose(got[0], wanted[0], rel_tol=2e-14, abs_tol=2e-14), (
                'The isotropic mirror follows the tensor trace with the independently rounded cell'
            )
        else:
            assert got[0] == wanted[0], (
                'Persisted parameters follow exact independent decimal rounding'
            )
