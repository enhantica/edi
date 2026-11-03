"""The real app keeps dictionary displays and the instrument description selectors."""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]


def run_actor(tmp_path, function):
    if function == 'DictionaryDisplay::test_page:experiment':
        run_actor(tmp_path, 'DescriptionLoadState::test_description_load_state')
    assert (ROOT / 'core/include/edi/display.hpp').is_file(), (
        'The app consumes the public dictionary through its core display bridge'
    )
    dictionary = ROOT / 'build/crysta-src/data/dictionary/parameters.yaml'
    assert dictionary.is_file(), 'App label expectations come from the SDK pin source dictionary'
    source = yaml.safe_load(dictionary.read_text())
    assert isinstance(source.get('categories'), list), (
        'The SDK source dictionary contains the reviewed category display metadata'
    )
    rows = source['parameters'] + source.get('items', [])
    expected = {
        'items': {row['uid']: row for row in rows},
        'categories': {row['id']: row for row in source['categories']},
        'tokens': [],
    }
    expected['tokens'] = [
        option['token']
        for row in rows
        for option in row.get('options', [])
        if option['token'] != option['display_name']
    ]
    (tmp_path / 'dictionary.json').write_text(json.dumps(expected))
    group_source = Path(
        os.environ.get(
            'EDI_TEST_INSTRUMENT_GROUP_SOURCE',
            ROOT / 'app/qml/Pages/Experiment/InstrumentGroup.qml',
        )
    )
    (tmp_path / 'instrument-group.qml').write_text(
        group_source.read_text(encoding='utf-8'), encoding='utf-8'
    )
    configured = os.environ.get('EDI_APP_TEST_RUNNER')
    binary = Path(configured) if configured else ROOT / 'build/app/app/edi_app_tests'
    assert binary.is_file(), 'The dictionary app gate executes the production Qt test host'
    result = subprocess.run(
        [
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_dictionary_display.qml'),
            *(
                [function, 'DictionaryDisplay::test_instrument_selectors']
                if function == 'DictionaryDisplay::test_page:experiment'
                else [function]
            ),
            '-o',
            '-,txt',
        ],
        cwd=ROOT,
        env={
            **os.environ,
            'EDI_ACCEPTANCE_REFERENCE': str(tmp_path),
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'The real app satisfies dictionary displays and instrument description selectors: '
        + output
    )
    assert 'PASS' in output and '0 failed' in output, (
        'The selected app actor reaches a passing assertion rather than an empty launch'
    )


@pytest.mark.parametrize('case', ['structure', 'experiment', 'analysis', 'report'])
def test_actual_app_pages_follow_dictionary_contract(tmp_path, case):
    run_actor(tmp_path, 'DictionaryDisplay::test_page:' + case)


@pytest.mark.parametrize(
    'case',
    [
        'cell',
        'fractional',
        'occupancy',
        'instrument',
        'peak',
        'background',
        'linked_structure',
        'absorption',
        'preferred_orientation',
    ],
)
def test_actual_app_numeric_categories_follow_file_spelling(tmp_path, case):
    run_actor(tmp_path, 'DictionaryDisplay::test_category:' + case)
