"""Independent declared-input completion for Save observations, never an engine call."""

import ast
import hashlib
import math
import operator
from fractions import Fraction
from functools import cache
from pathlib import Path

CELL = ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma')
SITE = ('fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso')
TENSOR = ('11', '22', '33', '12', '13', '23')
ANISOTROPIC = {'Uani', 'Bani', 'beta'}
OPTIONAL_XRAY = (
    'setup_polarization_coefficient',
    'setup_monochromator_twotheta',
    'setup_wavelength_2',
    'setup_wavelength_2_to_1_ratio',
)
EXTINCTION = (
    'domain_radius',
    'mosaic_spread',
    'crystal_radius',
    'coefficient',
    'coefficient_11',
    'coefficient_22',
    'coefficient_33',
    'coefficient_12',
    'coefficient_13',
    'coefficient_23',
)
DECLARED_TABLE_SHA256 = 'fc29a89a22c41453fe51195484f35c21fc06347ef911ef72c0f20635c95be496'
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def arithmetic(node, names, number=float):
    """Closed ordinary arithmetic, preserving the declared binary operation order."""
    if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
        assert math.isfinite(node.value), 'Declared reference literals must be finite'
        return number(str(node.value))
    if isinstance(node, ast.Name):
        assert node.id in names, 'A declared expression must name an independently bound input'
        return names[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = arithmetic(node.operand, names, number)
        return value if isinstance(node.op, ast.UAdd) else -value
    assert isinstance(node, ast.BinOp) and type(node.op) in OPERATORS, (
        'Other expression forms require a separately justified independent reference rule'
    )
    return OPERATORS[type(node.op)](
        arithmetic(node.left, names, number), arithmetic(node.right, names, number)
    )


@cache
def tree(text):
    return ast.parse(text, mode='eval').body


def normalized(text):
    return ''.join(text.split()).casefold()


@cache
def declared_groups():
    data = Path(__file__).with_name('declared-space-groups.symtab').read_bytes()
    assert hashlib.sha256(data).hexdigest() == DECLARED_TABLE_SHA256, (
        'The independent original declared setting/orbit input must remain frozen'
    )
    groups, aliases = {}, {}
    current, section = None, ''
    for line in data.decode().splitlines():
        if not line or line.startswith('#'):
            continue
        if line == '@@space_group':
            current = {'operators': [], 'sites': {}}
        elif line == '@@aliases':
            section = 'aliases'
        elif section == 'aliases':
            name, it, code = line.split('\t')
            aliases.setdefault(normalized(name), []).append((int(it), code.casefold()))
        elif line.startswith('@it_number '):
            current['it'] = int(line.split(maxsplit=1)[1])
        elif line.startswith('@it_coordinate_system_code '):
            current['code'] = line.split(maxsplit=1)[1].casefold()
            key = (current['it'], current['code'])
            assert key not in groups, 'Every original declared setting is unique'
            groups[key] = current
        elif line.startswith('['):
            section = line
        elif line.startswith('@'):
            continue
        elif section == '[operators]':
            current['operators'].append(line)
        elif section == '[wyckoff]':
            letter, multiplicity, _oriented, _abstract, representative, free = line.split()
            current['sites'][letter] = (int(multiplicity), representative, int(free))
    return groups, aliases


@cache
def declared_short_aliases():
    data = Path(__file__).with_name('declared-space-groups.symtab').read_bytes()
    assert hashlib.sha256(data).hexdigest() == DECLARED_TABLE_SHA256, (
        'The exact short-name table bytes must remain frozen before parsing'
    )
    rows = data.decode()
    aliases = {}
    for line in rows.split('@@aliases\n', 1)[1].splitlines():
        if not line or line.startswith('#'):
            continue
        name, it, code = line.split('\t')
        tokens = name.split()
        real_direction = any(symbol != '1' for symbol in tokens[1:])
        short = normalized(
            ' '.join(
                symbol
                for index, symbol in enumerate(tokens)
                if index == 0 or symbol != '1' or not real_direction
            )
        )
        aliases.setdefault(short, []).append((int(it), code.casefold()))
    return aliases


def setting(structure):
    groups, aliases = declared_groups()
    name = normalized(structure.space_group.name_h_m)
    code = structure.space_group.coord_system_code.casefold() or '-'
    if ':' in name:
        name, suffix = name.rsplit(':', 1)
        assert code in {'-', suffix}, 'A declared setting name and code cannot conflict'
        code = suffix
    candidates = sorted(set(aliases.get(name, [])))
    if not candidates:
        candidates = sorted(set(declared_short_aliases().get(name, [])))
    if code != '-':
        candidates = [key for key in candidates if key[1] == code]
    assert len(candidates) == 1, (
        'A reference must identify one declared setting, never guess a default or another origin'
    )
    return candidates[0], groups[candidates[0]]


def coordinates(text, names):
    parts = text.split(',')
    assert len(parts) == 3, 'Declared coordinate inputs retain exactly three axes'
    return tuple(arithmetic(tree(part), names, Fraction) for part in parts)


@cache
def fixed_declaration(key, letter):
    group = declared_groups()[0][key]
    assert letter in group['sites'], 'A declared letter belongs to its exact setting'
    multiplicity, text, freedom = group['sites'][letter]
    if freedom:
        return None
    representative = coordinates(text, {})
    names = dict(zip(('x', 'y', 'z'), representative, strict=True))
    orbit = tuple(
        sorted({tuple(value % 1 for value in coordinates(op, names)) for op in group['operators']})
    )
    assert len(orbit) == multiplicity, (
        'Full declared operators retain the fixed orbit multiplicity'
    )
    return representative, orbit


def owned_experiment_shape(experiment, bind):
    links = list(experiment.linked_structures)
    assert len({row.structure_id for row in links}) == len(links), (
        'Linked-scale rows retain unique ids within their actual bank'
    )
    for row in links:
        bind(f'{experiment.name}.linked_structure.{row.structure_id}.scale', row.scale)
    extinction = experiment.extinction
    extinction_shape = None
    if extinction is not None:
        presence = []
        for field in EXTINCTION:
            parameter = getattr(extinction, field)
            presence.append((field, parameter is not None))
            if parameter is not None:
                bind(f'{experiment.name}.extinction.{field}', parameter)
        extinction_shape = (extinction.type, extinction.mosaic_distribution, tuple(presence))
    return tuple((row.structure_id, row.enabled) for row in links), extinction_shape


def model_inputs(project):
    parameters = list(project.parameters)
    positions = {id(p): index for index, p in enumerate(parameters)}
    assert len(positions) == len(parameters), 'Each model parameter retains one storage identity'
    slots, lookups, shapes, optional = {}, {}, [], []

    def bind(path, parameter):
        assert id(parameter) in positions and path not in slots, (
            'Every declared slot names one parameter in this exact owning model'
        )
        slots[path] = positions[id(parameter)]
        lookups[path] = path

    for structure in project.structures:
        key = setting(structure)[0]
        sites, tensors = list(structure.atom_sites), list(structure.atom_site_aniso)
        assert len({site.id for site in sites}) == len(sites), 'Site ids are unique in each owner'
        assert len({row.id for row in tensors}) == len(tensors), (
            'Tensor ids are unique in each owner'
        )
        assert {row.id for row in tensors} == {
            site.id for site in sites if site.adp_type in ANISOTROPIC
        }, 'Tensor rows belong exactly to their declared anisotropic sites'
        shapes.append((
            structure.name,
            key,
            tuple((s.id, s.type_symbol, s.adp_type, s.wyckoff_letter) for s in sites),
        ))
        for field in CELL:
            bind(f'{structure.name}.cell.{field}', getattr(structure.cell, field))
        for site in sites:
            for field in SITE:
                path = f'{structure.name}.atom_site.{site.id}.{field}'
                bind(path, getattr(site, field))
                lookups[f'structure.{structure.name}.{site.id}.{field}'] = path
        for row in tensors:
            for suffix in TENSOR:
                bind(
                    f'{structure.name}.atom_site_aniso.{row.id}.adp_{suffix}',
                    getattr(row, 'adp_' + suffix),
                )
    assert len({e.name for e in project.experiments}) == len(project.experiments), (
        'Experiment bank names retain unique ownership'
    )
    for experiment in project.experiments:
        family = (
            experiment.experiment_type.beam_mode.name,
            experiment.experiment_type.radiation_probe.name,
        )
        shapes.append((experiment.name, family, *owned_experiment_shape(experiment, bind)))
        if family == ('CONSTANT_WAVELENGTH', 'XRAY'):
            for field in OPTIONAL_XRAY:
                parameter = getattr(experiment.instrument, field)
                if parameter is not None:
                    path = f'{experiment.name}.instrument.{field}'
                    bind(path, parameter)
                    optional.append((
                        path,
                        experiment.name,
                        field,
                        parameter.start_value is not None,
                    ))
    assert len(set(slots.values())) == len(slots), (
        'Distinct declared slots cannot share parameter storage'
    )
    aliases = tuple((row.id, row.parameter_unique_name) for row in project.analysis.aliases)
    constraints = tuple(
        (row.id, row.expression, row.enabled) for row in project.analysis.constraints
    )
    identity = (tuple(sorted(slots.items())), tuple(shapes), aliases, constraints)
    return parameters, slots, lookups, optional, identity


def declared_relations(identity, slots, lookups):
    aliases, constraints = identity[2], identity[3]
    assert len({name for name, _path in aliases}) == len(aliases), 'Alias ids remain unique'
    indices = {}
    for name, path in aliases:
        assert path in lookups, 'Every declared alias has an independently owned schema path'
        indices[name] = slots[lookups[path]]
    graph = {}
    for _name, statement, enabled in constraints:
        assert isinstance(enabled, bool), 'Enabled state is an explicit declaration'
        if not enabled:
            continue
        lhs, separator, rhs = statement.partition('=')
        lhs = lhs.strip()
        assert separator and lhs in indices, 'A relation targets a declared alias'
        target = indices[lhs]
        assert target not in graph, 'Two declarations cannot set the same target'
        graph[target] = tree(rhs.strip())
    return indices, graph


def apply_declared(values, indices, graph, *, blocked=frozenset()):
    done, busy = set(), set()

    def visit(target):
        assert target not in busy, 'Declared dependency cycles cannot produce a saved reference'
        if target in done:
            return
        busy.add(target)
        names = {}
        for node in ast.walk(graph[target]):
            if isinstance(node, ast.Name):
                assert node.id in indices, 'A relation cannot name a missing or changed alias'
                source = indices[node.id]
                assert source not in blocked, (
                    'A derived-metric leader needs its own independent exact relation'
                )
                if source in graph:
                    visit(source)
                names[node.id] = values[source][0]
        value = arithmetic(graph[target], names)
        assert math.isfinite(value), 'Declared completion must retain a finite scalar value'
        assert values[target][2] is False, 'A declared dependent keeps its cleared free flag'
        values[target] = (value, values[target][1], False)
        busy.remove(target)
        done.add(target)

    for target in graph:
        visit(target)


def fixed_values(project, slots):
    result = {}
    for structure in project.structures:
        key = setting(structure)[0]
        for site in structure.atom_sites:
            if site.wyckoff_letter in {'', '.', '?'}:
                continue
            declaration = fixed_declaration(key, site.wyckoff_letter)
            if declaration is None:
                continue
            representative, orbit = declaration
            xyz = tuple(getattr(site, 'fract_' + axis).value % 1 for axis in ('x', 'y', 'z'))
            assert xyz in {tuple(float(value) for value in point) for point in orbit}, (
                'A fully fixed site must belong to its declared orbit before projection'
            )
            for axis, value in zip(('x', 'y', 'z'), representative, strict=True):
                result[slots[f'{structure.name}.atom_site.{site.id}.fract_{axis}']] = float(value)
    return result
