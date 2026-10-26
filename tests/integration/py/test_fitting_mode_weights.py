"""Joint weights are persisted only in the mode that uses them."""

import os
import runpy
import shlex
from pathlib import Path

import edi as engine
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('mode', ['single', 'joint', 'sequential', 'independent'])
def test_joint_weights_load_in_every_mode_and_save_only_in_joint(tmp_path, mode):
    inputs = runpy.run_path(str(ROOT / 'tests/integration/py/test_c13_t12_loop_identity.py'))
    structure, experiment, analysis, _ = inputs['_texts']('joint_fit')
    source = tmp_path / 'input'
    for folder in ['structures', 'experiments', 'analysis']:
        (source / folder).mkdir(parents=True)
    (source / 'structures/structure.edi').write_text(structure)
    (source / 'experiments/experiment.edi').write_text(experiment)
    if mode not in {'sequential', 'independent'}:
        (source / 'experiments/second.edi').write_text(
            experiment.replace('data_experiment', 'data_second')
        )
    analysis = analysis.replace('experiment 1', 'experiment 0.625').replace(
        'second 2', 'second 2.125'
    )
    analysis += '\n_fitting_mode.type ' + mode + '\n'
    if mode in {'sequential', 'independent'}:
        analysis = analysis.replace('second 2.125\n', '')
        analysis += (
            '_sequential_fit.data_dir experiments/scan\n_sequential_fit.file_pattern *.xy\n'
        )
        (source / 'experiments/scan').mkdir()
        (source / 'experiments/scan/file.xy').write_text('45 2 1\n46 3 1\n')
    (source / 'analysis/analysis.edi').write_text('_edi.schema_version 3\n' + analysis)
    project = engine.Project.load(source)
    supplied = [0.625] if mode in {'sequential', 'independent'} else [0.625, 2.125]
    assert [bank.dataset_weight for bank in project.experiments] == supplied, (
        'Legacy weights must still load under every fitting mode at their declared values'
    )
    output = tmp_path / 'saved'
    project.save_as(output)
    text = (output / 'analysis/analysis.edi').read_text()
    assert ('_joint_fit.experiment_id' in text) == (mode == 'joint'), (
        'The joint weight category must be written only while the fitting mode is joint'
    )
    tokens = shlex.split(text)
    assert tokens[tokens.index('_fitting_mode.type') + 1] == mode, (
        'Descriptive GUI mode labels must never replace the persisted mode tokens'
    )
    reopened = engine.Project.load(output)
    expected = supplied if mode == 'joint' else [1.0] * len(supplied)
    assert [bank.dataset_weight for bank in reopened.experiments] == expected, (
        'Reopen must retain active joint weights and use default weights for omitted categories'
    )


def test_gui_fitting_modes_use_the_owner_descriptions():
    files = [
        ROOT / 'app/src/analysis_view_model.cpp',
        ROOT / 'core/src/selectors.cpp',
        ROOT / 'app/qml/Pages/Analysis/FittingModeGroup.qml',
    ]
    document = yaml.safe_load(
        (
            Path(os.environ.get('CRYSTA_CONSUMER_SRC', ROOT / 'build/crysta-src'))
            / 'data/dictionary/parameters.yaml'
        ).read_text()
    )
    row = next(
        row
        for row in document['parameters'] + document.get('items', [])
        if row['uid'] == 'fitting_mode.type'
    )
    source = '\n'.join(path.read_text() for path in files)
    assert 'setItemOptions("fitting_mode.type", modes, modes.front())' in source, (
        'The actual selector model resolves applicable fitting-mode names through the dictionary'
    )
    assert 'uid: "fitting_mode.type"' in source and 'row.analysis.fittingModeOptions' in source, (
        'The real selector consumes the fitting-mode dictionary and its guarded options'
    )
    for label in [
        'Single experiment',
        'Joint: all experiments at once',
        'Sequential: each from the previous',
        'Independent: each from the same start',
    ]:
        assert label in {option['display_name'] for option in row['options']}, (
            'The fitting-mode selector must declare each owner-approved display name'
        )
