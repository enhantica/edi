"""gates after the graded-start ladder moved to the crysta corpus.

Ruling 8d retired edi's 25 copied project directories. The surviving descent-study subjects
are now explicit ``graded-start:<family>:<rung>`` labels on corpus cases, and their outcomes are
committed derived-value records. These gates consume that declaration; they never recreate the
deleted second home or execute another fit.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import yaml

from conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]


# Resolved LAZILY: a module-level call raises at IMPORT when the pinned corpus predates the
# case, which breaks collection for the whole suite rather than failing this module's tests.
def _manifest_path() -> Path:
    return corpus_case_dir('si-sepd-s2').parent / 'manifest.yml'


# The exact surviving promoted rungs after the ruling-8d disposition. This is intentionally not
# a claim that all 25 former copies survive: their data were duplicate and the manifest labels are
# now the single descent-study inventory.
EXPECTED_GRADED_STARTS = {
    'graded-start:cosio-d20:s3': 'seam-cosio-d20-s3',
    'graded-start:lbco-hrpt:s1': 'lbco-hrpt-s2',
    'graded-start:lbco-hrpt:s2': 'seam-lbco-hrpt-s2',
    'graded-start:ncaf-wish-5bank:s1': 'seam-ncaf-wish-5bank-s1',
    'graded-start:ncaf-wish-5bank:s5': 'seam-ncaf-wish-5bank-s5',
    'graded-start:si-sepd:s1': 'si-sepd-s2',
    'graded-start:si-sepd:s3': 'seam-si-sepd-s3',
}


def _cases() -> dict[str, dict[str, Any]]:
    document = yaml.safe_load(_manifest_path().read_text(encoding='utf-8'))
    return {case['id']: case for case in document['cases']}


def _tagged_cases() -> dict[str, str]:
    tagged: dict[str, str] = {}
    for case_id, case in _cases().items():
        for tag in case.get('tags', []):
            if not tag.startswith('graded-start:'):
                continue
            assert tag not in tagged, f'duplicate graded-start label {tag!r}'
            tagged[tag] = case_id
    return tagged


def _expected(case_id: str) -> dict[str, Any]:
    return json.loads((corpus_case_dir(case_id) / 'expected.json').read_text(encoding='utf-8'))


def test_c11_t26_hidden_consumer_contains_no_live_fit_or_calculation() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding='utf-8'))
    forbidden = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            'fit',
            'calculate',
        }:
            forbidden.append((node.lineno, node.func.attr))
        if isinstance(node.func, ast.Name) and node.func.id in {'run', 'Popen'}:
            forbidden.append((node.lineno, node.func.id))
    assert not forbidden, f'F-rec consumer grew a live execution surface: {forbidden}'
