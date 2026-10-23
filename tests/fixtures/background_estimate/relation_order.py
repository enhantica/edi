"""Disposable relation-order inputs; equality invariants, never a physics oracle."""

import re
import shutil

import numpy as np

from tests.fixtures.background_estimate.settings import write_settings


def relation_input(destination, source, relation, *, normalized=False, mode='single'):
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('README.md'))
    for path in destination.rglob('*.edi'):
        path.write_text(re.sub(r'(?<=\d)\([^()]*\)', '', path.read_text()))
    metadata = destination / 'project.edi'
    metadata.write_text(
        re.sub(r'(?m)^_metadata.purpose .*$', '_metadata.purpose "fitting"', metadata.read_text())
    )
    experiment = destination / 'experiments/hrpt.edi'
    text = experiment.read_text()
    scale = 2.5 if normalized and relation == 'scale' else 10.0
    text = re.sub(r'(_linked_structure.scale\n\S+)\s+\S+', r'\g<1> ' + str(scale), text)
    text = re.sub(
        r'(?m)^_instrument.calib_twotheta_offset (\S+)$',
        r'_instrument.calib_twotheta_offset \1()',
        text,
    )
    experiment.write_text(text)
    if normalized and relation == 'cell':
        path = destination / 'structures/lbco.edi'
        path.write_text(
            re.sub(
                r'(?m)^_cell.length_[abc] .*$',
                lambda match: match[0].split()[0] + ' 3.9375',
                path.read_text(),
            )
        )
    declared_mode = mode if mode not in {'independent', 'sequential'} else 'single'
    target = 'hrpt.linked_structure.lbco.scale' if relation == 'scale' else 'lbco.cell.length_a'
    value = '2.5' if relation == 'scale' else '3.9375'
    (destination / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_fitting_mode.type '
        + declared_mode
        + '\n_minimizer.max_iterations 1\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
        'target ' + target + '\nloop_\n_constraint.expression\n"target = ' + value + '"\n'
    )
    write_settings(
        destination,
        {
            'mode': 'auto',
            'method': 'snip',
            'width': 7.25,
            'smoothness': None,
            'n_points': 9,
            'use_model': True,
        },
        experiment='hrpt',
    )
    return destination


def scan_files(project, destination, mode):
    data = project.experiment.data
    x = np.asarray(data.two_theta)
    y = np.asarray(data.intensity_meas)
    sigma = np.asarray(data.intensity_meas_su)
    directory = destination / 'experiments/scan'
    directory.mkdir()
    for index in range(2):
        np.savetxt(
            directory / (str(index) + '.xy'), np.column_stack([x, y + index * 11.25, sigma])
        )
    path = destination / 'analysis/analysis.edi'
    path.write_text(
        re.sub(r'(?m)^_fitting_mode.type .*$', '_fitting_mode.type ' + mode, path.read_text())
        + '\n_sequential_fit.data_dir experiments/scan\n_sequential_fit.file_pattern *.xy\n'
    )
