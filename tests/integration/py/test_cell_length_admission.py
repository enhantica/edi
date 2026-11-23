"""The cell-length boundary applies to every public entrance."""

import math
import re
import shutil
from pathlib import Path

import edi

FIXTURE = Path(__file__).resolve().parents[2] / 'fixtures/loop_parameter_ids/line-segment'
LENGTHS = ('length_a', 'length_b', 'length_c')
MAX_LENGTH = 99.0
ABOVE_MAX = math.nextafter(MAX_LENGTH, math.inf)


def admitted_length(entrance, parameter, name, value, directory):
    if entrance == 'Python set':
        parameter.value = value
        return parameter.value
    if entrance == 'factory dict':
        structure = edi.StructureFactory.from_dict({'cell': {name: value}})
        return getattr(structure.cell, name).value
    project = edi.Project.load(directory)
    return getattr(project.structure.cell, name).value


def test_cell_length_limits_match_at_python_factory_and_file_boundaries(tmp_path):
    directory = shutil.copytree(FIXTURE, tmp_path / 'bounds')
    path = directory / 'structures/phase.edi'
    original = path.read_text(encoding='utf-8')
    failures = []
    for name in LENGTHS:
        structure_for_set = edi.Structure()
        cell = structure_for_set.cell
        for value, accepted in ((MAX_LENGTH, True), (ABOVE_MAX, False)):
            declarations = re.sub(
                rf'^(_cell\.{name}) .*$', rf'\g<1> {value!r}', original, flags=re.MULTILINE
            )
            path.write_text(declarations, encoding='utf-8')

            for entrance in ('Python set', 'factory dict', '.edi load'):
                parameter = getattr(cell, name)
                previous = parameter.value
                try:
                    actual = admitted_length(entrance, parameter, name, value, directory)
                except (edi.DomainValidationError, edi.IoError, ValueError, TypeError) as error:
                    if accepted:
                        failures.append((name, entrance, value, str(error)))
                    if entrance == 'Python set':
                        assert parameter.value == previous, 'Refused Python edits preserve length'
                else:
                    if not accepted or actual != value:
                        failures.append((name, entrance, value, f'admitted {actual!r}'))
            assert path.read_text(encoding='utf-8') == declarations, (
                'A project load leaves the original cell declaration bytes intact'
            )
    assert not failures, (
        'Every length entrance admits exactly 99 Å without clamping and refuses the next '
        f'representable value above 99 Å. Boundary disagreements: {failures!r}'
    )
