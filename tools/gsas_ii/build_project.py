"""Build a new GSAS-II GPX from the Edi exchange model and compare it if requested."""

import argparse
import json
import re
import shutil
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from GSASII import GSASIIscriptable, GSASIIspc

from tools.gsas_ii.bundle import FORMAT, POWDER_FORMAT, profile_metrics, require
from tools.gsas_ii.export_project import export_project


def _write_cif(path: Path, phase: dict) -> None:
    group = phase['space_group']
    require(re.fullmatch(r'[ A-Za-z0-9/:-]+', group), 'Invalid Hermann-Mauguin group')
    lines = ['data_edi_phase', f"_space_group_name_H-M_alt '{group}'"]
    tags = ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma')
    for tag, value in zip(tags, phase['cell'], strict=True):
        lines.append(f'_cell_{tag} {float(value):.17g}')
    lines.extend([
        'loop_',
        '_atom_site_label',
        '_atom_site_type_symbol',
        '_atom_site_fract_x',
        '_atom_site_fract_y',
        '_atom_site_fract_z',
        '_atom_site_occupancy',
        '_atom_site_adp_type',
        '_atom_site_U_iso_or_equiv',
    ])
    tensors = []
    for label, species, x, y, z, occupancy, uiso, *tensor in phase['atoms']:
        require(re.fullmatch(r'[A-Za-z0-9_.-]+', label), f'Invalid CIF atom label {label}')
        require(re.fullmatch(r'[A-Za-z][A-Za-z0-9+-]*', species), f'Invalid species {species}')
        kind = 'Uani' if tensor else 'Uiso'
        ion = _gsas_ion(species)
        lines.append(
            f"'{label}' {ion} {x:.17g} {y:.17g} {z:.17g} {occupancy:.17g} {kind} {uiso:.17g}"
        )
        if tensor:
            require(len(tensor) == 6, f'Invalid anisotropic site {label}')
            tensors.append(f"'{label}' " + ' '.join(f'{value:.17g}' for value in tensor))
    if tensors:
        lines.extend(['loop_', '_atom_site_aniso_label'])
        lines.extend(f'_atom_site_aniso_U_{key}' for key in ('11', '22', '33', '12', '13', '23'))
        lines.extend(tensors)
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')


def _add_powder(project, measured: Path, histogram: dict):
    mode = histogram['type']
    require(mode in {'PNC', 'PXC', 'PNT'}, f'Unsupported powder mode {mode}')
    settings = dict(histogram['instrument'])
    neutral = {'Type': mode, 'Bank': 1, 'Z': 0.0, 'Azimuth': 0.0, 'Polariz.': 0.0}
    if mode == 'PNT':
        neutral.update({'fltPath': 1.0, 'difB': 0.0, 'sig-q': 0.0, 'beta-q': 0.0})
    if mode == 'PXC':
        settings['Polariz.'] = settings.pop('polarization')
        settings['Azimuth'] = settings.pop('azimuth')
        if 'Lam2' in settings:
            settings['Lam1'] = settings.pop('Lam')
            settings['I(L2)/I(L1)'] = settings.pop('ratio')
    instrument = {key: [value, value, 0] for key, value in neutral.items()}
    for key, (value, refine) in settings.items():
        require(type(refine) is bool, f'Expected a refine flag for {key}')
        instrument[key] = [value, value, int(refine)]
    return project.add_powder_histogram(str(measured), [instrument, {}], fmthint='Topas xye')


def _apply_phase_link(phase, histogram, sample: dict) -> None:
    phase.setSampleProfile(histogram, 'size', 'isotropic', sample['size_um'], LGmix=1.0)
    phase.setSampleProfile(
        histogram, 'microstrain', 'isotropic', sample['microstrain_ppm'], LGmix=1.0
    )
    phase_scale, phase_refine = sample['phase_scale']
    phase.HAPvalue('Scale', newValue=phase_scale, targethistlist=[histogram])
    phase.data['Histograms'][histogram.name]['Scale'][1] = phase_refine


def _apply_histogram_settings(histogram, spec: dict) -> None:
    sample = spec['sample']
    histogram.SampleParameters['Scale'] = sample['scale']
    if 'radius_mm' in sample:
        histogram.SampleParameters['Gonio. radius'] = sample['radius_mm']
        histogram.SampleParameters['DisplaceX'] = sample['displace_x']
        histogram.SampleParameters['DisplaceY'] = sample['displace_y']
    background = spec['background']
    coefficients = background['coefficients']
    fit_limits = spec.get('fit_limits')
    if fit_limits:
        histogram.data['Limits'][1:] = fit_limits
    histogram.set_refinements({
        'Background': {
            'type': 'chebyschev-1',
            'no. coeffs': len(coefficients),
            'coeffs': coefficients,
            'refine': background['refine'],
        }
    })


def _new_pattern(project, histogram: dict, xye: Path) -> tuple:
    observed = np.asarray(histogram['observations'], dtype=float)
    require(
        observed.ndim == 2
        and observed.shape[1] in {3, 4}
        and len(observed) >= 2
        and np.isfinite(observed).all()
        and np.all(observed[:, 2] >= 0),
        'Expected a complete observation table with nonnegative weights',
    )
    masked = observed[:, 3].astype(bool) if observed.shape[1] == 4 else None
    observed = observed[:, :3]
    measured = observed.copy()
    measured[:, 2] = 1 / np.sqrt(np.where(measured[:, 2] > 0, measured[:, 2], 1))
    measured[:, 1] = np.maximum(1.0, measured[:, 1])
    np.savetxt(xye, measured, fmt='%.17g', encoding='ascii')
    pattern = _add_powder(project, xye, histogram)
    # GSAS-II treats imported TOF X values as bin edges. Edi stores the
    # processed observation coordinates, so restore the complete stored grid.
    pattern.data['data'][1] = [column.copy() for column in observed.T] + [
        np.zeros(len(observed)) for _ in range(3)
    ]
    if masked is not None:
        pattern.data['data'][1] = [
            np.ma.array(x, mask=masked.copy()) for x in pattern.data['data'][1]
        ]
    domain = (float(observed[0, 0]), float(observed[-1, 0]))
    pattern.data['Limits'] = [domain, list(domain)]
    _apply_histogram_settings(pattern, histogram)
    return pattern, observed


def _new_phase(project, phase: dict, cif: Path):
    _write_cif(cif, phase)
    structure = project.add_phase(str(cif), phasename=phase['name'], fmthint='CIF')
    flags = dict(
        zip((row[0] for row in phase['atoms']), phase.get('atom_flags', []), strict=False)
    )
    structure.set_refinements({'Cell': phase.get('cell_refine', False), 'Atoms': flags})
    return structure


def _operation_key(rotation, shift) -> tuple:
    return tuple(np.asarray(rotation, dtype=int).ravel()), tuple(
        np.rint(24 * shift).astype(int) % 24
    )


def _gsas_magnetic_group(group: dict, model: dict) -> None:
    desired = {}
    for text in model['operations']:
        rotation, shift, spin = GSASIIspc.MagText2MTS(text)
        desired[_operation_key(rotation, np.asarray(shift))] = spin
    ordered = [
        _operation_key(sign * rotation, center + sign * shift)
        for center in group['SGCen']
        for sign in (1, -1)[: 1 + group['SGInv']]
        for rotation, shift in group['SGOps']
    ]
    require(set(ordered) == set(desired), 'GSAS-II magnetic family setting differs')
    signs = [desired[op] for op in ordered]
    count = len(group['SGSpin'])
    require(count <= 6, 'Unsupported magnetic generator count')
    for spins in product((1, -1), repeat=count - 1):
        group['SGSpin'] = [1, *spins]
        GSASIIspc.SetMagnetic(group)
        if np.array_equal(signs, group['SpnFlp']):
            return
    raise ValueError('GSAS-II could not reproduce the signed nuclear operators')


def _gsas_ion(symbol: str) -> str:
    return re.sub(r'(\d+)([+-])$', r'\2\1', symbol)


def _new_magnetic_phase(project, phase: dict, cif: Path):
    model = phase['magnetic']
    subset = {row[0]: row for row in model['moments']}
    atoms = []
    for atom in phase['atoms']:
        if atom[0] not in subset:
            continue
        moment = subset[atom[0]]
        atoms.append([atom[0], _gsas_ion(moment[1]), *atom[2:]])
    info = {
        **phase,
        'name': phase['name'] + '-magnetic',
        'atoms': atoms,
        'atom_flags': [''] * len(atoms),
        'cell_refine': False,
    }
    structure = _new_phase(project, info, cif)
    general = structure.data['General']
    _gsas_magnetic_group(general['SGData'], model)
    general['Type'], general['AtomPtrs'] = 'magnetic', [3, 1, 10, 12]
    for atom in structure.data['Atoms']:
        moment = subset[atom[0]]
        atom[7:7] = moment[2:5]
        atom[2] = 'M' if any(moment[5]) else ''
    GSASIIscriptable.SetupGeneral(structure.data, str(cif.parent))
    return structure


def _pair_magnetic_constraints(project, nucleus, magnetic, histogram, model: dict) -> None:
    hist_id = histogram.id
    nuclear_id, magnetic_id = nucleus.id, magnetic.id
    project.index_ids()
    for field in ('Scale', 'Size;i', 'Mustrain;i'):
        project.add_EquivConstr(
            [f'{nuclear_id}:{hist_id}:{field}', f'{magnetic_id}:{hist_id}:{field}'],
            reloadIdx=False,
        )
    for axis in range(3):
        project.add_EquivConstr(
            [f'{nuclear_id}::A{axis}', f'{magnetic_id}::A{axis}'], reloadIdx=False
        )
    nuclear_atoms = {atom.label: index for index, atom in enumerate(nucleus.atoms())}
    for index, moment in enumerate(model['moments']):
        nucleus_index = nuclear_atoms[moment[0]]
        for term in ('AUiso', 'Afrac'):
            project.add_EquivConstr(
                [f'{nuclear_id}::{term}:{nucleus_index}', f'{magnetic_id}::{term}:{index}'],
                reloadIdx=False,
            )
        for axis, free in zip('xyz', moment[5], strict=True):
            if any(moment[5]) and not free:
                project.add_HoldConstr([f'{magnetic_id}::AM{axis}:{index}'], reloadIdx=False)


def _create_gpx(bundle: dict, scratch: Path) -> Path:
    if bundle['format'] == FORMAT:
        phases = [bundle['phase']]
        hist = bundle['histogram']
        histograms = [{**hist, 'links': [{'phase_index': 0, **hist['sample']}]}]
    else:
        require(bundle['format'] == POWDER_FORMAT, f'Expected {FORMAT} or {POWDER_FORMAT}')
        phases, histograms = bundle['phases'], bundle['histograms']
    gpx = scratch / 'reconstructed.gpx'
    project = GSASIIscriptable.G2Project(newgpx=str(gpx))
    structures = [
        _new_phase(project, phase, scratch / f'phase-{i}.cif') for i, phase in enumerate(phases, 1)
    ]
    magnetic = {
        i: _new_magnetic_phase(project, phase, scratch / f'magnetic-{i}.cif')
        for i, phase in enumerate(phases)
        if 'magnetic' in phase
    }
    observations = []
    for i, histogram in enumerate(histograms, 1):
        pattern, observed = _new_pattern(project, histogram, scratch / f'measured-{i}.xye')
        observations.append(observed)
        for settings in histogram['links']:
            structure = structures[settings['phase_index']]
            project.link_histogram_phase(pattern, structure)
            _apply_phase_link(structure, pattern, settings)
            index = settings['phase_index']
            if index in magnetic:
                project.link_histogram_phase(pattern, magnetic[index])
                _apply_phase_link(magnetic[index], pattern, settings)
                _pair_magnetic_constraints(
                    project, structure, magnetic[index], pattern, phases[index]['magnetic']
                )
    for tied in bundle.get('adp_ties', []):
        targets = []
        for phase_id, label in tied:
            atoms = structures[phase_id].atoms()
            index = next(i for i, site in enumerate(atoms) if site.label == label)
            targets.append(f'{phase_id}::AUiso:{index}')
        project.add_EquivConstr(targets)
    project.save()

    reopened = GSASIIscriptable.G2Project(str(gpx))
    for pattern, observed in zip(reopened.histograms(), observations, strict=True):
        result = np.column_stack([pattern.getdata(field) for field in ('X', 'Yobs', 'Yweight')])
        require(
            result.shape == observed.shape and np.array_equal(result, observed),
            'Reopened GSAS-II project changed observations or weights',
        )
    return gpx


def _compare(base: Path, rebuilt: Path) -> dict:
    original = json.loads(base.read_text(encoding='ascii'))
    result = json.loads(rebuilt.read_text(encoding='ascii'))
    prior = np.asarray(original['histogram']['observations'])
    after = np.asarray(result['histogram']['observations'])
    require(
        prior.shape == after.shape
        and np.allclose(prior[:, :2], after[:, :2], rtol=0, atol=1e-8)
        and np.allclose(prior[:, 2], after[:, 2], rtol=2e-6, atol=0),
        'The reference and reconstructed project have different observations',
    )
    source_profile = original['reference']
    rebuilt_profile = result['reference']
    return profile_metrics(
        np.column_stack((source_profile['calculated'], source_profile['background'])),
        np.column_stack((rebuilt_profile['calculated'], rebuilt_profile['background'])),
        1 / np.sqrt(prior[:, 2]),
    )


def build_project(
    source: Path,
    output: Path,
    *,
    compare_to: Path | None = None,
    metrics: Path | None = None,
) -> None:
    """Create and reopen a fresh GSAS-II project using its own writer."""
    require(output.suffix.lower() == '.gpx', 'Expected .gpx output')
    require(not output.exists() and not output.is_symlink(), f'Output already exists: {output}')
    require((compare_to is None) == (metrics is None), 'Specify both comparison paths')
    bundle = json.loads(source.read_text(encoding='ascii'))
    with TemporaryDirectory(prefix='gsas-ii-reconstruction-') as scratch:
        gpx = _create_gpx(bundle, Path(scratch))
        with gpx.open('rb') as src, output.open('xb') as destination:
            shutil.copyfileobj(src, destination)
        if compare_to is not None:
            rebuilt = Path(scratch) / 'reconstructed.gsas.json'
            export_project(output, rebuilt, reference=True)
            comparison = json.dumps(_compare(compare_to, rebuilt), indent=2, allow_nan=False)
            with metrics.open('x', encoding='ascii') as stream:
                stream.write(comparison + '\n')


def main() -> None:
    """Build a fresh GPX from a versioned GSAS-II exchange bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Edi-exported .gsas.json bundle')
    parser.add_argument('output', type=Path, help='New GSAS-II project (.gpx)')
    parser.add_argument('--compare-to', type=Path, help='Original GSAS-II reference bundle')
    parser.add_argument('--metrics', type=Path, help='New JSON file for profile residuals')
    args = parser.parse_args()
    try:
        build_project(args.source, args.output, compare_to=args.compare_to, metrics=args.metrics)
    except (KeyError, OSError, TypeError, ValueError, GSASIIscriptable.G2ScriptException) as error:
        parser.exit(1, f'GSAS-II reconstruction: {error}\n')


if __name__ == '__main__':
    main()
