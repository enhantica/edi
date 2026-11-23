# SPDX-License-Identifier: BSD-3-Clause
"""A long-axis hexagonal cell can be entered, calculated and fitted.

A W-type hexaferrite has a = b = 5.90 Å and c = 32.2 Å. The pattern is calculated at those
values, used as the measurement, and fitted back from a shifted start.

Run with python -m pytest tests/fixtures/long_cell_fit/check_long_cell.py
--noconftest -o addopts= -q after building the native extension.
"""

import math

import easydiffraction as edi
import pytest

A, C = 5.90, 32.2

CIF = f"""data_ferrite
_edi.schema_version 3
_cell.length_a {A}
_cell.length_b {A}
_cell.length_c {C}
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 120
_space_group.name_h_m "P 63/m m c"
_space_group.coord_system_code h
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.wyckoff_letter
_atom_site.occupancy
_atom_site.adp_iso
_atom_site.adp_type
Ba Ba 0 0 0.25 b 1 0.5 Biso
Fe1 Fe 0 0 0 a 1 0.5 Biso
Fe2 Fe 0.333333 0.666667 0.03 f 1 0.5 Biso
O1 O 0 0 0.1 e 1 0.5 Biso
O2 O 0.333333 0.666667 0.16 f 1 0.5 Biso
"""

GRID = [10.0 + 0.05 * i for i in range(1601)]  # 10-90 deg 2theta


def _structure():
    structure = edi.StructureFactory.from_cif_str(CIF)
    structure.name = 'ferrite'
    return structure


def _project(structure, intensity, su):
    experiment = edi.ExperimentFactory.from_dict({
        'experiment_type': {'beam_mode': 'constant wavelength'},
        'peak': {
            'type': 'cwl-tch-pseudo-voigt',
            'broad_gauss_u': 0.1,
            'broad_gauss_v': -0.1,
            'broad_gauss_w': 0.1,
            'broad_lorentz_x': 0.0,
            'broad_lorentz_y': 0.05,
        },
        'instrument': {'setup_wavelength': 1.494, 'calib_twotheta_offset': 0.0},
        'linked_structure': {'scale': 1.0},
        'background': [(10.0, 10.0), (90.0, 10.0)],
    })
    experiment.name = 'hrpt'
    experiment.data = edi.PdCwlData(two_theta=GRID, intensity_meas=intensity, intensity_meas_su=su)
    project = edi.Project()
    project.structure = structure
    project.experiment = experiment
    return project


def _set(owner, name, value, *, free=None):
    parameter = getattr(owner, name)
    parameter.value = value
    if free is not None:
        parameter.free = free
    setattr(owner, name, parameter)


def test_long_cell_loads_from_cif_and_dict():
    cell = _structure().cell
    assert (cell.length_a.value, cell.length_b.value, cell.length_c.value) == (A, A, C)
    built = edi.StructureFactory.from_dict({'cell': {'length_a': A, 'length_c': C}})
    assert built.cell.length_c.value == C


def test_python_setter_admits_up_to_99_angstroms():
    cell = _structure().cell
    _set(cell, 'length_c', 99.0)
    assert cell.length_c.value == 99.0
    with pytest.raises(ValueError, match='admissible range'):
        _set(cell, 'length_c', 99.5)


def test_long_cell_calculates_and_fits_back():
    ones = [1.0] * len(GRID)
    reference = _project(_structure(), ones, ones)
    reference.calculate()
    calc = list(reference.experiment.data.intensity_calc)
    assert len(calc) == len(GRID)
    assert max(calc) > 10 * min(calc), 'the long cell must give Bragg peaks above background'

    structure = _structure()
    _set(structure.cell, 'length_a', 5.89, free=True)
    _set(structure.cell, 'length_c', 32.15, free=True)
    project = _project(structure, calc, [math.sqrt(max(y, 1.0)) for y in calc])
    outcome = project.fit()
    assert outcome.status.name.lower() == 'done'
    cell = project.structure.cell
    assert cell.length_a.value == pytest.approx(A, abs=1e-4)
    assert cell.length_c.value == pytest.approx(C, abs=1e-3)
