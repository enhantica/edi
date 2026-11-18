"""The hand-counted two-bank NCAF free set excludes each equality follower."""

import shutil

import edi as engine
import pytest

from tests.fixtures.joint_series import cases, ncaf


@pytest.mark.parametrize('ties', [0, 1, 2])
def test_two_bank_powder_ties_remove_one_joint_column_each(tmp_path, ties):
    root = tmp_path / 'project'
    shutil.copytree(ncaf.CASE / 'project', root)
    kept = ('wish_5_6', 'wish_4_7')
    for file in (root / 'experiments').glob('*.edi'):
        if file.stem not in kept:
            file.unlink()
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(
        '_edi.schema_version 3\n_fitting_mode.type joint\n_minimizer.max_iterations 1\n'
        'loop_\n_joint_fit.experiment_id\n_joint_fit.weight\nwish_5_6 1\nwish_4_7 1\n'
    )
    parameters = ('peak.broad_gauss_sigma_2', 'instrument.calib_d_to_tof_offset')[:ties]
    aliases, expressions = [], []
    for index, name in enumerate(parameters):
        aliases.extend([
            (f'leader{index}', f'wish_5_6.{name}'),
            (f'follower{index}', f'wish_4_7.{name}'),
        ])
        expressions.append(f'follower{index} = leader{index}')
    if ties:
        cases.relations(root, aliases, expressions)
    project = engine.Project.load(root)
    for parameter in list(project.free_parameters):
        parameter.free = False
    project.structure.cell.length_a.free = True
    for bank in kept:
        experiment = project.experiments[bank]
        experiment.linked_structures['ncaf'].scale.free = True
        experiment.peak.broad_gauss_sigma_2.free = bank == kept[0] or ties < 1
        experiment.instrument.calib_d_to_tof_offset.free = bank == kept[0] or ties < 2
    assert len(project.free_parameters) == 7 - ties, (
        'One cell and two banks with scale, width and zero make seven minus equality followers'
    )
    project.analysis.fit()
    for name in parameters:
        category, item = name.split('.')
        leader = getattr(getattr(project.experiments[kept[0]], category), item)
        follower = getattr(getattr(project.experiments[kept[1]], category), item)
        assert follower.value == leader.value, (
            'A bank equality must evaluate inside the powder fit'
        )
        assert follower.uncertainty == leader.uncertainty, (
            'An equality follower must use its leader joint covariance row'
        )
