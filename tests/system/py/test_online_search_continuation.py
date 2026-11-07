"""Search memory, chunk boundaries and linked inputs use independent fixtures."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def search_host(tmp_path_factory):
    with run_online_host(
        tmp_path_factory.mktemp('search-continuation'),
        load_groups_only=True,
        failure_entries=False,
        offline_http=True,
        session_type='SearchContinuationSession',
    ) as host:
        yield host


def test_cell_rounding_at_nontrivial_values(search_host):
    search_host.check('precision')


@pytest.mark.parametrize('kind', ['structure', 'experiment', 'data'])
def test_field_placeholders_and_metadata_selectors(search_host, kind):
    search_host.check('placeholders', kind)


@pytest.mark.parametrize('kind', ['structure', 'experiment', 'data'])
def test_reopen_keeps_search_and_clear_discards_it(search_host, kind):
    search_host.check('memory', kind)


@pytest.mark.parametrize('outcome', ['success', 'retry'])
def test_cod_scroll_chunks_preserve_inventory_and_retry(search_host, outcome):
    search_host.check('chunks', outcome)


@pytest.mark.parametrize('kind', ['structure', 'experiment', 'data'])
def test_empty_collection_query_lists_every_entry_of_kind(search_host, kind):
    search_host.check('empty_kind', kind)


@pytest.mark.parametrize('formula', ['laCoO3', 'LaCoO3', 'la co o3'])
def test_case_free_formula_search_keeps_exact_match_first(search_host, formula):
    search_host.check('case_formula', formula)


@pytest.mark.parametrize('structure', ['missing', 'present'])
def test_full_experiment_brings_or_reuses_its_structure_in_one_undo(search_host, structure):
    search_host.check('linked_structure', structure)


def test_journal_table_generator_uses_the_independent_local_csv(tmp_path):
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            str(root / 'tools/data/build_journal_abbreviations.py'),
            str(tmp_path),
            '--lists',
            'general',
            '--from',
            str(root / 'tests/fixtures/online_popup_contract'),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, 'The journal table builds without any network access'
    table = json.loads((tmp_path / 'journal-abbreviations.json').read_text())
    assert table['abbreviations'] == {
        'Physical Review B': 'Phys. Rev. B',
        'Journal of Solid State Chemistry': 'J. Solid State Chem.',
    }, 'Generated journal abbreviations equal the independent ISO 4 fixture mappings'
