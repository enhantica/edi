"""Compare immutable writer bytes across the declared Joint/row-ID transitions.

Only the exact non-Joint weights block and fit-state identity cells may differ.
Fit-state slots retain their historical compact grammar; public alias names use
category and field names. Every numeric value and unrelated byte stays compared.
"""

import re
from pathlib import Path

from tests.fixtures.stored_loop_ids.historical_bytes import TOKEN, loop_ids

WEIGHTS = re.compile(
    rb'\nloop_\n_joint_fit.experiment_id\n_joint_fit.weight\n'
    rb'(?:[^\s_#][^\s]*[ \t]+[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\n)+'
)


def without_nonjoint_weights(previous):
    modes = re.findall(rb'(?m)^_fitting_mode.type\s+(\S+)\s*$', previous)
    if modes == [b'joint']:
        return previous
    if modes not in ([b'single'], [b'sequential'], [b'independent'], []):
        message = 'The frozen weights transition needs one declared supported fitting mode'
        raise ValueError(message)
    matches = list(WEIGHTS.finditer(previous))
    if len(matches) > 1:
        message = 'The frozen writer must carry at most one exact weights loop'
        raise ValueError(message)
    return WEIGHTS.sub(b'', previous, count=1)


def fit_rows(data):
    tags = []
    start = None
    offsets = []
    offset = 0
    for line in data.splitlines(keepends=True):
        word = line.strip()
        if word == b'loop_':
            tags = []
            start = None
        elif word.startswith(b'_') and start is None:
            tags.append(word)
        elif tags and word and not word.startswith(b'#'):
            if b'_fit_parameter.id' in tags:
                cells = list(TOKEN.finditer(line))
                if len(cells) != len(tags):
                    message = 'The frozen fit-state transition needs complete rows'
                    raise ValueError(message)
                cell = cells[tags.index(b'_fit_parameter.id')]
                offsets.append((offset + cell.start(), offset + cell.end(), cell.group()))
                start = offset
            elif start is not None:
                tags = []
        offset += len(line)
    return offsets


def old_fit_state_bytes(previous, emitted, source):  # noqa: PLR0914 - exact byte transition
    before = fit_rows(previous)
    after = fit_rows(emitted)
    if len(before) != len(after):
        message = 'An ID migration cannot change the frozen fit-state row population'
        raise ValueError(message)
    edits = []
    for (_, _, old), (start, end, new) in zip(before, after, strict=True):
        if old == new:
            continue
        ordinal = re.fullmatch(rb'([^.]+)\.background\[(\d+)\]', old)
        scale = re.fullmatch(rb'([^.]+)\.(scale|march_r|march_random_fract)', old)
        if ordinal:
            name, index = ordinal.groups()
            experiment = (Path(source) / 'experiments' / (name.decode() + '.edi')).read_bytes()
            rows = loop_ids(experiment, b'_background')
            if int(index) >= len(rows):
                message = 'The historical fit-state slot must reach its declared input row'
                raise ValueError(message)
            prefix = name + b'.background.' + rows[int(index)][2]
            accepted = {prefix, prefix + b'.intensity'}
        elif scale:
            name, field = scale.groups()
            experiment = (Path(source) / 'experiments' / (name.decode() + '.edi')).read_bytes()
            # Frozen single-phase inputs declare one link. Never guess a phase from a live model.
            matches = re.findall(
                rb'loop_\n_linked_structure.structure_id\n_linked_structure.scale\n'
                rb'([^\s]+)\s+[^\n]+\n',
                experiment,
            )
            if len(matches) != 1:
                message = 'The compact phase-slot migration needs one frozen declared link'
                raise ValueError(message)
            phase = matches[0]
            category = b'linked_structure' if field == b'scale' else b'preferred_orientation'
            accepted = {
                name + b'.' + phase + b'.' + field,
                name + b'.' + category + b'.' + phase + b'.' + field,
            }
        else:
            message = 'The ID transition cannot exempt an unrelated fit-state identity'
            raise ValueError(message)
        if new not in accepted:
            message = 'A migrated fit-state slot must name exactly its frozen row ID'
            raise ValueError(message)
        edits.append((start, end, old))
    for start, end, old in reversed(edits):
        emitted = emitted[:start] + old + emitted[end:]
    return emitted


def current_fit_state_bytes(previous, source):
    """Convert only archived fit-state keys using the archive's declared input rows.

    This prepares a current-format disposable input; it never allows an older
    spelling through a product reader or obtains any numeric cell from an engine.
    """
    edits = []
    for start, end, key in fit_rows(previous):
        ordinal = re.fullmatch(rb'([^.]+)\.background\[(\d+)\]', key)
        phase_slot = re.fullmatch(rb'([^.]+)\.(scale|march_r|march_random_fract)', key)
        if ordinal:
            block, index = ordinal.groups()
            experiment = (Path(source) / 'experiments' / (block.decode() + '.edi')).read_bytes()
            rows = loop_ids(experiment, b'_background')
            if int(index) >= len(rows):
                message = 'An archived slot must identify a complete declared background row'
                raise ValueError(message)
            current = block + b'.background.' + rows[int(index)][2]
        elif phase_slot:
            block, field = phase_slot.groups()
            experiment = (Path(source) / 'experiments' / (block.decode() + '.edi')).read_bytes()
            phases = re.findall(
                rb'loop_\n_linked_structure.structure_id\n_linked_structure.scale\n'
                rb'([^\s]+)\s+[^\n]+\n',
                experiment,
            )
            if len(phases) != 1:
                message = 'An archived phase slot must identify its one declared structure'
                raise ValueError(message)
            current = block + b'.' + phases[0] + b'.' + field
        else:
            continue
        edits.append((start, end, current))
    for start, end, current in reversed(edits):
        previous = previous[:start] + current + previous[end:]
    return previous
