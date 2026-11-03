"""Independent inputs and axial-vector sums for the Pnma cobalt model."""

import json
from pathlib import Path

import gemmi
import numpy as np

ROOT = Path(__file__).parent
J0 = (0.4332, 14.3553, 0.5857, 4.6077, -0.0382, 0.1338, 0.0179)
J2 = (1.9049, 11.644, 1.3159, 4.357, 0.3146, 1.645, 0.0017)
ROTATIONS = np.array([
    (1, 1, 1),
    (1, -1, -1),
    (-1, 1, -1),
    (-1, -1, 1),
    (-1, -1, -1),
    (-1, 1, 1),
    (1, -1, 1),
    (1, 1, -1),
])
TRANSLATIONS = np.array([
    (0, 0, 0),
    (0.5, 0.5, 0.5),
    (0, 0.5, 0),
    (0.5, 0, 0.5),
    (0, 0, 0),
    (0.5, 0.5, 0.5),
    (0, 0.5, 0),
    (0.5, 0, 0.5),
])


def form_factor(s, c2=0):
    """Brown's three Gaussian terms, with the j2 leading s squared."""

    def gaussian(row):
        a, alpha, b, beta, c, gamma, d = row
        return (
            a * np.exp(-alpha * s * s) + b * np.exp(-beta * s * s) + c * np.exp(-gamma * s * s) + d
        )

    return gaussian(J0) + c2 * s * s * gaussian(J2)


def columns(text):
    """Decode the native STAR records without invoking either product."""
    if not text.lstrip().startswith('data_'):
        text = 'data_project\n' + text
    result = {}
    for block in gemmi.cif.read_string(text):
        for item in block:
            if item.pair:
                result[item.pair[0].lower()] = [gemmi.cif.as_string(item.pair[1])]
            elif item.loop:
                width = len(item.loop.tags)
                for i, tag in enumerate(item.loop.tags):
                    result[tag.lower()] = [
                        gemmi.cif.as_string(v) for v in item.loop.values[i::width]
                    ]
    return result


def project(root, structure=None, experiment=None, *, show=True):
    """Write a native project through the same input boundary as a saved project."""
    (root / 'structures').mkdir(parents=True)
    (root / 'experiments').mkdir()
    (root / 'project.edi').write_text(
        '_edi.schema_version 3\n_metadata.name magnetic\n'
        f'_structure_view.show_moments {str(show).lower()}\n'
    )
    (root / 'structures/cosio.edi').write_text(structure or (ROOT / 'magnetic.edi').read_text())
    (root / 'experiments/d20.edi').write_text(experiment or (ROOT / 'experiment.edi').read_text())
    return root


def expansion(source=None):
    """Apply the eight published diagonal operations, deduplicating each site."""
    if source is None:
        source = columns((ROOT / 'magnetic.edi').read_text())
    xyz = np.array([source['_atom_site.fract_' + a] for a in 'xyz'], dtype=float).T
    moments = np.array(
        [source['_atom_site_moment.crystalaxis_' + axis] for axis in 'xyz'], dtype=float
    ).T
    result = {}
    for label, moment in zip(source['_atom_site_moment.label'], moments, strict=True):
        position = xyz[source['_atom_site.id'].index(label)]
        for rotation, translation in zip(ROTATIONS, TRANSLATIONS, strict=True):
            point = np.round((rotation * position + translation) % 1, 9)
            result[label, *point] = np.prod(rotation) * rotation * moment
    return result


def magnetic_squared(hkl, c2=0, *, source=None):
    """Physical sum in fm squared from the independent cell and expanded moments."""
    if source is None:
        source = columns((ROOT / 'magnetic.edi').read_text())
    cell = np.array([float(source['_cell.length_' + a][0]) for a in 'abc'])
    reciprocal = np.asarray(hkl) / cell
    s = np.linalg.norm(reciprocal) / 2
    direction = reciprocal / np.linalg.norm(reciprocal)
    amplitude = np.zeros(3, dtype=complex)
    for (_, x, y, z), moment in expansion(source).items():
        amplitude += moment * np.exp(2j * np.pi * np.dot(hkl, (x, y, z)))
    amplitude *= 2.695 * form_factor(s, c2) * np.exp(-0.269 * s * s)
    perpendicular = amplitude - np.dot(direction, amplitude) * direction
    return float(np.vdot(perpendicular, perpendicular).real)


def magnetic_peak_windows():
    """TCH full widths from the fixed PCR, for (100) and (001)."""
    values = json.loads((ROOT / 'cosio/values.json').read_text())
    for d in [values['cell'][0], values['cell'][2]]:
        theta = np.arcsin(1.87 / (2 * d))
        position = np.degrees(2 * theta) + values['zero']
        u, v, w, lorentz_x, lorentz_y = values['uvwxy']
        gaussian = np.sqrt(u * np.tan(theta) ** 2 + v * np.tan(theta) + w)
        lorentz = lorentz_x / np.cos(theta) + lorentz_y * np.tan(theta)
        width = (
            gaussian**5
            + 2.69269 * gaussian**4 * lorentz
            + 2.42843 * gaussian**3 * lorentz**2
            + 4.47163 * gaussian**2 * lorentz**3
            + 0.07842 * gaussian * lorentz**4
            + lorentz**5
        ) ** 0.2
        yield position, width
