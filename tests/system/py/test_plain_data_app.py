"""Observe the production view model without enabling the GUI test groups."""

from __future__ import annotations

import copy
import json
import os
import re
import shlex
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pytest

from tests.conftest import crysta_reference_prefix
from tests.integration.py.test_plain_data_picker import require_picker
from tests.integration.py.test_scan_app_contract import require_availability, source

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/plain_data'
CASES = json.loads((FIXTURE / 'cases.json').read_text())


@pytest.fixture(scope='module')
def native_probe(tmp_path_factory):
    header = (ROOT / 'app/src/project_view_model.hpp').read_text()
    assert 'createStructure(' in header and 'loadData(' in header, (
        'Create structure / Load data: the product view model must expose the actions '
        'declared in the visible native host contract before execution'
    )
    build = tmp_path_factory.mktemp('plain-data-host')
    command = [
        'pixi',
        'run',
        '-e',
        'app',
        'python',
        str(FIXTURE / 'build_probe.py'),
        '--root',
        str(ROOT),
        '--build',
        str(build),
        '--sdk',
        str(crysta_reference_prefix()),
    ]
    gui = os.environ.get('EDI_SCAN_APP_GUI_SOURCE')
    if gui:
        command += ['--gui-source', gui]
    completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=600)
    assert completed.returncode == 0, (
        'Plain-data native host: compile the actual app module against the installed SDK\n'
        + completed.stdout
        + completed.stderr
    )
    return build / 'cmake/tests/fixtures/plain_data/plain_data_probe'


def run(native_probe, tmp_path, mode='load', beam='cwl', case='two_columns', escape='none'):
    work = tmp_path / (mode + '-' + beam + '-' + case + '-' + escape)
    work.mkdir()
    spec = CASES[beam + '/' + case]
    command = [
        str(native_probe),
        mode,
        str(FIXTURE),
        str(work),
        beam,
        escape,
        beam + '/' + case + '/' + spec['file'],
    ]
    environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='software')
    completed = subprocess.run(
        command, env=environment, capture_output=True, text=True, check=False, timeout=30
    )
    assert completed.returncode == 0, (
        'Plain-data native host: complete the observed action without process failure\n'
        + completed.stderr
    )
    return json.loads(completed.stdout.splitlines()[-1])


def require_success(record):
    assert 'error' not in record, (
        'Plain-data workflow: all admitted view-model actions must complete: '
        + record.get('error', '')
    )


def rows(state):
    e = state['experiments'][0]
    return [list(row) for row in zip(e['x'], e['y'], e['sigma'], strict=True)]


def require_reopened(record, expected):
    require_success(record)
    assert record['opened'] and rows(record['reopened']) == expected, (
        'Save plain data: reopen solely from the saved project after deleting the input file'
    )


def require_unlinked(state):
    assert state['experiments'][0]['links'] == ['structure1', 'structure2'], (
        'Create structure: a new structure must never link to an existing experiment'
    )


def configuration(state):
    experiment = state['experiments'][0]
    return {
        'parameters': state['parameters'],
        **{
            key: experiment[key]
            for key in ['instrument', 'peak', 'background', 'excluded', 'weight', 'links']
        },
    }


def content(state):
    return {key: state[key] for key in ['experiments', 'structures', 'parameters']}


def require_lifecycle(record, beam):
    require_success(record)
    original = record['before']
    expected = CASES[beam + '/two_columns']['rows']
    for step in [
        'after',
        'afterTypeAttempt',
        'afterRangeAttempt',
        'reopened',
        'afterReopenedTypeAttempt',
        'afterReopenedRangeAttempt',
        'beforeLive',
        'firstData',
        'secondData',
        'undoSecond',
        'undoFirst',
    ]:
        expected_configuration = configuration(original)
        if step in {'reopened', 'afterReopenedTypeAttempt', 'afterReopenedRangeAttempt'}:
            expected_configuration['weight'] = 1
        assert record[step]['fittingMode'] == original['fittingMode'] == 'single', (
            'Load data lifecycle: this one-experiment witness retains Single mode'
        )
        assert configuration(record[step]) == expected_configuration, (
            'Load data lifecycle: non-default instrument, peak, background, exclusions, '
            'links and parameter state survive; inactive joint weights reset on reopen: ' + step
        )
    assert (
        original['experiments'][0]['excluded'] == ([[9000, 9100]] if beam == 'tof' else [[60, 61]])
        and original['experiments'][0]['weight'] == 2.5
    ), 'Load data lifecycle control: exclusions and dataset weight begin non-default'
    assert any(value[0] == 0.0625 for value in original['experiments'][0]['peak']) and (
        original['experiments'][0]['background'][0][1] == 4.25
    ), 'Load data lifecycle control: peak and background begin with seeded non-default values'
    assert any(
        value[0] == (7 if beam == 'tof' else 0.125)
        for value in original['experiments'][0]['instrument']
    ), 'Load data lifecycle control: the active instrument offset begins non-default'
    for step, case in [
        ('after', 'two_columns'),
        ('firstData', 'two_columns'),
        ('secondData', 'three_columns'),
        ('undoSecond', 'two_columns'),
        ('reopened', 'two_columns'),
    ]:
        expected_rows = CASES[beam + '/' + case]['rows']
        measured = record[step]['experiments'][0]
        assert rows(record[step]) == expected_rows and measured['range'] == [
            expected_rows[0][0],
            expected_rows[-1][0],
            expected_rows[1][0] - expected_rows[0][0],
        ], (
            'Load data lifecycle: every measured state exposes the independent rows and range: '
            + step
        )
        assert not measured['simulation'] and measured['beam'] == (
            'time-of-flight' if beam == 'tof' else 'constant wavelength'
        ), (
            'Load data lifecycle: each measured state retains its beam mode and measured lock: '
            + step
        )
        assert measured['canLoadData'], (
            'Load data lifecycle: every non-scan measured state admits another load: ' + step
        )
    after = record['after']['experiments'][0]
    assert record['loaded'] and rows(record['after']) == expected, (
        'Load data: the created experiment receives the hand-constructed measured triples'
    )
    assert (
        not after['simulation']
        and after['canLoadData']
        and record['typeRefused']
        and (record['rangeRefused'])
    ), 'Load data: the measured object refuses type/range writes and still admits replacement'
    assert content(record['afterTypeAttempt']) == content(record['after']) and (
        content(record['afterRangeAttempt']) == content(record['after'])
    ), (
        'Load data write boundary: refused type and range actions '
        'preserve the complete measured state'
    )
    assert after['range'] == [expected[0][0], expected[-1][0], expected[1][0] - expected[0][0]], (
        'Load data: visible range reports measured start, end and nontrivial step'
    )
    assert content(record['reopened']) == content(record['after']) | {
        'experiments': [dict(after, weight=1)]
    }, 'Save plain data: reopen preserves all measured state and original file/name metadata'
    assert (
        record['reopenedTypeRefused']
        and record['reopenedRangeRefused']
        and (
            content(record['afterReopenedTypeAttempt']) == content(record['reopened'])
            and content(record['afterReopenedRangeAttempt']) == content(record['reopened'])
        )
    ), (
        'Save plain data write boundary: reopened measured objects '
        'refuse actual type and range edits'
    )
    assert (
        record['firstLoad']
        and record['secondLoad']
        and (rows(record['secondData']) == CASES[beam + '/three_columns']['rows'])
    ), 'Load data: each replacement receives its complete independently constructed data'
    first = record['firstData']['experiments'][0]
    second = record['secondData']['experiments'][0]
    assert (
        first['file'] == after['file']
        and first['name'] == after['name']
        and (second['file'] == 'replacement.xye' and second['name'] == first['name'])
    ), 'Load data naming: replacement changes the File column while preserving a non-default name'
    assert content(record['undoSecond']) == content(record['firstData']), (
        'Undo replacement: one Undo restores complete rows, file/name and preserved configuration'
    )
    assert content(record['undoFirst']) == content(record['beforeLive']), (
        'Undo first load: one Undo restores the complete simulation and its previous metadata'
    )
    assert record['undoTypeEditable'] and record['afterUndoTypeEdit']['experiments'][0][
        'beam'
    ] == ('constant wavelength' if beam == 'tof' else 'time-of-flight'), (
        'Undo load editability: the restored simulation accepts an actual nonidentity type edit'
    )
    assert record['undoRangeEditable'] and (
        record['afterUndoRangeEdit']['experiments'][0]['range'] == [31, 34, 0.75]
    ), 'Undo load editability: the restored simulation accepts an actual non-default range edit'


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
def test_load_lock_replace_and_single_step_undo(native_probe, tmp_path, beam):
    record = run(native_probe, tmp_path, beam=beam)
    require_lifecycle(record, beam)


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
def test_saved_data_is_self_contained_and_imported_data_can_be_replaced(
    native_probe, tmp_path, beam
):
    record = run(native_probe, tmp_path, beam=beam)
    expected = CASES[beam + '/two_columns']['rows']
    require_reopened(record, expected)
    assert rows(record['ediImported']) == expected, (
        'Load experiment: the explicitly imported .edi supplies the saved measured rows'
    )
    assert (
        record['ediLoadSucceeded']
        and rows(record['afterEdiLoadAttempt']) == CASES[beam + '/three_columns']['rows']
    ), 'Load data admission: an imported non-scan experiment receives the complete replacement'
    assert not record['reopened']['experiments'][0]['simulation'], (
        'Save plain data: the reopened experiment retains its measured-data type lock'
    )


@pytest.mark.parametrize(
    ('mode', 'expected_name'),
    [('load', 'pattern'), ('renamed', 'User_name')],
    ids=['default-name', 'user-name'],
)
def test_filename_and_user_name(native_probe, tmp_path, mode, expected_name):
    record = run(native_probe, tmp_path, mode=mode)
    require_success(record)
    if mode == 'renamed':
        assert record['before']['experiments'][0]['name'] == expected_name, (
            'Load data naming: the valid non-default user name must be retained before import'
        )
        assert record['beforeLive']['experiments'][0]['name'] == expected_name, (
            'Load data naming: replacement and Undo start with the same valid user name'
        )
    e = record['after']['experiments'][0]
    assert e['name'] == expected_name and e['file'] == 'pattern.xy', (
        'Load data naming: default names take the stem, user names survive, '
        'File shows the original filename'
    )
    assert record['reopened']['experiments'][0]['file'] == 'pattern.xy', (
        'Save plain data: the original File column label survives save and reopen'
    )


def message_count(token):
    try:
        value = Decimal(token.replace('\u2212', '-'))
    except InvalidOperation:
        pytest.fail('Load data message count: a numeric claim must be a valid number: ' + token)
    assert value.is_finite() and value >= 0 and value == value.to_integral_value(), (
        'Load data message count: every numeric claim must be a finite nonnegative integer: '
        + token
    )
    return value


def require_message(message, counts):
    text = message.lower()
    row = r'row(?:\(s\)|s)?'
    line = r'line(?:\(s\)|s)?'
    number = (
        r'(?<![\w.+\u2212-])([+\u2212-]?(?:\d[\d.e+-]*|\.\d[\d.e+-]*|inf(?:inity)?|nan))(?![\w.])'
    )
    patterns = {
        'skipped': [
            rf'{number}\s+{line}\s+(?:skipped|unparsable|malformed)',
            rf'{number}\s+(?:skipped|unparsable|malformed)\s+{line}',
            rf'(?:skipped|unparsable|malformed)\s+{line}\s*[:=]\s*{number}',
        ],
        'nonpositive': [
            (
                rf'{number}\s+(?:{row}\s+(?:with\s+)?)?'
                r'(?:non[- ]?positive|(?:intensity|y)\s*(?:≤|<=)\s*0)'
            ),
            rf'non[- ]?positive(?:\s+{row})?\s*[:=]\s*{number}',
        ],
        'duplicates': [
            (
                rf'{number}\s+(?:{row}\s+(?:with\s+(?:a\s+)?)?)?'
                r'(?:duplicates?|duplicated|repeated\s+x)'
            ),
            rf'duplicates?(?:\s+rows?)?\s*[:=]\s*{number}',
        ],
        'reordered': [
            rf'{number}\s+(?:{row}\s+)?(?:reordered|sorted)',
            rf'(?:reordered|sorted)(?:\s+rows?)?\s*[:=]\s*{number}',
        ],
    }
    for category, alternatives in patterns.items():
        observed = [
            message_count(match.group(1))
            for pattern in alternatives
            for match in re.finditer(pattern, text)
        ]
        assert len(observed) <= 1 and (observed[0] if observed else 0) == counts[category], (
            'Load data message count: each category owns its number, including zero: ' + category
        )
    derived = bool(re.search(r'(?:sigma|\u03c3).*?(?:sqrt\s*\(|√)', text))
    assert derived == bool(counts['derived']), (
        'Load data message uncertainty: the derived-sigma note occurs exactly when used'
    )
    if derived:
        reported = re.findall(r'used\s+for\s+' + number + r'\s+' + row, text)
        assert not reported or (
            len(reported) == 1 and message_count(reported[0]) == counts['derived']
        ), 'Load data message uncertainty: a reported derived-row count is bound to its own note'


@pytest.mark.parametrize(
    ('category', 'style'),
    [
        (category, style)
        for category in ['skipped', 'nonpositive', 'duplicates', 'reordered']
        for style in ['number-first', 'category-first']
    ]
    + [('derived', 'number-first')],
)
@pytest.mark.parametrize('damage', ['negative', 'fractional', 'nonfinite'])
def test_message_counts_reject_invalid_numbers_in_every_field(category, style, damage):
    counts = dict(CASES['cwl/three_columns']['counts'], **{category: 2})

    def message(token):
        labels = {
            'skipped': ('skipped lines', 'skipped lines'),
            'nonpositive': ('non-positive rows', 'non-positive rows'),
            'duplicates': ('duplicates', 'duplicates'),
            'reordered': ('reordered', 'reordered rows'),
        }
        if category == 'derived':
            return 'sigma=sqrt(y) used for ' + token + ' rows'
        before, after = labels[category]
        return token + ' ' + before if style == 'number-first' else after + ': ' + token

    # Equivalent numeric spellings still denote the independently constructed integer two.
    for token in ['2', '+2', '2.0', '2e0']:
        require_message(message(token), counts)
    damaged = {'negative': ['-2', '\u22122'], 'fractional': ['0.2'], 'nonfinite': ['nan', 'inf']}[
        damage
    ]
    for token in damaged:
        with pytest.raises(AssertionError, match='Load data message count'):
            require_message(message(token), counts)
        if category != 'derived':
            # An unrecognized claim must not become an omitted zero-category count.
            zero = dict(counts, **{category: 0})
            with pytest.raises(AssertionError, match='Load data message count'):
                require_message(message(token), zero)


@pytest.mark.parametrize(('beam', 'case'), [tuple(key.split('/')) for key in CASES])
def test_one_load_message_reports_constructed_counts(native_probe, tmp_path, beam, case):
    record = run(native_probe, tmp_path, mode='counts', beam=beam, case=case)
    require_success(record)
    assert record['loaded'] and rows(record['after']) == CASES[beam + '/' + case]['rows'], (
        'Load data message control: its actual import succeeds with the constructed rows'
    )
    messages = record['messages']
    assert len(messages) == 1, (
        'Load data messages: one import appends exactly one status-bar entry'
    )
    require_message(messages[0], CASES[beam + '/' + case]['counts'])


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
@pytest.mark.parametrize('wording', ['inequality', 'category-first'])
def test_message_observer_accepts_equivalent_category_wording(beam, wording):
    counts = CASES[beam + '/nonpositive']['counts']
    message = (
        '2 row(s) with intensity ≤ 0 skipped'
        if wording == 'inequality'
        else 'non-positive rows: 2'
    )
    require_message(message, counts)


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
@pytest.mark.parametrize(
    'damage',
    [
        'swapped',
        'invented-skipped',
        'invented-nonpositive',
        'invented-duplicates',
        'invented-reordered',
        'missing-skipped',
        'missing-nonpositive',
        'missing-duplicates',
        'missing-reordered',
    ],
)
def test_message_observer_rejects_cross_category_and_false_counts(beam, damage):
    if damage == 'swapped':
        counts = CASES[beam + '/unsorted_duplicates']['counts']
        require_message('1 duplicate; 3 reordered', counts)
        message = '3 duplicates, 1 reordered'
    elif damage.startswith('invented-'):
        counts = CASES[beam + '/three_columns']['counts']
        require_message('3 measured points loaded', counts)
        message = {
            'invented-skipped': '2 skipped lines',
            'invented-nonpositive': '2 non-positive rows',
            'invented-duplicates': '2 duplicates',
            'invented-reordered': '2 reordered',
        }[damage]
    else:
        category = damage.removeprefix('missing-')
        counts = dict(CASES[beam + '/three_columns']['counts'], **{category: 2})
        good = {
            'skipped': '2 skipped lines',
            'nonpositive': '2 non-positive rows',
            'duplicates': '2 duplicates',
            'reordered': '2 reordered',
        }[category]
        require_message(good, counts)
        message = '3 measured points loaded'
    with pytest.raises(AssertionError, match='Load data message count'):
        require_message(message, counts)


@pytest.fixture(scope='module')
def lifecycle_control():
    """Hand-constructed observation control; never a production-output reference."""
    experiment = {
        'instrument': [[0.125, False]],
        'peak': [[0.0625, False]],
        'background': [[14, 4.25, False]],
        'excluded': [[60, 61]],
        'weight': 2.5,
        'links': ['structure1'],
        'name': 'experiment1',
        'file': '',
        'beam': 'constant wavelength',
        'simulation': True,
        'canLoadData': True,
        'range': [14, 16, 0.5],
        'x': [],
        'y': [],
        'sigma': [],
    }
    before = {
        'fittingMode': 'single',
        'experiments': [experiment],
        'structures': ['unchanged structure'],
        'parameters': [[0.125, False], [0.0625, False], [4.25, False]],
    }
    first = copy.deepcopy(before)
    e = first['experiments'][0]
    expected = CASES['cwl/two_columns']['rows']
    e.update(
        simulation=False,
        name='pattern',
        file='pattern.xy',
        range=[expected[0][0], expected[-1][0], expected[1][0] - expected[0][0]],
    )
    e.update(
        zip(
            ['x', 'y', 'sigma'],
            [list(column) for column in zip(*expected, strict=True)],
            strict=True,
        )
    )
    second = copy.deepcopy(first)
    expected_second = CASES['cwl/three_columns']['rows']
    second['experiments'][0].update(file='replacement.xye')
    second['experiments'][0].update(
        zip(
            ['x', 'y', 'sigma'],
            [list(column) for column in zip(*expected_second, strict=True)],
            strict=True,
        )
    )
    type_edited = copy.deepcopy(before)
    type_edited['experiments'][0]['beam'] = 'time-of-flight'
    range_edited = copy.deepcopy(type_edited)
    range_edited['experiments'][0]['range'] = [31, 34, 0.75]
    record = {
        'before': before,
        'beforeLive': copy.deepcopy(before),
        'after': first,
        'afterTypeAttempt': copy.deepcopy(first),
        'afterRangeAttempt': copy.deepcopy(first),
        'reopened': copy.deepcopy(first),
        'afterReopenedTypeAttempt': copy.deepcopy(first),
        'afterReopenedRangeAttempt': copy.deepcopy(first),
        'firstData': copy.deepcopy(first),
        'secondData': second,
        'undoSecond': copy.deepcopy(first),
        'undoFirst': copy.deepcopy(before),
        'loaded': True,
        'typeRefused': True,
        'rangeRefused': True,
        'reopenedTypeRefused': True,
        'reopenedRangeRefused': True,
        'firstLoad': True,
        'secondLoad': True,
        'undoTypeEditable': True,
        'undoRangeEditable': True,
        'afterUndoTypeEdit': type_edited,
        'afterUndoRangeEdit': range_edited,
    }
    for step in ('reopened', 'afterReopenedTypeAttempt', 'afterReopenedRangeAttempt'):
        record[step]['experiments'][0]['weight'] = 1
    require_lifecycle(record, 'cwl')
    return record


@pytest.mark.parametrize(
    ('step', 'field'),
    [
        ('after', 'excluded'),
        ('secondData', 'instrument'),
        ('undoSecond', 'peak'),
        ('undoFirst', 'background'),
        ('reopened', 'weight'),
        ('after', 'fittingMode'),
        ('undoSecond', 'file'),
        ('undoSecond', 'name'),
        ('undoFirst', 'file'),
        ('undoTypeEditable', 'action'),
        ('undoRangeEditable', 'action'),
        ('reopenedTypeRefused', 'action'),
        ('reopenedRangeRefused', 'action'),
        ('firstData', 'x'),
        ('secondData', 'range'),
        ('undoSecond', 'simulation'),
        ('reopened', 'beam'),
        ('secondData', 'canLoadData'),
    ],
)
def test_lifecycle_observer_consumes_configuration_metadata_and_actual_edits(
    lifecycle_control, step, field
):
    changed = copy.deepcopy(lifecycle_control)
    if field == 'fittingMode':
        changed[step]['fittingMode'] = 'joint'
    elif field == 'action':
        changed[step] = False
    else:
        experiment = changed[step]['experiments'][0]
        if field in {'x', 'range'}:
            experiment[field][0] += 0.125
        elif field == 'simulation':
            experiment[field] = True
        elif field == 'canLoadData':
            experiment[field] = False
        elif field == 'beam':
            experiment[field] = 'time-of-flight'
        elif field in {'excluded', 'background'}:
            experiment[field] = []
        elif field in {'instrument', 'peak'}:
            experiment[field][0][0] += 1
        elif field == 'weight':
            experiment[field] = 2.5
        else:
            experiment[field] = 'wrong-restored-metadata'
    assert changed != lifecycle_control, (
        'Lifecycle observer escape: alter its consumed state or actual edit-action observation'
    )
    with pytest.raises(AssertionError, match=r'Load data|Undo|Save plain data'):
        require_lifecycle(changed, 'cwl')


def test_default_structure_matches_frozen_beta_cif(native_probe, tmp_path):
    record = run(native_probe, tmp_path, mode='structure')
    require_success(record)
    reference = (FIXTURE / 'default.cif').read_text()
    assert (
        '_space_group_name_H-M_alt "P b n m"' in reference and 'O O 0 0 0 1 Biso 0' in reference
    ), (
        'Create structure reference: the frozen upstream block declares '
        'the expected group and oxygen site'
    )
    assert record['created'] and record['createdSecond'], (
        'Create structure: both successive creation actions must succeed'
    )
    tokens = shlex.split(reference)
    expected = {
        'name': 'structure1',
        'group': tokens[tokens.index('_space_group_name_H-M_alt') + 1],
        'cell': [
            float(tokens[tokens.index('_cell_' + tag) + 1])
            for tag in [
                'length_a',
                'length_b',
                'length_c',
                'angle_alpha',
                'angle_beta',
                'angle_gamma',
            ]
        ],
        'sites': [{'id': 'O', 'type': 'O', 'xyz': [0, 0, 0], 'occupancy': 1, 'biso': 0}],
    }
    assert record['first']['structures'][0] == expected, (
        'Create structure: all cell, group and site values equal the frozen beta default CIF'
    )
    assert [s['name'] for s in record['second']['structures']] == ['structure1', 'structure2'], (
        'Create structure: successive creations allocate increasing default names'
    )
    assert record['undo']['structures'] == record['first']['structures'], (
        'Undo create structure: one undo removes only the last created structure'
    )


def test_link_all_unlinked_new_structure_and_atomic_remove_undo(native_probe, tmp_path):
    record = run(native_probe, tmp_path, mode='links')
    require_success(record)
    assert record['newExperiment']['experiments'][0]['links'] == ['structure1', 'structure2'], (
        'Create experiment: automatically link every existing structure'
    )
    require_unlinked(record['newStructure'])
    assert record['removed']['experiments'][0]['links'] == ['structure2'], (
        'Remove structure: remove all referring experiment links in the same edit'
    )
    assert [s['name'] for s in record['removed']['structures']] == ['structure2', 'structure3'], (
        'Remove structure: remove the selected structure and retain every other structure'
    )
    assert (
        record['undo']['structures'] == record['newStructure']['structures']
        and record['undo']['experiments'] == record['newStructure']['experiments']
    ), 'Undo remove structure: one undo restores both the structure and all experiment links'
    assert record['messages'], (
        'Remove linked structure: report the removed experiment links in Messages'
    )


def test_mixed_project_create_fit_measured_only_calculate_all(native_probe, tmp_path):
    record = run(native_probe, tmp_path, mode='mixed')
    require_success(record)
    assert record['createdExtra'] and record['mixed']['canCreate'], (
        'Mixed project: measured data must not disable Create experiment'
    )
    assert len(record['calculated']) == 2 and all(count > 0 for count in record['calculated']), (
        'Mixed project: calculation covers both the measured and data-less experiment'
    )
    assert record['fitPoints'] == 3 and record['afterFit']['experiments'][1]['simulation'], (
        'Mixed project: fitting consumes only measured points and keeps the data-less experiment'
    )


def test_packet_escape_controls_reject_bad_observations():
    good = {'opened': True, 'reopened': {'experiments': [{'x': [1], 'y': [4], 'sigma': [2]}]}}
    require_reopened(good, [[1, 4, 2]])
    with pytest.raises(AssertionError, match='Plain-data workflow'):
        require_reopened({'error': 'external data required on reopen'}, [[1, 4, 2]])
    require_unlinked({'experiments': [{'links': ['structure1', 'structure2']}]})
    with pytest.raises(AssertionError, match='Create structure'):
        require_unlinked({'experiments': [{'links': ['structure1', 'structure2', 'structure3']}]})


@pytest.mark.parametrize(('mode', 'escape'), [('load', 'source-reopen'), ('links', 'link-new')])
def test_packet_escapes_reach_the_native_actions(native_probe, tmp_path, mode, escape):
    control = run(native_probe, tmp_path, mode=mode)
    require_success(control)
    mutated = run(native_probe, tmp_path, mode=mode, escape=escape)
    if mode == 'load':
        require_reopened(control, CASES['cwl/two_columns']['rows'])
        assert mutated.get('error') == 'external data required on reopen', (
            'Save-data escape: the actor must actually try to reopen the deleted source file'
        )
        with pytest.raises(AssertionError, match='Plain-data workflow'):
            require_reopened(mutated, CASES['cwl/two_columns']['rows'])
    else:
        require_unlinked(control['newStructure'])
        require_success(mutated)
        with pytest.raises(AssertionError, match='Create structure'):
            require_unlinked(mutated['newStructure'])


def test_nonpositive_retention_escape_reaches_the_loaded_model(native_probe, tmp_path):
    control = run(native_probe, tmp_path, case='nonpositive')
    require_success(control)
    expected = CASES['cwl/nonpositive']['rows']
    assert rows(control['after']) == expected, (
        'Bragg import control: the actual admitted dataset excludes both nonpositive rows'
    )
    mutated = run(native_probe, tmp_path, case='nonpositive', escape='retain-nonpositive')
    assert rows(mutated['after'])[-1] == [18.0, 0.0, 1.0], (
        'Nonpositive escape: the actor reaches the native measured model and retains a zero row'
    )
    assert rows(mutated['after']) != expected, (
        'Bragg import observer: a zero row retained in the actual model defeats exact row equality'
    )


def test_desktop_browser_picker_and_editability_bindings_share_load_path():
    qml = source('qml/Pages/Experiment/ExperimentsGroup.qml')
    require_availability(qml)
    require_picker(qml, False)
    require_picker(qml, True)
    range_qml = source('qml/Pages/Experiment/MeasuredRangeGroup.qml')
    type_qml = source('qml/Pages/Experiment/ExperimentTypeGroup.qml')
    assert (
        'experiment.calculationOnly' in range_qml and 'experiment.calculationOnly' in type_qml
    ), 'Load data editability: measured data disables both range and type selectors'
    structure_qml = source('qml/Pages/Structure/StructuresGroup.qml')
    assert 'Create structure' in structure_qml and '.createStructure()' in structure_qml, (
        'Create structure button: replace the disabled manual-definition '
        'action in the shipped page'
    )
    cmake = (ROOT / 'app/CMakeLists.txt').read_text()
    assert 'src/web_files.cpp' in cmake, (
        'Load data browser build: the common app target compiles its picker implementation'
    )
    browser = source('src/web_files.cpp')
    assert 'EMSCRIPTEN' in browser and ('openFile' in browser or 'openFiles' in browser), (
        'Load data browser build: compile the picker implementation for the web platform'
    )


@pytest.mark.parametrize('kind', ['experiment', 'structure'])
@pytest.mark.parametrize('case', ['title', 'upper', 'mixed'])
@pytest.mark.parametrize('occupied', [1, 2], ids=['one-held-name', 'two-held-names'])
def test_automatic_creation_uses_the_persisted_casefold_identity_domain(
    native_probe, tmp_path, kind, case, occupied
):
    # Independent reference: the smallest positive suffix whose ASCII case-folded name
    # is absent. The writer owns this identity domain on every filesystem.
    spelling = {
        'title': kind.capitalize(),
        'upper': kind.upper(),
        'mixed': 'eXpErImEnT' if kind == 'experiment' else 'sTrUcTuRe',
    }[case]
    environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='software')
    completed = subprocess.run(
        [
            str(native_probe),
            'identity',
            str(FIXTURE),
            str(tmp_path),
            'cwl',
            kind,
            spelling,
            str(occupied),
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, (
        'Creation identity: the real app host must complete '
        'the automatic action and save observation\n' + completed.stderr
    )
    record = json.loads(completed.stdout.splitlines()[-1])
    require_success(record)
    assert record['beforeSaved'], (
        'Creation identity: the independently named input must save before automatic creation: '
        + record['beforeSaveError']
    )
    category = kind + 's'
    prior_names = [spelling + str(i + 1) for i in range(occupied)]
    assert [row['name'] for row in record['before'][category]] == prior_names, (
        'Creation identity: the app fixture must contain '
        'independently specified case-variant names'
    )
    assert record['created'] and record['recreated'], (
        'Creation identity: automatic experiment and structure creation '
        'remain available beside user names'
    )
    expected = prior_names + [kind + str(occupied + 1)]
    assert [row['name'] for row in record['after'][category]] == expected, (
        'Creation identity: both automatic actions choose '
        'the first unused persisted case-folded name'
    )
    assert [row['name'] for row in record['undone'][category]] == prior_names, (
        'Creation identity: Undo removes only the newly created object '
        'and retains every prior spelling'
    )
    assert record['saved'], (
        'Creation identity: an admitted automatic creation must save '
        'without a case-collision refusal: ' + record['saveError']
    )
    assert record['opened'], 'Creation identity: a successfully saved automatic object must reopen'
    assert [row['name'] for row in record['reopened'][category]] == expected, (
        'Creation identity: save and reopen retain the complete ordered identity set'
    )


SCAN_REFERENCE = json.loads((ROOT / 'tests/fixtures/correlations/scan-reference.json').read_text())


def observe_correlations(native_probe, tmp_path, action, mode, history):
    work = tmp_path / 'work'
    work.mkdir()
    result = subprocess.run(
        [
            str(native_probe),
            action,
            str(ROOT / f'tests/fixtures/correlations/scan-{mode}'),
            str(work),
            mode,
            'history' if history else 'fresh',
            'unused',
        ],
        env=dict(os.environ, QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='software'),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, (
        'Correlation lifecycle: the actual native app/core actor must complete: ' + result.stderr
    )
    record = json.loads(result.stdout.splitlines()[-1])
    assert 'error' not in record, (
        'Correlation lifecycle: all real load, fit, save and resume actions must succeed: '
        + record.get('error', '')
    )
    return record


def require_dataset_matrix(matrix, case):
    names = matrix['labels']
    assert matrix['available'] == 3, (
        "A Single fit inside a scan must expose that dataset's three actual free parameters"
    )
    assert sorted(names) == sorted(case['names']), (
        'The selected dataset matrix must name the independent covariance reference parameters'
    )
    for row in range(3):
        for column in range(row):
            expected = case['matrix'][case['names'].index(names[row])][
                case['names'].index(names[column])
            ]
            assert matrix['values'][row * 3 + column] == pytest.approx(expected, abs=2e-4), (
                'A selected dataset must show its own normalized covariance, including signs'
            )


def require_core_file_pairs(pairs, case):
    actual = [pair for pair in pairs if Path(pair['file']).name == case['file']]
    assert len(actual) == 3, 'A completed file must retain every core pair after scan cancellation'
    observed = {
        tuple(sorted((pair['i'], pair['j']))): float(pair['coefficient']) for pair in actual
    }
    expected = {
        tuple(sorted((pair['parameter_unique_name_i'], pair['parameter_unique_name_j']))): pair[
            'correlation'
        ]
        for pair in case['rows']
    }
    assert observed == pytest.approx(expected, abs=2e-4), (
        'Completed-file covariance must match the external normal-equations reference'
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('history', [False, True], ids=['fresh', 'after-scan'])
def test_single_fit_in_scan_shows_saves_and_undoes_its_own_matrix(
    native_probe, tmp_path, mode, history
):
    record = observe_correlations(native_probe, tmp_path, 'correlation-single', mode, history)
    case = SCAN_REFERENCE['cases'][1]
    for step in ('fitted', 'selectedAgain', 'reopened'):
        require_dataset_matrix(record[step], case)
    require_core_file_pairs(record['reopened']['pairs'], case)
    assert {key: record['otherAfter'][key] for key in ('labels', 'values', 'available')} == {
        key: record['otherBefore'][key] for key in ('labels', 'values', 'available')
    }, "A Single fit must leave the other scan dataset's matrix and associations unchanged"
    assert record['undone'] == record['before'], (
        'Undo of a Single dataset fit must restore its previous matrix and core pairs exactly'
    )
    if history:
        assert record['reset']['available'] == 0, (
            'Reset fits must remove the selected dataset matrix'
        )
        assert record['undoReset'] == record['reopened'], (
            'Undo of Reset fits must restore the saved per-dataset matrix and core pairs'
        )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('history', [False, True], ids=['fresh', 'replace-old-pair'])
def test_cancelled_scan_retains_completed_core_pairs_and_resumes(
    native_probe, tmp_path, mode, history
):
    record = observe_correlations(native_probe, tmp_path, 'correlation-cancel', mode, history)
    assert record['cancelBeforeAny'] == record['before'], (
        'Cancellation before any file completes must preserve all previously held pairs'
    )
    assert record['completed'] == 1, (
        'The cancellation witness must complete exactly its first file'
    )
    assert len(record['cancelled']) == 3, (
        "Cancellation must retain only the completed file's pairs, replacing a stale pair"
    )
    require_core_file_pairs(record['cancelled'], SCAN_REFERENCE['cases'][0])
    assert record['reopened'] == record['cancelled'], (
        "Save and reload must retain a cancelled scan's completed core correlations exactly"
    )
    assert record['resumedFiles'] == ['02.xy'], (
        "Resume must fit only the unfinished dataset, without replacing the first dataset's pairs"
    )
    assert len(record['resumed']) == 6, "Resume must retain both files' complete covariance pairs"
    for case in SCAN_REFERENCE['cases']:
        require_core_file_pairs(record['resumed'], case)
    assert not record['noopFiles'], 'A completed scan resume must execute no file fits'
    assert record['noop'] == record['resumed'], (
        'A no-op resume must preserve every completed correlation and its dataset association'
    )
    assert record['memoryAfterSave'] == record['resumed'], (
        'Saving a scan must preserve all completed datasets correlations in memory'
    )
    require_core_file_pairs(record['completedReopened'], SCAN_REFERENCE['cases'][0])
    assert len(record['completedReopened']) == 3, (
        'A scan saves only its explicitly declared template dataset correlations'
    )


@pytest.mark.parametrize('kind', ['structure', 'experiment', 'site', 'point'])
def test_app_rename_follows_all_saved_references_and_undo(native_probe, tmp_path, kind):
    work = tmp_path / 'work'
    work.mkdir()
    completed = subprocess.run(
        [
            str(native_probe),
            'correlation-rename',
            str(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment'),
            str(work),
            'unused',
            kind,
            'unused',
        ],
        env=dict(os.environ, QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='software'),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, 'Reference renames must execute the actual native app actor'
    record = json.loads(completed.stdout.splitlines()[-1])
    assert 'error' not in record, (
        'All admitted app rename, save, reopen and Undo actions must succeed: '
        + record.get('error', '')
    )
    before = record['before']
    expected = copy.deepcopy(before)
    replacements = {
        'structure': [('phase.', 'new_phase.'), ('.phase.', '.new_phase.')],
        'experiment': [('bank.', 'new_bank.')],
        'site': [('.atom_site.A.', '.atom_site.new_site.')],
        'point': [('.background.pA.', '.background.new_point.')],
    }[kind]

    def follow(name):
        for old, new in replacements:
            name = name.replace(old, new)
        return name

    expected['aliases'] = [follow(name) for name in expected['aliases']]
    for pair in expected['pairs']:
        pair['i'] = follow(pair['i'])
        pair['j'] = follow(pair['j'])
    if kind == 'structure':
        expected['links'] = [
            'new_phase' if value == 'phase' else value for value in expected['links']
        ]
        expected['textures'] = [
            'new_phase' if value == 'phase' else value for value in expected['textures']
        ]
    assert record['renamed'] == expected, (
        'App renames must follow aliases, both correlation endpoints and link/texture rows'
    )
    assert record['reopened'] == expected, (
        'Save and reload must retain every app-rewritten reference'
    )
    assert record['undone'] == expected, (
        'Undo of removal after renaming must retain every rewritten reference'
    )


@pytest.mark.parametrize('kind', ['structure', 'experiment'])
@pytest.mark.parametrize('scenario', ['plain', 'scan', 'refusal'])
def test_literal_datablock_rename_undo_restores_references_template_and_saved_state(
    native_probe, tmp_path, kind, scenario
):
    work = tmp_path / 'rename-undo'
    work.mkdir()
    completed = subprocess.run(
        [
            str(native_probe),
            'correlation-rename-undo',
            str(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment'),
            str(work),
            'scan' if scenario == 'scan' else 'plain',
            kind,
            'refusal' if scenario == 'refusal' else 'accepted',
        ],
        env=dict(os.environ, QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='software'),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, (
        'Literal rename Undo must execute the actual application actor'
    )
    record = json.loads(completed.stdout.splitlines()[-1])
    assert 'error' not in record, (
        'The rename Undo lifecycle must reach save and reload: ' + record.get('error', '')
    )
    assert not record['beforeCanUndo'], (
        'A newly loaded rename witness must begin without earlier Undo history'
    )
    if scenario == 'refusal':
        assert not record['renameCanUndo'], 'A refused collision must add no Undo step'
        assert record['nameRenamed'] == record['nameBefore'], (
            'A refused rename must retain its original datablock key'
        )
        assert record['renamed'] == record['before'], (
            'A refused rename must retain every reference'
        )
    else:
        assert record['renameCanUndo'], 'A successful datablock rename is one actual undoable edit'
        assert record['nameRenamed'] != record['nameBefore'], (
            'The literal rename actor must reach a different datablock key'
        )
        assert record['nameUndone'] == record['nameBefore'], 'Undo must reverse the rename itself'
        assert not record['undoCanUndo'], 'One rename Undo must exhaust its sole history step'
        assert record['afterReloadUndo'] == record['afterReloadBefore'], (
            'A rename after reload must have its own working inverse'
        )
    assert record['undone'] == record['before'], (
        'Literal rename Undo restores all aliases, both correlation endpoints and links/textures'
    )
    assert record['undoneTemplate'] == record['beforeTemplate'], (
        'Rename Undo restores the entire scan template reference state'
    )
    assert record['templateUndone'] == record['templateBefore'], (
        'Rename Undo restores the original template dataset designation'
    )
    assert record['undoReopened'] == record['before'], (
        'Saving and reopening the undone state must retain all original references'
    )
    assert record['undoReopenedTemplate'] == record['beforeTemplate'], (
        'Save/reload preserves the restored scan template references'
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_scan_keeps_all_live_matrices_but_persists_only_template_with_reload_explanation(
    native_probe, tmp_path, mode
):
    record = observe_correlations(native_probe, tmp_path, 'correlation-template', mode, False)
    for step in ('templateLive', 'templateReopened'):
        require_dataset_matrix(record[step], SCAN_REFERENCE['cases'][0])
    for step in ('otherLive', 'otherAfterSave'):
        require_dataset_matrix(record[step], SCAN_REFERENCE['cases'][1])
    require_core_file_pairs(record['savedPairs'], SCAN_REFERENCE['cases'][0])
    assert len(record['savedPairs']) == 3, 'A scan persists exactly its template dataset matrix'
    assert record['otherReopened']['available'] == 0, (
        'A reloaded non-template dataset must not display a persisted matrix'
    )
    reason = record['otherReopened']['emptyText'].lower()
    assert 'template' in reason, (
        'The reloaded non-template tab must explain the template-only persistence rule'
    )
    assert 'only' in reason, 'The empty-state explanation must identify the persistence limit'
