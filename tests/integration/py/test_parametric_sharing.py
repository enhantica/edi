"""Public sharing operations follow handwritten group and file expectations."""

import edi as engine
import pytest

from tests.fixtures.joint_series import cases as prior
from tests.fixtures.parametric_series import cases


def shared_group_names(analysis, parameter):
    possible_names = {f'{bank}.{parameter}' for bank in cases.BANKS}
    return [line.strip() for line in analysis.splitlines() if line.strip() in possible_names]


@pytest.mark.parametrize('path', cases.PATHS)
@pytest.mark.parametrize('free', [False, True])
def test_shared_and_free_are_orthogonal_in_joint(tmp_path, path, free):
    project = engine.Project.load(cases.model(tmp_path / 'source'))
    members = [cases.parameter(project, bank, path) for bank in cases.BANKS]
    for index, member in enumerate(members):
        member.free = free
        member.value = 0.3 + index
    members[1].shared = True
    assert [member.free for member in members] == [free] * 3, (
        'Sharing preserves the existing group Free flag'
    )
    assert [member.shared for member in members] == [True] * 3, (
        'Sharing through a follower covers every eligible experiment'
    )
    assert [member.value for member in members] == [1.3] * 3, (
        'The selected member supplies the common value'
    )
    members[2].free = not free
    assert [member.free for member in members] == [not free] * 3, (
        'Free edited through either member changes the whole group'
    )
    members[0].value = 2.75
    assert [member.value for member in members] == [2.75] * 3, (
        'Editing a shared value updates every member'
    )
    members[2].shared = False
    assert [member.shared for member in members] == [False] * 3, (
        'Unsharing removes the whole group'
    )
    assert [member.free for member in members] == [not free] * 3, (
        'Unsharing retains the group Free flag'
    )
    assert [member.value for member in members] == [2.75] * 3, (
        'Unsharing leaves independent copies of the common value'
    )


@pytest.mark.parametrize('path', cases.PATHS)
@pytest.mark.parametrize('free', [False, True])
def test_shared_group_round_trip_and_inactive_mode(tmp_path, path, free):
    root = cases.model(tmp_path / 'source')
    project = engine.Project.load(root)
    for bank in cases.BANKS:
        cases.parameter(project, bank, path).free = free
    cases.parameter(project, 'third', path).shared = True
    project.save_as(tmp_path / 'saved')
    analysis = tmp_path / 'saved/analysis/analysis.edi'
    text = analysis.read_text()
    assert shared_group_names(text, path) == ['third.' + path], (
        'The selected third member is the sole persisted group name'
    )
    assert '_alias.' not in text, 'Generated groups never add user aliases'
    assert '_constraint.' not in text, 'Generated groups never add user constraints'
    reopened = engine.Project.load(tmp_path / 'saved')
    assert [cases.parameter(reopened, bank, path).shared for bank in cases.BANKS] == [True] * 3, (
        'All members retain sharing after reload'
    )
    assert [cases.parameter(reopened, bank, path).free for bank in cases.BANKS] == [free] * 3, (
        'Both fixed and free shared linear terms survive reload'
    )
    analysis.write_text(text.replace('_fitting_mode.type joint', '_fitting_mode.type independent'))
    inactive = engine.Project.load(tmp_path / 'saved')
    members = [cases.parameter(inactive, bank, path) for bank in cases.BANKS]
    members[1].free = not free
    assert members[0].free == free, (
        'Inactive sharing cannot change another Independent experiment Free flag'
    )
    inactive.save_as(tmp_path / 'inactive')
    active_text = (tmp_path / 'inactive/analysis/analysis.edi').read_text()
    assert shared_group_names(active_text, path) == ['third.' + path], (
        'Independent save preserves the selected member name of the inactive shared group'
    )


@pytest.mark.parametrize('free_index', [0, 1], ids=['fixed-clicked', 'free-clicked'])
def test_new_mixed_shared_group_keeps_any_free_and_the_clicked_value(tmp_path, free_index):
    project = engine.Project.load(cases.model(tmp_path / 'source'))
    path = 'peak.broad_gauss_w'
    members = [cases.parameter(project, bank, path) for bank in cases.BANKS]
    for index, member in enumerate(members):
        member.free = index == free_index
        member.value = 0.3 + index

    members[1].shared = True
    assert all(member.shared and member.free for member in members), (
        'A new group with any previously free copy starts free and shared throughout'
    )
    assert [member.value for member in members] == [1.3] * 3, (
        'The clicked copy supplies the common value even if another copy determined Free'
    )
    members[2].free = False
    assert all(member.shared and not member.free for member in members), (
        'Later Free edits change the single group flag while retaining Shared'
    )


def test_loaded_group_preserves_selected_member(tmp_path):
    root = cases.model(tmp_path / 'source')
    first = root / 'experiments/0_zeta.edi'
    first.write_text(
        first.read_text().replace('_peak.broad_gauss_w 0.15', '_peak.broad_gauss_w 0.45()')
    )
    third = root / 'experiments/2_third.edi'
    third.write_text(
        third.read_text().replace('_peak.broad_gauss_w 0.15', '_peak.broad_gauss_w 0.85')
    )
    cases.append_shared(root, ['third.peak.broad_gauss_w'])
    project = engine.Project.load(root)
    project.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/analysis/analysis.edi').read_text()
    assert shared_group_names(text, 'peak.broad_gauss_w') == ['third.peak.broad_gauss_w'], (
        'Saving a loaded group preserves exactly the persisted member name'
    )
    assert [project.experiments[bank].peak.broad_gauss_w.free for bank in cases.BANKS] == [
        True
    ] * 3, 'A mixed loaded group is free if any saved copy was free'
    assert [project.experiments[bank].peak.broad_gauss_w.value for bank in cases.BANKS] == [
        0.85
    ] * 3, 'A mixed loaded group takes the persisted member value'


def test_user_dependent_blocks_sharing_without_changing_constraints(tmp_path):
    root = cases.model(tmp_path / 'source')
    prior.relations(
        root,
        [('dependent', 'zeta.peak.broad_gauss_w'), ('source', 'alpha.peak.broad_gauss_w')],
        ['dependent = source * 2'],
    )
    analysis_file = root / 'analysis/analysis.edi'
    analysis_file.write_text(
        analysis_file.read_text().replace(
            '_constraint.expression\n', '_constraint.id\n_constraint.expression\nwidth_tie '
        )
    )
    project = engine.Project.load(root)
    project.save_as(tmp_path / 'before')
    analysis = 'analysis/analysis.edi'
    baseline = (tmp_path / 'before' / analysis).read_bytes()
    for bank in cases.BANKS:
        with pytest.raises((ValueError, RuntimeError), match=r'constraint.*width_tie'):
            project.experiments[bank].peak.broad_gauss_w.shared = True
        assert all(
            not project.experiments[member].peak.broad_gauss_w.shared for member in cases.BANKS
        ), 'A dependent member prevents sharing the entire group from any member'

    project.save_as(tmp_path / 'after')
    assert (tmp_path / 'after' / analysis).read_bytes() == baseline, (
        'A refused Shared edit leaves the aliases, user expression and sharing state intact'
    )


@pytest.mark.parametrize('fixed', [False, True])
def test_parametric_fixed_and_free_shared_background_reload(tmp_path, fixed):
    project = engine.Project.load(cases.scan(tmp_path / 'source', fixed=fixed))
    parameter = cases.parameter(project, 'zeta', 'background.1.intensity')
    assert parameter.shared, 'A listed background coefficient is eligible for sharing'
    assert parameter.free == (not fixed), (
        'Loading Shared preserves bare versus parenthesized CIF values'
    )
    project.save_as(tmp_path / 'saved')
    reopened = engine.Project.load(tmp_path / 'saved')
    parameter = cases.parameter(reopened, 'zeta', 'background.1.intensity')
    assert (parameter.shared, parameter.free) == (True, not fixed), (
        'All shared background state survives a save and reload'
    )


def test_sparse_start_duplicate_is_rejected(tmp_path):
    root = cases.scan(tmp_path / 'source', shared=False)
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text()
        + '\nloop_\n'
        + '\n'.join(cases.START_TAGS)
        + '\np1.xy zeta.background.2.intensity 8\np1.xy zeta.background.2.intensity 9\n'
    )
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)duplicate'):
        engine.Project.load(root)


def test_sparse_start_identity_survives_directory_copy(tmp_path):
    root = cases.scan(tmp_path / 'source', shared=False)
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text()
        + '\nloop_\n'
        + '\n'.join(cases.START_TAGS)
        + '\np1.xy zeta.background.2.intensity 8.125\n'
    )
    engine.Project.load(root).save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/analysis/analysis.edi').read_text()
    assert all(tag in text for tag in cases.START_TAGS), (
        'The sparse-start loop survives serialization'
    )
    assert 'p1.xy' in text, 'A start retains its data-relative point identity'
    assert '8.125' in text, 'A start retains its independently authored value'
    assert 'scan/p1.xy' not in text, (
        'The persisted start key stays relative to the scan data directory'
    )


def test_parametric_mode_requires_a_scan(tmp_path):
    root = cases.model(tmp_path / 'source', mode='parametric')
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)(scan|sequential|data_dir)'):
        engine.Project.load(root)


def test_shared_start_survives_and_unknown_point_start_is_dropped(tmp_path):
    root = cases.scan(tmp_path / 'source')
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text()
        + '\nloop_\n'
        + '\n'.join(cases.START_TAGS)
        + '\np1.xy zeta.background.1.intensity 8.125\np9.xy zeta.background.2.intensity 19.375\n'
        + 'p1.xy zeta.background.2.intensity 8.25\n'
    )
    engine.Project.load(root).save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/analysis/analysis.edi').read_text()
    assert '8.25' in text, 'A valid unshared point start survives reload'
    assert '8.125' in text, 'A shared start survives as the series start'
    assert '19.375' not in text, 'An unlisted point cannot acquire a persisted start'
