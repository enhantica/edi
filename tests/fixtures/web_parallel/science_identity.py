"""Identity beside immutable mixed raw/written scientific coordinates (review657).

This module does not parse product files, alter a bank, select tolerances, or run
a fit. The caller supplies independently read block names beside the existing
scientific list; the old list and conditioning coordinates remain untouched.
"""

import math
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import PurePosixPath

from tests.fixtures.saved_spelling.reference import NUMBER, VALUE_SU, decode, rounded_token
from tests.fixtures.web_parallel.numeric import uncertainty_tolerances

_TAG = re.compile(r'_[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\Z')
_LOOPS = {
    '_atom_site': ('_atom_site.id',),
    '_atom_site_aniso': ('_atom_site_aniso.id',),
    '_background': ('_background.id',),
    '_data': (),
    '_fit_result_bank': ('_fit_result_bank.experiment_id',),
    '_fit_result_phase': (
        '_fit_result_phase.experiment_id',
        '_fit_result_phase.structure_id',
    ),
    '_linked_structure': ('_linked_structure.structure_id',),
}
_SCALARS = {
    '_cell',
    '_space_group',
    '_peak',
    '_pd_instr',
    '_pd_calib',
    '_scale',
    '_fit_result',
    '_instrument',
}
_CALIBRATION = {
    'calib_twotheta_offset',
    'calib_d_to_tof_offset',
    'calib_d_to_tof_linear',
    'calib_d_to_tof_quadratic',
    'calib_d_to_tof_reciprocal',
}


@dataclass(frozen=True)
class Cell:
    document: str
    block: str
    category: str
    row: tuple
    tag: str


@dataclass
class Index:
    blocks: dict
    cells: dict = field(default_factory=dict)
    coordinates: dict = field(default_factory=dict)
    loop_order: dict = field(default_factory=dict)
    row_keys: set = field(default_factory=set)
    data_ids: set = field(default_factory=set)


def _document(name):
    if not isinstance(name, str) or not name:
        raise ValueError('science identity needs a canonical document path')
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or '..' in path.parts
        or path.as_posix() != name
        or path.suffix != '.edi'
    ):
        raise ValueError('science identity needs a canonical document path')


def _shape(row):
    if not isinstance(row, list) or not row or len(row) % 2:
        raise ValueError('science identity needs complete tag/value rows')
    count = len(row) // 2
    tags, values = row[:count], row[count:]
    if any(not isinstance(token, str) for token in row):
        raise ValueError('science identity needs string tokens')
    if any(not _TAG.fullmatch(tag) for tag in tags) or len(set(tags)) != count:
        raise ValueError('science identity refuses missing/duplicate/invalid columns')
    categories = {tag.partition('.')[0] for tag in tags}
    if len(categories) != 1:
        raise ValueError('science identity refuses mixed-category rows')
    return categories.pop(), tags, dict(zip(tags, values, strict=True))


def _row_identity(category, values, ordinal):
    if category == '_data':
        if sum(tag in values for tag in ('_data.two_theta', '_data.time_of_flight')) != 1:
            raise ValueError('science data identity needs one declared abscissa')
        identity = (('ordinal', str(ordinal)),)
        if '_data.id' in values:
            identity += (('_data.id', values['_data.id']),)
        return identity
    required = _LOOPS.get(category)
    if required is None or any(tag not in values for tag in required):
        raise ValueError('science loop identity needs its declared row keys')
    identity = tuple((tag, values[tag]) for tag in required)
    if any(not value or value in {'?', '.'} for _, value in identity):
        raise ValueError('science identity refuses unavailable row keys')
    return identity


def _record(index, document, row_number, row):
    category, tags, values = _shape(row)
    scalar = len(tags) == 1 and (category in _SCALARS or tags[0] == '_background.type')
    identity = ()
    if not scalar:
        order = index.loop_order.setdefault((document, category), [])
        identity = _row_identity(category, values, len(order))
        row_key = document, category, identity
        if row_key in index.row_keys:
            raise ValueError('science identity refuses duplicate loop rows')
        index.row_keys.add(row_key)
        if category == '_data' and '_data.id' in values:
            data_id = document, values['_data.id']
            if data_id in index.data_ids:
                raise ValueError('science identity refuses duplicate data ids')
            index.data_ids.add(data_id)
        order.append(identity)
    for column, tag in enumerate(tags):
        key = Cell(document, index.blocks[document], category, identity, tag)
        if key in index.cells:
            raise ValueError('science identity refuses duplicate scalar/loop cells')
        index.cells[key] = values[tag]
        index.coordinates[document, row_number, len(tags) + column] = key


def _foreign_keys(index):
    banks = {name for path, name in index.blocks.items() if path.startswith('experiments/')}
    structures = {name for path, name in index.blocks.items() if path.startswith('structures/')}
    for key, value in index.cells.items():
        if (
            key.tag in {'_fit_result_bank.experiment_id', '_fit_result_phase.experiment_id'}
            and value not in banks
        ):
            raise ValueError('science identity has an unknown experiment bank')
        if (
            key.tag in {'_linked_structure.structure_id', '_fit_result_phase.structure_id'}
            and value not in structures
        ):
            raise ValueError('science identity has an unknown structure link')


def semantic_index(scientific, block_names):
    """Retain every cell and coordinate; ignore category order only, not loop order."""
    if not scientific or scientific.keys() != block_names.keys():
        raise ValueError('science identity needs every declared document/block')
    identities = set()
    for name, block in block_names.items():
        _document(name)
        if not isinstance(block, str) or block in {'?', '.'}:
            raise ValueError('science identity needs an actual block name')
        if not block and name != 'analysis/analysis.edi':
            raise ValueError('science identity needs an actual block name')
        identity = PurePosixPath(name).parent.as_posix(), block
        if identity in identities:
            raise ValueError('science identity refuses duplicate block owners')
        identities.add(identity)
    index = Index(dict(block_names))
    for name, rows in scientific.items():
        if not isinstance(rows, list) or not rows:
            raise ValueError('science identity refuses an empty document')
        for row_number, row in enumerate(rows):
            _record(index, name, row_number, row)
    _foreign_keys(index)
    return index


def align_to_frozen(actual, frozen, *, actual_blocks, frozen_blocks):
    """Return actual values in OLD coordinates, without sorting or rewriting the bank."""
    expected = semantic_index(frozen, frozen_blocks)
    observed = semantic_index(actual, actual_blocks)
    if (
        observed.blocks != expected.blocks
        or observed.cells.keys() != expected.cells.keys()
        or observed.loop_order != expected.loop_order
    ):
        raise ValueError('science identity changed document/bank/row/column inventory or order')
    aligned = {name: [list(row) for row in rows] for name, rows in frozen.items()}
    for (document, row, token), key in expected.coordinates.items():
        aligned[document][row][token] = observed.cells[key]
    return aligned


def conditioning_semantics(frozen, conditioning, block_names):
    """Authenticate unchanged OLD coordinates, then attach keys beside those coordinates."""
    uncertainty_tolerances(frozen, conditioning)
    index = semantic_index(frozen, block_names)
    return {
        (document, row, token): (
            index.coordinates[document, row, token],
            column,
            conditioning['labels'][column],
        )
        for document, row, token, column in conditioning['bindings']
    }


def frozen_domains(fixture, block_names):
    """The bank is mixed: only recorded substitutions are raw native parameters."""
    index = semantic_index(fixture['scientific'], block_names)
    domains = dict.fromkeys(index.coordinates, 'historical-written')
    seen = set()
    for document, row, token, _column, _written, raw in fixture['native_precision_bindings']:
        coordinate = document, row, token
        if coordinate in seen or coordinate not in domains:
            raise ValueError('science provenance has an invalid/duplicate substitution')
        if fixture['scientific'][document][row][token] != raw:
            raise ValueError('science provenance substitution differs from the frozen token')
        domains[coordinate] = 'native-raw-parameter'
        seen.add(coordinate)
    return domains


def projected_parameter(token, declared_rule):
    """Use FIRST saved_spelling/Decimal reference; retain absent/zero/free distinctions.

    This projects positive fitted SUs only. Fixed/zero/absent six-digit file
    projection is deliberately not claimed by this first unit.
    """
    rule = 'iucr_99' if declared_rule is None else declared_rule
    if rule not in {'iucr_19', 'iucr_99'}:
        raise ValueError('science projection needs an absent/default or declared IUCr rule')
    match = VALUE_SU.fullmatch(token.encode())
    if match is not None:
        value, uncertainty = decode(token)
        if not math.isfinite(value) or (
            uncertainty is not None and (not math.isfinite(uncertainty) or uncertainty < 0)
        ):
            raise ValueError('science projection refuses nonfinite/negative operands')
        return rounded_token(match, rule).decode() if uncertainty else token
    if not re.fullmatch(NUMBER, token) or not Decimal(token).is_finite():
        raise ValueError('science projection needs a complete parameter token')
    return token


@dataclass(frozen=True)
class RawParameter:
    key: Cell
    column: int
    value: float
    uncertainty: float


def _omitted_key(label, banks):
    pieces = label.rsplit('.', 1)
    bank, member = pieces if len(pieces) == 2 else (None, pieces[0])
    if member != 'scale' and not member.startswith('calib_'):
        return None
    matches = [
        (path, block, links)
        for path, (block, links) in banks.items()
        if bank is None or block == bank
    ]
    if len(matches) != 1:
        raise ValueError('raw omitted parameter needs one declared owning bank')
    document, block, links = matches[0]
    _document(document)
    if (
        not document.startswith('experiments/')
        or not block
        or block in {'?', '.'}
        or not links
        or any(not link or link in {'?', '.'} for link in links)
    ):
        raise ValueError('raw omitted parameter needs declared experiment/link storage')
    if member == 'scale':
        if len(links) != 1 or len(set(links)) != len(links) or not links[0]:
            raise ValueError('raw scale label cannot choose an ambiguous structure link')
        return Cell(
            document,
            block,
            '_linked_structure',
            (('_linked_structure.structure_id', links[0]),),
            '_linked_structure.scale',
        )
    if member not in _CALIBRATION:
        raise ValueError('raw omitted calibration has no admitted storage declaration')
    return Cell(document, block, '_instrument', (), '_instrument.' + member)


def omitted_raw_parameters(raw, banks):
    """Bind scale/calibration by label + actual bank/link, never rounded-value matching."""
    labels, values, covariance = raw['labels'], raw['values'], raw['covariance']
    count = len(labels)
    if any(not isinstance(label, str) or not label for label in labels):
        raise ValueError('raw omitted parameter needs actual string labels')
    if (
        not count
        or len(set(labels)) != count
        or len(values) != count
        or len(covariance) != count**2
    ):
        raise ValueError('raw omitted parameter needs complete unique labeled vectors')
    if any(not math.isfinite(value) for value in [*values, *covariance]):
        raise ValueError('raw omitted parameter refuses nonfinite independent capture')
    result = {}
    used = set()
    for column, label in enumerate(labels):
        key = _omitted_key(label, banks)
        if key is None:
            continue
        diagonal = covariance[column * count + column]
        if diagonal < 0 or key in used:
            raise ValueError('raw omitted parameter has invalid covariance/storage identity')
        result[label] = RawParameter(key, column, values[column], math.sqrt(diagonal))
        used.add(key)
    return result
