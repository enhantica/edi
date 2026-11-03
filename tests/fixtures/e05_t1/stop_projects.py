"""Declared stop inputs: a zero column and a domain-blocked positive-gain column."""

import shutil
from pathlib import Path

import gemmi

from tests.fixtures.project_categories.historical_bytes import units


def background_prefix(text):
    """Replace only background/data, retaining the saved experiment's full typed input."""
    document = gemmi.cif.read_string(text)
    document.check_for_duplicates()
    block = document.sole_block()
    schema = block.find_pair('_edi.schema_version')
    if schema is None or gemmi.cif.as_string(schema[1]) not in {'2', '3', '4'}:
        message = 'the saved experiment must retain one supported _edi.schema_version'
        raise ValueError(message)
    if block.find_pair('_background.type') is None:
        message = 'the LBCO stop input must declare its background'
        raise ValueError(message)
    # Gemmi marks actual pair/loop start lines, including loop_ itself. Slice
    # original text: no writer/default, rounded parameter or invented profile.
    # Gemmi memory_input counts LF bytes, not Python's additional Unicode
    # splitlines boundaries inside legal comments and semicolon text. Preserve
    # every original character while indexing that exact physical-line domain.
    lines = text.split('\n')
    lines = [line + '\n' for line in lines[:-1]] + lines[-1:]
    items = list(block)
    previous_line = 0
    for item in items:
        token = item.pair[0] if item.pair is not None else 'loop_' if item.loop else None
        line = item.line_number
        if (
            token is None
            or not previous_line < line <= len(lines)
            or lines[line - 1].split(maxsplit=1)[:1] != [token]
        ):
            message = 'stop fixture requires canonical physical item starts'
            raise ValueError(message)
        previous_line = line
    retained = lines[: items[0].line_number - 1]
    for index, item in enumerate(items):
        tags = (
            [item.pair[0]] if item.pair is not None else list(item.loop.tags) if item.loop else []
        )
        replaced = [tag.startswith(('_background.', '_data.')) for tag in tags]
        if any(replaced):
            if not all(replaced):
                message = 'stop fixture cannot replace a loop mixing owned and retained categories'
                raise ValueError(message)
            continue
        end = items[index + 1].line_number - 1 if index + 1 < len(items) else len(lines)
        retained.extend(lines[item.line_number - 1 : end])
    return ''.join(retained)


def materialize(engine, source, target, *, stalled):
    """Write a disposable LBCO input with an independently declared stop condition."""
    target = Path(target)
    if target.exists():
        shutil.rmtree(target)
    project = engine.Project.load(str(source))
    for parameter in project.parameters:
        parameter.free = False
    for site in project.structure.atom_sites:
        site.occupancy.value = 0.0
    driver = project.structure.atom_sites[0].adp_iso
    driver.value = 0.0 if stalled else 0.5
    driver.free = True
    project.save_as(str(target))
    (target / 'README.md').unlink(missing_ok=True)
    if not stalled:
        return target

    experiment = target / 'experiments/hrpt.edi'
    head, entries, separators, tail = units(experiment.read_bytes())
    if not any(key == b'_background.type' for key, _ in entries):
        message = 'the LBCO stop input must declare its background'
        raise ValueError(message)
    retained = (
        head
        + b''.join(
            separator + body
            for (key, body), separator in zip(entries, separators, strict=True)
            if key.removeprefix(b'loop:').split(b'.', 1)[0] not in {b'_background', b'_data'}
        )
        + tail
    )
    experiment.write_bytes(
        retained.rstrip(b'\n')
        + b'\n\n_background.type line-segment\n'
        + b"""

loop_
_background.id
_background.position
_background.intensity
left 35 0
right 85 0

loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
40 -1 1
60 -1 1
80 -1 1
"""
    )
    (target / 'analysis/analysis.edi').write_text("""_edi.schema_version 3
_fitting_mode.type single
_minimizer.type crysta
_minimizer.max_iterations 3
_minimizer.chi_square_tolerance 1e-6

loop_
_alias.id
_alias.parameter_unique_name
driver lbco.atom_site.La.adp_iso
left hrpt.background.left.intensity
right hrpt.background.right.intensity
fraction hrpt.preferred_orientation.lbco.march_random_fract

loop_
_constraint.id
_constraint.expression
_constraint.enabled
left_value "left = driver" true
right_value "right = driver" true
fraction_value "fraction = driver" true
""")
    return target
