"""Public sharing operations follow handwritten group and file expectations."""

import edi as engine
import pytest

from tests.fixtures.joint_series import cases as prior
from tests.fixtures.parametric_series import cases


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
    assert 'zeta.' + path in text, 'The first eligible project member owns the persisted group'
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
    assert 'zeta.' + path in active_text, (
        'Independent save preserves the inactive shared declaration'
    )


def test_loaded_follower_normalizes_and_leader_free_wins(tmp_path):
    root = cases.model(tmp_path / 'source')
    first = root / 'experiments/0_zeta.edi'
    first.write_text(
        first.read_text().replace('_peak.broad_gauss_w 0.15', '_peak.broad_gauss_w 0.15()')
    )
    cases.append_shared(root, ['third.peak.broad_gauss_w'])
    project = engine.Project.load(root)
    assert [project.experiments[bank].peak.broad_gauss_w.free for bank in cases.BANKS] == [
        True
    ] * 3, 'A mixed loaded group takes its eligible leader Free flag'
    project.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/analysis/analysis.edi').read_text()
    assert 'zeta.peak.broad_gauss_w' in text, 'A follower declaration writes the eligible leader'
    assert 'third.peak.broad_gauss_w' not in text, 'A normalized group omits duplicate followers'


def test_user_dependent_is_excluded_before_leader_selection(tmp_path):
    root = cases.model(tmp_path / 'source')
    prior.relations(
        root,
        [('dependent', 'zeta.peak.broad_gauss_w'), ('source', 'alpha.peak.broad_gauss_w')],
        ['dependent = source * 2'],
    )
    project = engine.Project.load(root)
    project.experiments['third'].peak.broad_gauss_w.shared = True
    assert not project.experiments['zeta'].peak.broad_gauss_w.shared, (
        'A user-dependent member keeps its own relation'
    )
    assert project.experiments['alpha'].peak.broad_gauss_w.shared, (
        'The first eligible independent member becomes the leader'
    )
    project.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/analysis/analysis.edi').read_text()
    assert 'alpha.peak.broad_gauss_w' in text.split(cases.SHARED_TAG)[1], (
        'The serialized leader excludes earlier user-dependent paths'
    )
    with pytest.raises((ValueError, RuntimeError)):
        project.experiments['zeta'].peak.broad_gauss_w.shared = True


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


def test_unknown_and_shared_point_starts_are_dropped(tmp_path):
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
    assert '8.125' not in text, 'A point start cannot override a shared template value'
    assert '19.375' not in text, 'An unlisted point cannot acquire a persisted start'
