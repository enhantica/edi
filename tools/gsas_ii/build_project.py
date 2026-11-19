"""Build a new GSAS-II GPX from the Edi exchange model and compare it if requested."""

import argparse
import json
import re
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from GSASII import GSASIIscriptable

from tools.gsas_ii.bundle import FORMAT, INSTRUMENT, profile_metrics, require
from tools.gsas_ii.export_project import export_project


def _write_cif(path: Path, phase: dict) -> None:
    require(phase['space_group'] == 'P n m a', 'Expected the standard P n m a phase')
    lines = ['data_edi_phase', "_space_group_name_H-M_alt 'P n m a'"]
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
    for label, species, x, y, z, occupancy, uiso in phase['atoms']:
        require(re.fullmatch(r'[A-Za-z0-9_.-]+', label), f'Invalid CIF atom label {label}')
        require(species in {'Pb', 'S', 'O'}, f'Unsupported atom type {species}')
        lines.append(
            f"'{label}' {species} {x:.17g} {y:.17g} {z:.17g} {occupancy:.17g} Uiso {uiso:.17g}"
        )
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')


def _add_powder(project, measured: Path, histogram: dict):
    require(histogram['type'] == 'PNC', 'Expected one PNC histogram')
    settings = histogram['instrument']
    require(set(settings) == set(INSTRUMENT), 'Unexpected PNC instrument field')
    neutral = {'Type': 'PNC', 'Bank': 1, 'Z': 0.0, 'Azimuth': 0.0, 'Polariz.': 0.0}
    instrument = {key: [value, value, 0] for key, value in neutral.items()}
    for key, (value, refine) in settings.items():
        require(type(refine) is bool, f'Expected a refine flag for {key}')
        instrument[key] = [value, value, int(refine)]
    return project.add_powder_histogram(str(measured), [instrument, {}], fmthint='Topas xye')


def _apply_settings(phase, histogram, spec: dict) -> None:
    sample = spec['sample']
    phase.setSampleProfile(histogram, 'size', 'isotropic', sample['size_um'], LGmix=1.0)
    phase.setSampleProfile(
        histogram, 'microstrain', 'isotropic', sample['microstrain_ppm'], LGmix=1.0
    )
    phase_scale, phase_refine = sample['phase_scale']
    phase.HAPvalue('Scale', newValue=phase_scale, targethistlist=[histogram])
    phase.data['Histograms'][histogram.name]['Scale'][1] = phase_refine
    histogram.SampleParameters['Scale'] = sample['scale']
    background = spec['background']
    coefficients = background['coefficients']
    histogram.set_refinements({
        'Background': {
            'type': 'chebyschev-1',
            'no. coeffs': len(coefficients),
            'coeffs': coefficients,
            'refine': background['refine'],
        }
    })


def _create_gpx(bundle: dict, scratch: Path) -> Path:
    require(bundle['format'] == FORMAT, f'Expected bundle format {FORMAT}')
    phase, histogram = bundle['phase'], bundle['histogram']
    cif, xye, gpx = scratch / 'phase.cif', scratch / 'measured.xye', scratch / 'reconstructed.gpx'
    _write_cif(cif, phase)
    observed = np.asarray(histogram['observations'], dtype=float)
    require(
        observed.ndim == 2
        and observed.shape[1] == 3
        and len(observed) >= 2
        and np.isfinite(observed).all()
        and np.all(observed[:, 2] > 0),
        'Expected a complete observation table with positive weights',
    )
    measured = observed.copy()
    measured[:, 2] = 1 / np.sqrt(measured[:, 2])
    np.savetxt(xye, measured, fmt='%.17g', encoding='ascii')
    project = GSASIIscriptable.G2Project(newgpx=str(gpx))
    pattern = _add_powder(project, xye, histogram)
    structure = project.add_phase(
        str(cif), histograms=[pattern], phasename=phase['name'], fmthint='CIF'
    )
    _apply_settings(structure, pattern, histogram)
    project.save()

    reopened = GSASIIscriptable.G2Project(str(gpx)).histogram(0)
    result = np.column_stack([reopened.getdata(field) for field in ('X', 'Yobs', 'Yweight')])
    require(
        result.shape == observed.shape
        and np.array_equal(result[:, :2], observed[:, :2])
        and np.allclose(result[:, 2], observed[:, 2], rtol=1e-13, atol=0),
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
