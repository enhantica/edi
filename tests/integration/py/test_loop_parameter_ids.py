"""Every parameter-bearing loop uses its declared row id (owner seq 17/18).

Names come from the frozen diffraction-lib capture for these exact projects.
The field projection keeps numeric parameters owned by the native model, not
the reference's text and integer descriptors. No engine-produced name is an oracle.
"""

import hashlib
import json
import shutil
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/loop_parameter_ids'
REFERENCE = json.loads((FIXTURE / 'reference.json').read_text())
FIELDS = {
    'background': {'intensity', 'coef'},
    'linked_structure': {'scale'},
    'preferred_orientation': {'march_r', 'march_random_fract'},
    'atom_site': {'fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso'},
    'atom_site_aniso': {'adp_11', 'adp_22', 'adp_33', 'adp_12', 'adp_13', 'adp_23'},
}


def relevant(name):
    parts = name.split('.')
    return len(parts) == 4 and parts[1] in FIELDS and parts[3] in FIELDS[parts[1]]


def expected(kind):
    return sorted(name for name in REFERENCE['projects'][kind]['names'] if relevant(name))


def names(project):
    # The native descriptor intentionally has no public unique_name property.
    # Alias creation observes the production name resolver for the held parameter.
    aliases = project.analysis.aliases
    result = []
    bank = project.experiments['bank']
    descriptors = [row.intensity for row in bank.background]
    descriptors += [row.coef for row in bank.background_terms]
    descriptors += [row.scale for row in bank.linked_structures]
    descriptors += [
        getattr(row, field)
        for row in bank.preferred_orientation
        for field in sorted(FIELDS['preferred_orientation'])
    ]
    descriptors += [
        getattr(row, field)
        for row in project.structures['phase'].atom_sites
        for field in sorted(FIELDS['atom_site'])
    ]
    for index, parameter in enumerate(descriptors):
        key = 'identity_probe_' + str(index)
        aliases.create(id=key, param=parameter)
        result.append(aliases[key].parameter_unique_name)
        aliases.remove(key)
    return result


@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
def test_loop_parameter_names_match_independent_declared_ids(kind, tmp_path):
    record = REFERENCE['projects'][kind]
    assert {
        p.relative_to(FIXTURE / kind).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (FIXTURE / kind).rglob('*.edi')
    } == record['sha256'], (
        'The external names must belong to the exact committed physical input files'
    )
    project = engine.Project.load(FIXTURE / kind)
    # Prefix census includes old positional and single-structure shortcut names;
    # filtering by four-part relevant() here would silently omit those escapes.
    actual = sorted(
        name
        for name in names(project)
        if any(
            name.startswith(prefix)
            for prefix in (
                'bank.background',
                'bank.linked_structure',
                'bank.preferred_orientation',
                'phase.atom_site',
                'bank.scale',
                'bank.march_r',
                'bank.march_random_fract',
            )
        )
    )
    assert actual == expected(kind), (
        'All numeric loop parameters must match diffraction-lib row ids, '
        'including a single linked structure'
    )
    destination = tmp_path / 'saved'
    project.save_as(destination)
    reopened = engine.Project.load(destination)
    assert sorted(name for name in names(reopened) if relevant(name)) == expected(kind), (
        'Save and reload must preserve every declared loop parameter identity'
    )


@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
def test_positional_alias_with_constraint_is_refused_on_load(kind, tmp_path):
    private = tmp_path / 'input'
    shutil.copytree(FIXTURE / kind, private)
    older = 'bank.background[0]' if kind == 'line-segment' else 'bank.background.1.coef'
    analysis = private / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text()
        + '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
        + f'left {older}\nright bank.linked_structure.phase.scale\n'
        + '\nloop_\n_constraint.id\n_constraint.expression\n'
        + 'bind "right = 2*left"\n'
    )
    before = analysis.read_bytes()
    with pytest.raises((ValueError, RuntimeError)) as caught:
        engine.Project.load(private)
    assert older in str(caught.value), (
        'A positional alias must be refused with its name even when a constraint uses it'
    )
    assert 'older version' in str(caught.value).lower(), (
        'An old alias must produce the short version refusal instead of migration'
    )
    assert len(str(caught.value)) <= 240, 'The older-alias load diagnostic must stay short'
    assert analysis.read_bytes() == before, (
        'Refusing an old alias must preserve the original constraint and every input byte'
    )
