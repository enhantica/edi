"""ADR-0111 point 4: uncertainty follows seed sensitivity, not a free flag."""

import math

import edi as api
import pytest

from tests.fixtures.magnetic_pnma import reference
from tests.fixtures.magnetic_pnma import uncertainty_states as inputs


@pytest.mark.parametrize(
    ('kind', 'sigma'),
    [
        ('tied', 0.2),
        ('chain', 0.2),
        ('symmetry-tied', 0.2),
        ('undefined-tied', None),
        ('cross-undefined', None),
        ('constant', 'fixed'),
        ('cell-chain', 2),
        ('cell-chain-undefined', None),
    ],
)
def test_dependent_uncertainty_comes_from_the_relation_graph_after_reload(tmp_path, kind, sigma):
    model = api.Project.load(inputs.project(tmp_path / 'input', kind))
    for index in range(2):
        model.analysis.calculate()
        row = model.structure.atom_site_moment['A']
        axis = 'y'
        follower = row.crystalaxis_y
        if kind == 'symmetry-tied':
            pair = [row.crystalaxis_x, row.crystalaxis_y]
            assert sum(p.free for p in pair) == 1, (
                'ADR-0111 the (t,t,0) subspace has exactly one independent seed'
            )
            axis = 'x' if not pair[0].free else 'y'
            follower = next(p for p in pair if not p.free)
        if kind.startswith('cell-chain'):
            follower = model.structure.cell.angle_beta
        assert not follower.free, 'ADR-0111 the witness is a dependent with a false free flag'
        if sigma == 'fixed':
            assert follower.uncertainty in {None, 0}, (
                'ADR-0111 a constant relation has zero variance, regardless of unrelated seeds'
            )
        elif sigma is None:
            assert follower.uncertainty is None or math.isnan(follower.uncertainty), (
                'ADR-0111 an undefined source stays undefined and a constant has no measured s.u.'
            )
        else:
            assert follower.uncertainty == pytest.approx(sigma, rel=1e-8), (
                'ADR-0111 the dependent maps its seed s.u. through its full relation chain'
            )
        target = tmp_path / ('saved' + str(index))
        model.save_as(target)
        raw = reference.columns((target / 'structures/cosio.edi').read_text())
        token = raw[
            '_cell.angle_beta'
            if kind.startswith('cell-chain')
            else '_atom_site_moment.crystalaxis_' + axis
        ][0]
        assert ('(' in token) == (sigma not in {None, 'fixed'} and kind != 'symmetry-tied'), (
            'ADR-0078 constrained followers save mapped v(su), symmetry followers save bare values'
        )
        model = api.Project.load(target)


def test_unrelated_undefined_seed_preserves_a_known_correlation_pair_on_second_save(tmp_path):
    model = api.Project.load(inputs.project(tmp_path / 'input', 'unrelated-undefined'))
    for index in range(2):
        target = tmp_path / ('saved' + str(index))
        model.save_as(target)
        columns = reference.columns((target / 'analysis/analysis.edi').read_text())
        correlations = columns.get('_fit_parameter_correlation.correlation', [])
        assert any(float(value) == pytest.approx(0.5) for value in correlations), (
            'ADR-0111 an unrelated singular seed cannot drop the determined x-z covariance'
        )
        model = api.Project.load(target)
