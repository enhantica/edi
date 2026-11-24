"""Cell edits and saved values share a range with distinct admission rules."""

import math
import re
import shutil
import warnings
from pathlib import Path

import edi
import pytest

FIXTURE = Path(__file__).resolve().parents[2] / 'fixtures/loop_parameter_ids/line-segment'
LENGTHS = ('length_a', 'length_b', 'length_c')
MAX_LENGTH = 99.0
ABOVE_MAX = math.nextafter(MAX_LENGTH, math.inf)


def test_cell_length_limits_match_at_python_factory_and_file_boundaries(tmp_path, capfd):
    directory = shutil.copytree(FIXTURE, tmp_path / 'bounds')
    path = directory / 'structures/phase.edi'
    original = path.read_text(encoding='utf-8')
    for name in LENGTHS:
        parameter = getattr(edi.Structure().cell, name)
        parameter.value = MAX_LENGTH
        assert parameter.value == MAX_LENGTH, 'Python assignment admits exactly 99 Å'
        with pytest.raises(ValueError, match=rf'\b{name}\b'):
            parameter.value = ABOVE_MAX
        assert parameter.value == MAX_LENGTH, 'Refused Python edits preserve the accepted length'

        structure = edi.StructureFactory.from_dict({'cell': {name: MAX_LENGTH}})
        assert getattr(structure.cell, name).value == MAX_LENGTH, (
            'Factory dictionaries admit exactly 99 Å'
        )
        with pytest.raises(ValueError, match=rf'\b{name}\b'):
            edi.StructureFactory.from_dict({'cell': {name: ABOVE_MAX}})

        for value, expected_warnings in ((MAX_LENGTH, []), (ABOVE_MAX, [name])):
            declarations = re.sub(
                rf'^(_cell\.{name}) .*$', rf'\g<1> {value!r}', original, flags=re.MULTILINE
            )
            path.write_text(declarations, encoding='utf-8')
            capfd.readouterr()
            with warnings.catch_warnings(record=True) as received:
                warnings.simplefilter('always')
                project = edi.Project.load(directory)
            emitted = capfd.readouterr()
            evidence = '\n'.join([
                *(str(item.message) for item in received),
                emitted.err,
                emitted.out,
            ])
            warned_lengths = re.findall(r'\bcell\.(length_[abc])\b[^\n]*\boutside\b', evidence)
            assert getattr(project.structure.cell, name).value == value, (
                'Loading keeps the exact saved cell length, including above the editing ceiling'
            )
            assert warned_lengths == expected_warnings, (
                'Loading warns once and names the cell length just above 99 Å'
            )
            assert path.read_text(encoding='utf-8') == declarations, (
                'A project load leaves the original cell declaration bytes intact'
            )
