"""Authored source declarations with different embedded, file and collection measurements."""

import hashlib
from pathlib import Path

import gemmi

FORMS = ('powder-cwl', 'powder-tof', 'reflections-cwl', 'reflections-tof')
ROUTES = (
    'factory-str',
    'factory-path',
    'collection-str',
    'collection-path',
    'collection-edi-path',
    'project',
)
CONFLICTS = ('own+path', 'own+collection', 'path+collection', 'own+path+collection')
# The linked-data contract admits files and collection entries for every experiment.
SINGLES = [(form, declaration) for form in FORMS for declaration in ('own', 'path', 'collection')]


AMBIGUITY = (
    r'(?i)(both|ambiguous|more than one|multiple|conflict|competing|incompatible|'
    r'at most one|keep one|only one)'
)


def admission_pattern(_form):
    # An unsupported-source refusal cannot stand in for conflicting-source admission.
    return AMBIGUITY


def payload(form, directory: Path, sources):
    directory.mkdir(parents=True, exist_ok=True)
    powder = form.startswith('powder')
    tof = form.endswith('tof')
    axis = (3500, 3600, 3700) if tof else (17.5, 18, 18.5)
    own = list(zip(axis, (4, 9, 16), (0.5, 1.25, 2.5), strict=True))
    external = ''.join(
        f'{x} {y} {s}\n' for x, y, s in zip(axis, (25, 36, 49), (0.75, 1.5, 2.75), strict=True)
    )
    collection = ''.join(
        f'{x} {y} {s}\n' for x, y, s in zip(axis, (64, 81, 100), (0.625, 1.75, 3.25), strict=True)
    )
    if not powder:
        external = (
            'Independent linked reflection input\n(3i4,2f12.4,i4,2f8.4)\n'
            + ('0' if tof else '1.73')
            + ' 0 0\n'
            + '2 1 3 25 .75 1 1.3 84\n1 2 3 -36 1.5 1 1.5 88\n'
            '2 1 3 49 2.75 1 1.7 92\n0 0 0 0 0 1 1.9 90\n'
        )
        collection = external.replace('25 .75', '64 .625').replace('-36 1.5', '-81 1.75')
    external_path = directory / ('outside.int' if not powder else 'outside.dat')
    external_path.write_text(external)
    sample = '"powder"' if powder else '"single crystal"'
    beam = '"time-of-flight"' if tof else '"constant wavelength"'
    text = (
        'data_source_boundary\n_edi.schema_version 3\n'
        f'_experiment_type.sample_form {sample}\n'
        f'_experiment_type.beam_mode {beam}\n'
        '_experiment_type.radiation_probe neutron\n_experiment_type.scattering_type bragg\n'
        'loop_\n_linked_structure.structure_id\n_linked_structure.scale\nphase 1\n'
    )
    if not tof:
        text += '_instrument.setup_wavelength 1.73\n'
    if powder:
        if tof:
            text += (
                '_peak.type tof-pseudo-voigt\n_peak.cutoff_fwhm 12\n'
                '_peak.broad_gauss_sigma_0 900\n_peak.broad_gauss_sigma_1 1000\n'
                '_peak.broad_gauss_sigma_2 300\n_peak.broad_lorentz_gamma_0 5\n'
                '_peak.broad_lorentz_gamma_1 0\n_peak.broad_lorentz_gamma_2 0\n'
                '_instrument.setup_twotheta_bank 90\n_instrument.calib_d_to_tof_offset 0\n'
                '_instrument.calib_d_to_tof_linear 10000\n'
                '_instrument.calib_d_to_tof_quadratic 0\n'
                '_instrument.calib_d_to_tof_reciprocal 0\n'
            )
        else:
            text += (
                '_peak.type cwl-gaussian\n_peak.cutoff_fwhm 12\n_peak.broad_gauss_u .05\n'
                '_peak.broad_gauss_v -.01\n_peak.broad_gauss_w .1\n'
                '_instrument.calib_twotheta_offset .123\n'
            )
    if 'own' in sources:
        if powder:
            text += 'loop_\n_data.id\n_data.' + ('time_of_flight' if tof else 'two_theta')
            text += '\n_data.intensity_meas\n_data.intensity_meas_su\n'
            text += ''.join(f'{at} {x} {y} {s}\n' for at, (x, y, s) in enumerate(own, 1))
        else:
            text += (
                'loop_\n_refln.id\n_refln.index_h\n_refln.index_k\n_refln.index_l\n'
                '_refln.intensity_meas\n_refln.intensity_meas_su\n'
            )
            if tof:
                text += '_refln.wavelength\n'
            for prefix, wavelength in [
                ('1 2 1 3 4 .5', '1.3'),
                ('2 1 2 3 -9 1.25', '1.5'),
                ('3 2 1 3 16 2.5', '1.7'),
            ]:
                text += prefix + (' ' + wavelength if tof else '') + '\n'
    if 'path' in sources:
        text += f'_data_source.path "{external_path}"\n'
    if 'collection' in sources:
        text += '_data_source.collection_id independent-third-source\n'
        text += '_data_source.digest ' + hashlib.sha256(collection.encode()).hexdigest() + '\n'
    return text, external_path


# Declared CIF spellings provide setup syntax only; measurement expectations above are authored.
CIF_TAGS = {
    '_data.two_theta': '_pd_meas.2theta_scan',
    '_data.time_of_flight': '_pd_meas.time_of_flight',
    '_data.id': '_pd_meas.id',
    '_data.intensity_meas': '_pd_meas.intensity_total',
    '_data.intensity_meas_su': '_pd_meas.intensity_total_su',
    '_data_source.collection_id': '_edi_data_source.collection_id',
    '_data_source.digest': '_edi_data_source.digest',
    '_data_source.path': '_edi_data_source.path',
    '_experiment_type.beam_mode': '_edi_experiment_type.beam_mode',
    '_experiment_type.radiation_probe': '_diffrn_radiation.probe',
    '_experiment_type.sample_form': '_edi_experiment_type.sample_form',
    '_experiment_type.scattering_type': '_edi_experiment_type.scattering_type',
    '_instrument.calib_d_to_tof_linear': '_edi_instrument.calib_d_to_tof_linear',
    '_instrument.calib_d_to_tof_offset': '_edi_instrument.calib_d_to_tof_offset',
    '_instrument.calib_d_to_tof_quadratic': '_edi_instrument.calib_d_to_tof_quadratic',
    '_instrument.calib_d_to_tof_reciprocal': '_edi_instrument.calib_d_to_tof_reciprocal',
    '_instrument.calib_twotheta_offset': '_pd_calib.2theta_offset',
    '_instrument.setup_twotheta_bank': '_pd_meas.2theta_fixed',
    '_instrument.setup_wavelength': '_diffrn_radiation_wavelength.value',
    '_linked_structure.scale': '_edi_linked_structure.scale',
    '_linked_structure.structure_id': '_pd_phase_block.id',
    '_peak.broad_gauss_sigma_0': '_edi_peak.broad_gauss_sigma_0',
    '_peak.broad_gauss_sigma_1': '_edi_peak.broad_gauss_sigma_1',
    '_peak.broad_gauss_sigma_2': '_edi_peak.broad_gauss_sigma_2',
    '_peak.broad_gauss_u': '_edi_peak.broad_gauss_u',
    '_peak.broad_gauss_v': '_edi_peak.broad_gauss_v',
    '_peak.broad_gauss_w': '_edi_peak.broad_gauss_w',
    '_peak.broad_lorentz_gamma_0': '_edi_peak.broad_lorentz_gamma_0',
    '_peak.broad_lorentz_gamma_1': '_edi_peak.broad_lorentz_gamma_1',
    '_peak.broad_lorentz_gamma_2': '_edi_peak.broad_lorentz_gamma_2',
    '_peak.cutoff_fwhm': '_edi_peak.cutoff_fwhm',
    '_peak.type': '_edi_peak.type',
    '_refln.id': '_refln.id',
    '_refln.index_h': '_refln.index_h',
    '_refln.index_k': '_refln.index_k',
    '_refln.index_l': '_refln.index_l',
    '_refln.intensity_meas': '_refln.intensity_meas',
    '_refln.intensity_meas_su': '_refln.intensity_meas_su',
    '_refln.wavelength': '_refln.wavelength',
}


def as_cif(text):
    text = text.replace('_edi.schema_version 3\n', '')
    for native, alias in sorted(CIF_TAGS.items(), key=lambda pair: -len(pair[0])):
        text = text.replace(native, alias)
    # CIF measured loops have ordinal IDs supplied by their reader.
    block = gemmi.cif.read_string(text).sole_block()
    for tag in ('_pd_meas.id', '_refln.id'):
        column = block.find_loop(tag)
        if column:
            column.erase()
    return block.as_string()


# CIF carries the data itself; location declarations are reported unread, not hydrated.
CIF_IGNORED = ((), ('path',), ('collection',), ('path', 'collection'))


REFLECTION_ROWS = (
    (-2, 1, 3, 12.5, 0.75, 3, 1.31),
    (1, 2, -3, 25.5, 1.25, 8, 1.39),
    (2, -1, 3, -6.25, 1.5, 3, 1.47),
    (3, 1, 2, 36.75, 2.5, 8, 1.55),
    (-2, 1, 3, 0, 2.25, 3, 1.63),
)


def reflection_file(directory, beam, shape):
    """Author FullProf's integrated-intensity layout or a five-column plain file."""
    directory.mkdir(parents=True, exist_ok=True)
    rows = [row for row in REFLECTION_ROWS if shape == 'plural' or row[5] == 3]
    path = directory / ('authored.hkl' if shape == 'plain' else 'authored.InT')
    if shape == 'plain':
        text = ''.join(
            ' '.join(map(str, row[:5] + ((row[6],) if beam == 'tof' else ()))) + '\n'
            for row in rows
        )
    else:
        header = '0' if beam == 'tof' else '1.73'
        text = 'Independent reflection receipt\n(3i4,2f12.4,i4,2f8.4)\n' + header + ' 0 0\n'
        for h, k, ell, intensity, su, code, wavelength in rows:
            text += (
                f'{h:4d}{k:4d}{ell:4d}{intensity:12.4f}{su:12.4f}{code:4d}'
                f'{wavelength:8.4f}{84.0:8.4f}\n'
            )
    path.write_text(text)
    return path, rows


MULTIPLE_DATASETS = (
    r'(?i)(multiple|several|more than one).*dataset|'
    r'dataset.*(multiple|several|more than one)'
)
