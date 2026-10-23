"""Licence component lists exclude development tools and design references."""

import json
import re

import pytest

from tests.integration.py.test_table_and_about_contract import ROOT, dependency_matrix


def production_components():
    source = ROOT / 'tests/fixtures/distribution_licences/production_components.json'
    groups = json.loads(source.read_text())['groups']
    return {name.casefold() for group in groups for name in group['components']}


def require_production_components(names):
    extra = {name.strip('` ').casefold() for name in names} - production_components()
    assert not extra, (
        'Licence lists name only reviewed production code or data inclusions; '
        'development tools, design and porting references are excluded: ' + repr(sorted(extra))
    )


@pytest.mark.parametrize('listing', ['overview', 'notices', 'python'])
def test_source_component_lists_exclude_development_only_entries(listing):
    if listing == 'overview':
        names = dependency_matrix()
    elif listing == 'notices':
        names = re.findall(r'^## (.+)$', (ROOT / 'THIRD-PARTY-NOTICES').read_text(), re.MULTILINE)
    else:
        names = [
            path.name.removesuffix('-LICENSE') for path in (ROOT / 'licenses').glob('*-LICENSE')
        ]
        # The shipped licence filename uses the overview's documented slug form.
        allowed = production_components()
        slug_to_name = {re.sub(r'[^a-z0-9.+-]+', '-', name).strip('-'): name for name in allowed}
        names = [slug_to_name.get(name.casefold(), name) for name in names]
    require_production_components(names)


@pytest.mark.parametrize(
    'entry', ['easydiffractionbeta', 'diffraction-lib', 'pytest', 'Clang', 'New design helper']
)
def test_development_entry_refusal_cannot_be_evaded_by_a_surface_mark(entry):
    require_production_components(('Qt', 'plotly.js'))
    # Even a falsely asserted "compiled in" mark must not legitimise an entry.
    names = {name: {'desktop': 'compiled in'} for name in ('Qt', 'plotly.js', entry)}
    with pytest.raises(AssertionError, match='reviewed production'):
        require_production_components(names)
