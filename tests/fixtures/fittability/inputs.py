"""Small authored models for fit-policy observations.

The cubic metric fixes b=c=a and all angles at 90 degrees. Integrated intensities
carry no positions. The two point backgrounds and independent P1 coordinates are
input data; no engine output is used to decide an expected blocker.
"""

from pathlib import Path

CELL_FIELDS = ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma')


def structure(name='phase', *, cubic=False):
    group = 'P m -3 m' if cubic else 'P 1'
    values = (4.1, 4.1, 4.1, 90, 90, 90) if cubic else (5.1, 6.2, 7.3, 83, 97, 109)
    text = f'data_{name}\n_edi.schema_version 3\n_space_group.name_h_m "{group}"\n'
    text += ''.join(
        f'_cell.{key} {value}\n' for key, value in zip(CELL_FIELDS, values, strict=True)
    )
    text += (
        'loop_\n_atom_site.id\n_atom_site.type_symbol\n_atom_site.wyckoff_letter\n'
        '_atom_site.fract_x\n_atom_site.fract_y\n_atom_site.fract_z\n'
        '_atom_site.occupancy\n_atom_site.adp_type\n_atom_site.adp_iso\n'
    )
    xyz = '0 0 0' if cubic else '.13 .27 .39'
    return text + f'Ni Ni a {xyz} .73 Biso .41\n'


def experiment(name, *, single, linked='phase', enabled=True, measured=True, xray=False):
    form = 'single crystal' if single else 'powder'
    text = (
        f'data_{name}\n_edi.schema_version 3\n'
        f'_experiment_type.sample_form "{form}"\n'
        '_experiment_type.scattering_type bragg\n'
        f'_experiment_type.radiation_probe {"xray" if xray else "neutron"}\n'
        '_experiment_type.beam_mode "constant wavelength"\n'
        '_instrument.setup_wavelength 1.6\n'
    )
    if xray:
        text += '_scattering_source.xray_dispersion sasaki1989\n'
    text += (
        'loop_\n_linked_structure.structure_id\n_linked_structure.scale\n'
        f'_linked_structure.enabled\n{linked} 2.3 {str(enabled).lower()}\n'
    )
    if single:
        text += (
            '_extinction.type becker-coppens-type-2\n'
            '_extinction.crystal_radius .12\n_extinction.domain_radius 28.4\n'
        )
        if measured:
            text += (
                'loop_\n_refln.index_h\n_refln.index_k\n_refln.index_l\n'
                '_refln.intensity_meas\n_refln.intensity_meas_su\n'
                '1 1 1 2.7 .3\n2 1 3 3.8 .4\n4 1 3 1.9 .2\n'
            )
    else:
        text += (
            '_peak.type cwl-pseudo-voigt-berar-baldinozzi\n_peak.broad_gauss_u .03\n'
            '_peak.broad_gauss_v -.01\n_peak.broad_gauss_w .15\n'
            '_peak.mixing_eta_0 .37\n_peak.mixing_eta_1 .001\n'
            '_peak.asym_beba_a0 0\n_peak.asym_beba_b0 0\n'
            '_peak.asym_beba_a1 0\n_peak.asym_beba_b1 0\n'
            '_peak.asym_beba_limit 150\n_peak.cutoff_fwhm 5\n'
            '_instrument.calib_twotheta_offset 0\n'
            '_background.type line-segment\nloop_\n_background.id\n'
            '_background.position\n_background.intensity\na 20 3\nb 100 9\n'
        )
        if measured:
            text += (
                'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
                '30 10 1\n40 12 1\n50 9 1\n60 8 1\n70 10 1\n80 11 1\n'
            )
    return text


def materialize(root, **options):
    single = options.get('single', True)
    cubic = options.get('cubic', False)
    mixed = options.get('mixed', False)
    other = options.get('other', False)
    enabled = options.get('enabled', True)
    data_free = options.get('data_free', False)
    xray = options.get('xray', False)
    constraint = options.get('constraint', False)
    root = Path(root)
    for folder in ('structures', 'experiments', 'analysis'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name fit-policy\n')
    (root / 'structures/phase.edi').write_text(structure(cubic=cubic))
    if other:
        (root / 'structures/other.edi').write_text(structure('other'))
    (root / 'experiments/bank.edi').write_text(
        experiment('bank', single=single, enabled=enabled, xray=xray)
    )
    if mixed or data_free:
        (root / 'experiments/powder.edi').write_text(
            experiment('powder', single=False, measured=not data_free)
        )
    analysis = '_edi.schema_version 3\n_fitting_mode.type joint\n_minimizer.max_iterations 1\n'
    if constraint:
        analysis += (
            'loop_\n_alias.id\n_alias.parameter_unique_name\n'
            'held phase.atom_site.Ni.adp_iso\n'
            'source phase.atom_site.Ni.occupancy\n'
            'loop_\n_constraint.expression\n"held = source / 2"\n'
        )
    (root / 'analysis/analysis.edi').write_text(analysis)
    return root


def mark_free(root, relative, tag, value):
    path = root / relative
    before = path.read_text()
    lines = before.splitlines()
    matches = [i for i, line in enumerate(lines) if line.startswith(tag + ' ')]
    if len(matches) != 1:
        raise ValueError('The authored input must contain exactly one scalar ' + tag)
    lines[matches[0]] = tag + ' ' + value
    path.write_text('\n'.join(lines) + '\n')
