"""One physical bank, with an active magnetic phase and three named alternates."""

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PHASES = ('obsidian', 'saffron', 'indigo', 'azure')
ALIASES = {
    'obsidian': 'zz_obsidian',
    'saffron': 'aa_saffron',
    'indigo': 'ab_indigo',
    'azure': 'ac_azure',
}


def materialize(root, *, active='obsidian', additions=False, broken=False, sequential=False):
    for category in ('analysis', 'experiments', 'structures'):
        (root / category).mkdir(parents=True, exist_ok=True)
    magnetic = (ROOT / 'tests/fixtures/magnetic_pnma/cosio-2k-reference.edi').read_text()
    crystal = (
        ROOT / 'tests/fixtures/magnetic_type_iv/gui/popup/structures/parent.edi'
    ).read_text()
    for index, phase in enumerate(PHASES):
        text = crystal if phase == 'azure' else magnetic
        text = re.sub(r'^data_\S+', 'data_' + phase, text, count=1)
        if phase != 'azure':
            text = re.sub(
                r'^_cell\.length_a .+$',
                f'_cell.length_a {10.30806 + index}',
                text,
                flags=re.MULTILINE,
            )
        (root / 'structures' / (phase + '.edi')).write_text(text)
    experiment = (
        ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_2k/project/experiments/d20.edi'
    ).read_text()
    link_source = '_linked_structure.scale\ncosio 1.817226()'
    assert experiment.count(link_source) == 1, 'The measured source has one exact link to replace'
    links = '\n'.join(f'{phase} 1.817226() {str(phase == active).lower()}' for phase in PHASES)
    experiment = experiment.replace(
        link_source, '_linked_structure.scale\n_linked_structure.enabled\n' + links
    )
    texture = '\n'.join(f'{phase} .92 .13 1 0 0' for phase in PHASES)
    (root / 'experiments/d20.edi').write_text(
        experiment + '\nloop_\n_preferred_orientation.structure_id\n'
        '_preferred_orientation.march_r\n_preferred_orientation.march_random_fract\n'
        '_preferred_orientation.index_h\n_preferred_orientation.index_k\n'
        '_preferred_orientation.index_l\n' + texture + '\n'
    )
    relation = {
        'aa_saffron': 'd20.preferred_orientation.saffron.march_r',
        'ab_indigo': 'd20.indigo.march_r',
        'ac_azure': 'd20.preferred_orientation.azure.march_r',
        'zy_width': 'd20.peak.broad_lorentz_x',
        'zz_drop': 'd20.peak.broad_gauss_v',
        'zz_obsidian': 'd20.preferred_orientation.obsidian.march_r',
        'zz_reference': 'd20.instrument.calib_twotheta_offset',
        'zz_unused': 'd20.peak.broad_gauss_w',
    }
    if additions:
        relation = {'ac_azure': relation['ac_azure']}
    if broken:
        relation['zz_missing'] = 'missing.preferred_orientation.azure.march_r'
    aliases = '\n'.join(f'{name} {path}' for name, path in relation.items())
    scan = ''
    if sequential:
        points = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/project/experiments/d20_scan'
        (root / 'scan').mkdir()
        for name in ('all594687.dat', 'all594791.dat'):
            shutil.copyfile(points / name, root / 'scan' / name)
        scan = (
            '_sequential_fit.data_dir scan\n_sequential_fit.file_pattern *.dat\n'
            '_sequential_fit.template_file all594687.dat\n'
            'loop_\n_sequential_fit_extract.id\n_sequential_fit_extract.target\n'
            '_sequential_fit_extract.pattern\n_sequential_fit_extract.required\n'
            'temperature diffrn.ambient_temperature ^TEMP\\s+([0-9.]+) true\n'
        )
    mode = 'sequential' if sequential else 'single'
    relations = (
        '\nloop_\n_constraint.id\n_constraint.expression\n'
        'aa_saffron_rule "aa_saffron = .92"\n'
        'bb_hidden_input "zz_obsidian = ab_indigo + .025"\n'
        'zy_drop_rule "zy_width = .1"\n'
        'zz_visible_rule "zz_reference = .29433"\n'
    )
    history = (
        '_fit_result.result_kind deterministic\n_fit_result.success true\n'
        '_fit_result.message done\n_fit_result.iterations 1\n'
        '_fit_result.covariance_available true\n'
        'loop_\n_fit_parameter_correlation.id\n_fit_parameter_correlation.source_kind\n'
        '_fit_parameter_correlation.parameter_unique_name_i\n'
        '_fit_parameter_correlation.parameter_unique_name_j\n'
        '_fit_parameter_correlation.correlation\n'
        '1 deterministic d20.linked_structure.obsidian.scale d20.peak.broad_gauss_u .91\n'
        '2 deterministic d20.linked_structure.saffron.scale d20.peak.broad_gauss_u .93\n'
        '3 deterministic d20.linked_structure.indigo.scale d20.peak.broad_gauss_u .88\n'
        '4 deterministic d20.linked_structure.azure.scale d20.peak.broad_gauss_u .84\n'
    )
    (root / 'analysis/analysis.edi').write_text(
        f'_edi.schema_version 3\n_fitting_mode.type {mode}\n_minimizer.max_iterations 2\n'
        + scan
        + 'loop_\n_alias.id\n_alias.parameter_unique_name\n'
        + aliases
        + '\n'
        + ('' if additions else relations)
        + ('' if additions or sequential else history)
    )
    (root / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name projection\n')
    return root
