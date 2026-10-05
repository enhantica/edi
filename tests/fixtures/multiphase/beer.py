"""Static independent BEER expectations and project copies; no reference engine imports."""

import hashlib
import shutil
from pathlib import Path

import numpy as np

HOME = Path(__file__).with_name('beer')
PROJECT_ID = 'pd-neut-tof_ferrite-austenite-beer_joint'


def tree_digests(home):
    return {
        str(p.relative_to(home)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(home.rglob('*'))
        if p.is_file()
    }


def write_initial(home):
    shutil.copytree(HOME / 'projects/initial', home)
    return home


def actual_values(project, parameters):
    values = {}
    for key in parameters:
        block, category, *parts = key.split('.')
        if category == 'atom_site':
            atom = next(a for a in project.structures[block].atom_sites if a.id == parts[0])
            item = getattr(atom, parts[1])
        else:
            experiment = project.experiments[block]
            if category == 'linked_structure':
                rows = getattr(experiment, 'linked_structures', None)
                if rows is None:
                    rows = experiment.linked_structure
                item = getattr(rows[parts[0]], parts[1])
            elif category == 'background':
                # Native background ids are serialized one-based row ordinals.
                row = experiment.background[int(parts[0]) - 1]
                item = getattr(row, parts[1])
            else:
                field = parts[0]
                if category == 'instrument' and field == 'd_to_tof_offset':
                    field = 'calib_d_to_tof_offset'
                item = getattr(getattr(experiment, category), field)
        values[key] = item.value
    return values


def active_rwp(project):
    project.analysis.calculate()
    numerator = denominator = 0.0
    for experiment in project.experiments:
        x = np.asarray(experiment.data.time_of_flight)
        use = (x > 40500) & (x < 130000)
        y = np.asarray(experiment.data.intensity_meas)[use]
        error = np.asarray(experiment.data.intensity_meas_su)[use]
        calculated = np.asarray(experiment.data.intensity_calc)[use]
        numerator += np.sum(((y - calculated) / error) ** 2)
        denominator += np.sum((y / error) ** 2)
    return float(np.sqrt(numerator / denominator))
