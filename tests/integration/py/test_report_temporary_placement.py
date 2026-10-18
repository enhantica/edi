"""The filesystem witness must expose an unprotected write at every documented temporary."""

import pytest

from tests.fixtures.report_storage.temporary_aliases import plant

CASES = [
    ('html', 'reports/result.html', 'reports/result.html.tmp', '.result.html.tmp'),
    ('settings', 'reports/report.edi', 'reports/report.edi.tmp', '.report.edi.tmp'),
    ('experiment', 'experiments/bank.edi', 'experiments/bank.edi.tmp', '.bank.edi.tmp'),
]


def snapshot(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob('*')
        if path.is_file()
    }


def exercise(root, case, alias, parent, target):
    _kind, relative, owned_name, linked_name = case
    path = root / 'project'
    selected = path / relative
    selected.parent.mkdir(parents=True)
    selected.write_bytes(b'previous published bytes, independent\n')
    external, planted = plant(path, selected, alias, parent, target)
    expected = path / (linked_name if parent == 'linked' else owned_name)
    outside_before, published_before = snapshot(external), selected.read_bytes()
    expected.write_bytes(b'unprotected temporary overwrite\n')
    damaged = snapshot(external) != outside_before or selected.read_bytes() != published_before
    return planted, expected, damaged


@pytest.mark.parametrize('case', CASES, ids=[case[0] for case in CASES])
@pytest.mark.parametrize('alias', ['symbolic', 'hard', 'none'])
@pytest.mark.parametrize('parent', ['owned', 'linked'])
@pytest.mark.parametrize('target', ['outside', 'published'])
def test_every_temporary_alias_witness_reaches_the_documented_writer(
    tmp_path, case, alias, parent, target
):
    planted, expected, damaged = exercise(tmp_path, case, alias, parent, target)
    assert planted == expected, (
        'Every HTML, settings and experiment witness must plant at the module temporary '
        'specified by the project-output ADR, for both parent placements'
    )
    assert damaged == (alias != 'none'), (
        'An unprotected write at the actual module temporary must damage every planted '
        'symbolic or hard referent and leave the unaliased control unchanged'
    )
