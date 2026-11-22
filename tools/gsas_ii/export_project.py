"""Export the supported GSAS-II powder model from a trusted local GPX."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from GSASII import GSASIIscriptable, GSASIIspc

from tools.gsas_ii.bundle import FORMAT, INSTRUMENT, require


def _phase_model(phase) -> dict:
    general = phase.data['General']
    group = general['SGData']
    _, pnma = GSASIIspc.SpcGroup('P n m a')
    require(
        all(group.get(key) == pnma.get(key) for key in ('SpGrp', 'SGInv', 'SGFixed', 'SGGray'))
        and np.array_equal(group['SGCen'], pnma['SGCen'])
        and len(group['SGOps']) == len(pnma['SGOps'])
        and all(
            np.array_equal(rot, expected_rot) and np.array_equal(shift, expected_shift)
            for (rot, shift), (expected_rot, expected_shift) in zip(
                group['SGOps'], pnma['SGOps'], strict=True
            )
        ),
        'Only the standard P n m a setting is supported',
    )
    require(
        general['Type'] == 'nuclear'
        and not any(general.get(key) for key in ('Modulated', 'doPawley', 'HydIds'))
        and not general['SH Texture']['Order']
        and not phase.data.get('RBModels'),
        'Unsupported phase type, modulation, Pawley intensities, texture or rigid bodies',
    )
    require(not general['Cell'][0], 'Refining the cell changes the scale convention')
    require(
        all(isotope == 'Nat. Abund.' for isotope in general['Isotope'].values()),
        'Only natural isotope abundances are supported',
    )
    atoms = []
    for atom in phase.atoms():
        require(not atom.refinement_flags.strip(), f'Atom {atom.label} must be fixed')
        require(atom.type in {'Pb', 'S', 'O'}, f'Unsupported atom type {atom.type!r}')
        require(atom.adp_flag == 'I', f'Atom {atom.label} must have isotropic displacement')
        atoms.append([
            atom.label,
            atom.type,
            *map(float, atom.coordinates),
            float(atom.occupancy),
            float(atom.uiso),
        ])
    return {
        'name': phase.name,
        'space_group': 'P n m a',
        'cell': list(map(float, general['Cell'][1:7])),
        'atoms': atoms,
    }


def _fixed(parameters: dict, neutral: dict) -> None:
    for name, expected in neutral.items():
        require(parameters[name] == [expected, False], f'Unsupported active {name}')


def _sample_model(phase, histogram) -> dict:
    sample = histogram.data['Sample Parameters']
    link = phase.data['Histograms'][histogram.name]
    require(sample['Type'] == 'Debye-Scherrer', 'Only Debye-Scherrer geometry is supported')
    _fixed(sample, {'Absorption': 0, 'DisplaceX': 0, 'DisplaceY': 0})
    _fixed(link, {'Extinction': 0})
    _fixed(link['Babinet'], {'BabA': 0, 'BabU': 0})
    require(
        link['Use'] and not link['LeBail'] and len(phase.data['Histograms']) == 1,
        'Expected one active Rietveld phase-to-histogram link',
    )
    preference = link['Pref.Ori.']
    require(preference[:3] == ['MD', 1, False], 'Preferred orientation must be neutral')
    strain = link['HStrain']
    require(not any(strain[0]) and not any(strain[1]), 'Hydrostatic strain must be inactive')
    for key in ('Size', 'Mustrain'):
        form, values, free, *_ = link[key]
        require(
            form == 'isotropic' and values[2] == 1 and not any(free),
            f'{key} must be fixed, isotropic and entirely Lorentzian',
        )
    return {
        'size_um': float(link['Size'][1][0]),
        'microstrain_ppm': float(link['Mustrain'][1][0]),
        'scale': [float(sample['Scale'][0]), bool(sample['Scale'][1])],
        'phase_scale': [float(link['Scale'][0]), bool(link['Scale'][1])],
    }


def _instrument_model(histogram) -> dict:
    instrument, secondary = histogram.data['Instrument Parameters']
    require(instrument['Type'][1] == 'PNC' and not secondary, 'Expected one PNC instrument')
    require(
        set(instrument) <= {*INSTRUMENT, 'Type', 'Z', 'Polariz.', 'Azimuth', 'Source', 'Bank'},
        'Unsupported instrument parameter',
    )
    require(instrument['Z'][1:] == [0, 0], 'Instrument Z must be fixed at zero')
    for name in ('Lam', 'SH/L'):
        require(not instrument[name][2], f'Instrument {name} must be fixed')
    return {name: [float(instrument[name][1]), bool(instrument[name][2])] for name in INSTRUMENT}


def _observations(histogram) -> np.ndarray:
    columns = [np.ma.asarray(histogram.getdata(key)) for key in ('X', 'Yobs', 'Yweight')]
    require(
        not any(np.ma.getmaskarray(column).any() for column in columns),
        'Masked observations are outside this conversion',
    )
    observations = np.column_stack(columns)
    limits = histogram.data['Limits']
    require(
        len(limits) == 2 and np.array_equal(limits[1], observations[[0, -1], 0]),
        'Only the full measured range without exclusions is supported',
    )
    metadata = histogram.data['data'][0]
    require(
        metadata['wtFactor'] == 1 and not metadata.get('Dummy'),
        'Expected measured data with unit histogram weight multiplier',
    )
    return observations


def _background(histogram) -> dict:
    terms, extras = histogram.data['Background'][:2]
    require(
        terms[0] == 'chebyschev-1'
        and terms[2] == len(terms) - 3
        and not any(extras.get(key) for key in ('nDebye', 'nPeaks', 'debyeTerms', 'peaksList'))
        and not extras.get('background PWDR', [''])[0]
        and extras.get('fixback') is None,
        'Only a Chebyshev background without additional contributions is supported',
    )
    return {'refine': bool(terms[1]), 'coefficients': list(map(float, terms[3:]))}


def _reference(project, observed: np.ndarray) -> dict:
    project.set_Controls('cycles', 0)
    project.data['Controls']['data']['deriv type'] = 'analytic Hessian'
    project.do_refinements([{}])
    histogram = project.histogram(0)
    require(
        np.array_equal(_observations(histogram), observed),
        'GSAS-II changed the measured grid or observations during calculation',
    )
    return {
        'calculated': np.asarray(histogram.getdata('Ycalc')).tolist(),
        'background': np.asarray(histogram.getdata('Background')).tolist(),
    }


def export_project(source: Path, output: Path, *, reference: bool = False) -> None:
    """Write the ASCII bundle, optionally calculating a reference in a private GPX copy."""
    with TemporaryDirectory(prefix='gsas-ii-export-') as scratch:
        local_source = Path(scratch) / 'source.gpx'
        shutil.copyfile(source, local_source)
        with local_source.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        project = GSASIIscriptable.G2Project(
            str(local_source), newgpx=str(Path(scratch) / 'reference.gpx')
        )
        require(
            len(project.phases()) == 1
            and len(project.histograms()) == 1
            and not any(
                label[0].startswith(('HKLF ', 'IMG ', 'PKS ', 'SASD ', 'REFD ', 'PDF '))
                for label in project.names
            ),
            'Expected exactly one phase and one powder histogram',
        )
        constraints = project.data['Constraints']['data']
        require(
            not any(value for name, value in constraints.items() if not name.startswith('_'))
            and not any(project.data['Restraints']['data'].values())
            and not project.data['Controls']['data'].get('Seq Data'),
            'Constraints, restraints and sequential fits are outside this conversion',
        )
        phase, histogram = project.phase(0), project.histogram(0)
        measured = _observations(histogram)
        bundle = {
            'format': FORMAT,
            'source': {
                'filename': source.name,
                'sha256': digest,
                'last_saved_using': project.data['Controls']['data'].get('LastSavedUsing'),
            },
            'phase': _phase_model(phase),
            'histogram': {
                'name': histogram.name,
                'type': 'PNC',
                'instrument': _instrument_model(histogram),
                'sample': _sample_model(phase, histogram),
                'background': _background(histogram),
                'observations': measured.tolist(),
            },
        }
        if reference:
            bundle['reference'] = _reference(project, measured)
        payload = json.dumps(bundle, ensure_ascii=True, allow_nan=False, separators=(',', ':'))
    with output.open('x', encoding='ascii') as stream:
        stream.write(payload + '\n')


def main() -> None:
    """Run the trusted-file GSAS-II exporter."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Trusted local .gpx file')
    parser.add_argument('output', type=Path, help='New ASCII JSON bundle')
    parser.add_argument('--reference', action='store_true', help='Calculate the GSAS-II profile')
    args = parser.parse_args()
    try:
        export_project(args.source, args.output, reference=args.reference)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(1, f'GSAS-II export: {error}\n')


if __name__ == '__main__':
    main()
