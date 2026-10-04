"""gate 1: mechanical ADR coverage; semantic consistency also needs review.

The accepted plan T3 and data-contract points 01-05 name these amendment sites.
This gate cannot certify arbitrary prose's meaning; it prevents missing records,
stale implementation status, and the concrete superseded claims named in T3.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOME = ROOT / 'docs/dev/adrs'
NEW = '0018'
PRIOR = ('0012', '0016')
IMPLEMENTED = ('0016',)


def document(number):
    paths = list(HOME.glob(number + '-*.md'))
    assert len(paths) == 1, ' T3 each storage decision has one unambiguous ADR: ' + number
    return paths[0]


def test_new_storage_record_states_each_data_contract_part():
    path = document(NEW)
    text = path.read_text().lower()
    concepts = {
        '01 one-row category': r'(?:one|single)[ -]row',
        '01 column storage': r'column',
        '02 row access': r'row',
        '03 token identity': r'token',
        '03 removed row values': r'standalone|stand-alone|detached',
        '04 held snapshots': r'snapshot',
        '05 generation': r'generation',
        '05 stamped writes': r'stamp',
    }
    for requirement, pattern in concepts.items():
        assert re.search(pattern, text), (
            ' T3 the storage ADR states the accepted contract part: ' + requirement
        )
    assert path.name in (HOME / 'index.md').read_text(), (
        ' T3 the new storage decision is reachable from the ADR index'
    )
    if NEW == '0018':
        assert path.name in (ROOT / 'mkdocs.yml').read_text(), (
            ' T3 edi exposes its new decision through the documentation navigation'
        )
        for term in ('crysta', 'column', 'anchor'):
            assert term in text, ' I26 edi names its shared engine primitive: ' + term


@pytest.mark.parametrize('number', PRIOR)
def test_each_prior_decision_links_its_storage_amendment(number):
    text = document(number).read_text()
    assert document(NEW).name in text, (
        ' T3 every named prior storage decision links the amendment: ' + number
    )
    if number == '0016':
        assert 'edi needs no stamps of its own' not in text, (
            ' T3 the superseded no-stamp claim cannot remain an operative instruction'
        )


@pytest.mark.parametrize('number', IMPLEMENTED)
def test_implemented_decisions_have_no_stale_status(number):
    text = document(number).read_text()
    status = re.search(r'(?mi)^.*Implementation:.*$', text)
    assert status, ' T3 the ADR declares implementation status'
    assert not any(token in status[0].lower() for token in ('not implemented', '⬜')), (
        ' T3 the already implemented decision must have a current status: ' + number
    )
    rows = [
        line
        for line in (HOME / 'index.md').read_text().splitlines()
        if re.match(r'\| \[' + number + r'\]', line)
    ]
    assert len(rows) == 1, ' T3 each decision has one index row'
    assert not any(token in rows[0].lower() for token in ('not implemented', '⬜')), (
        ' T3 the index must agree with the implemented ADR status: ' + number
    )
