"Every series estimator has independent cubic, cap and persisted-setting witnesses."

import edi as engine
import numpy as np
import pytest

from tests.fixtures.background_estimate.series import project, terms
from tests.fixtures.background_estimate.settings import DEFAULTS, read_settings, write_settings


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
@pytest.mark.parametrize('cap', [2, 6])
def test_known_cubic_recovers_its_order_or_stops_at_the_saved_cap(tmp_path, kind, cap):
    source = project(tmp_path / 'input', kind)
    loaded = engine.Project.load(source)
    loaded.experiment.background.auto_estimate(
        method='arpls', width=6, smoothness=1000, tolerance=2, use_model=False, max_terms=cap
    )
    destination = tmp_path / 'saved'
    loaded.save_as(destination)
    actual = terms(destination)
    assert len(actual) == (2 if cap == 2 else 4), (
        'A known cubic plus seeded bounded noise must recover four terms '
        'or exactly the saved two-term cap'
    )
    assert [row[0] for row in actual] == list(range(len(actual))), (
        'Estimated series terms must retain contiguous zero-based powers in the declared basis'
    )
    if cap == 6:
        assert np.allclose([row[1] for row in actual], [50, 12, -5, 7], atol=0.3, rtol=0), (
            'Nontrivial polynomial origin and Chebyshev domain must recover '
            'the authored coefficients within 0.3, above independent Stage-1 '
            'bias'
        )
    reloaded = engine.Project.load(destination)
    reloaded.save_as(tmp_path / 'again')
    assert terms(tmp_path / 'again') == actual, (
        'Saved estimated terms must reload exactly in the same basis'
    )


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
@pytest.mark.parametrize('cap', [None, 1, 4, 12, 30])
def test_max_terms_saves_and_reloads_without_filling_a_blank(tmp_path, kind, cap):
    source = project(tmp_path / 'input', kind)
    write_settings(source, {**DEFAULTS, 'mode': 'manual', 'use_model': False, 'max_terms': cap})
    before = terms(source)
    loaded = engine.Project.load(source)
    assert loaded.experiment.background_estimate.max_terms == cap, (
        'The public estimate category must expose the authored max_terms '
        'or None for the derived cap'
    )
    destination = tmp_path / 'saved'
    loaded.save_as(destination)
    assert read_settings(destination)['max_terms'] == cap, (
        'Saving max_terms must preserve every admitted cap and leave a derived blank blank'
    )
    assert terms(destination) == before, (
        'Saving a manual cap must not change any saved coefficient'
    )
    again = engine.Project.load(destination)
    assert again.experiment.background_estimate.max_terms == cap, (
        'Reloading a saved series must retain its exact max_terms choice'
    )


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
@pytest.mark.parametrize('bad', [0, -1, 31, float('nan'), float('inf'), 1e300])
def test_invalid_term_cap_is_refused_without_partial_series_mutation(tmp_path, kind, bad):
    source = project(tmp_path / 'input', kind)
    loaded = engine.Project.load(source)
    loaded.save_as(tmp_path / 'before')
    with pytest.raises((ValueError, TypeError, OverflowError)):
        loaded.experiment.background.auto_estimate(method='arpls', use_model=False, max_terms=bad)
    loaded.save_as(tmp_path / 'after')
    assert terms(tmp_path / 'after') == terms(tmp_path / 'before'), (
        'An invalid term cap must be refused before replacing any coefficients'
    )
