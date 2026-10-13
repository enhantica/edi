"""Preserve shared record bytes while checking the declared edi pair-count extension."""

import re


def without_pair_count(text):
    matches = re.findall(r'^x-edi\.correlations=(\d+)$', text, re.MULTILINE)
    if not matches:
        assert 'x-edi.correlations' not in text, (
            'The declared pair count must be an unsigned integer'
        )
        return text
    assert len(matches) == 1, 'The edi machine record declares its pair count exactly once'
    free = re.findall(r'^n_free=(\d+)$', text, re.MULTILINE)
    assert len(free) == 1, 'The pair-count bound requires the independently declared free-set size'
    size = int(free[0])
    assert int(matches[0]) <= size * (size - 1) // 2, (
        'The reported correlations cannot exceed the distinct off-diagonal free-parameter pairs'
    )
    return re.sub(r'^x-edi\.correlations=\d+\n', '', text, flags=re.MULTILINE)
