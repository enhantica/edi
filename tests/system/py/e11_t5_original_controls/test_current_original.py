"""Fresh same-kit Composer/browser cases and immutable original-source protocols.

The explicit usage phase and final caller/source/binary identities are bound by root.
Original125 and original87 remain historical custody, never this new build identity.
"""

import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from contextlib import ExitStack
from pathlib import Path

import pytest

from . import original_profile


def _absolute(value):
    path = Path(value)
    assert path.is_absolute(), 'Recording inputs require explicit absolute source bindings'
    return path.resolve(strict=True)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_inputs():
    root = _absolute(os.environ['EDI_E11_ORIGINAL_SOURCE_ROOT'])
    frozen = Path(__file__).with_name('original_cases.py').resolve(strict=True)
    binding = json.loads(Path(__file__).with_name('source_binding.json').read_text())
    assert binding['binding_status'] == 'BOUND', 'Final source/binary inputs must be bound by root'
    assert binding['caller_binding_status'] == 'BOUND', (
        'Both fresh caller maps require source proof'
    )
    assert os.environ['EDI_E11_T5_A2A_PHASE'] == 'native', 'Activity header07 stays native'
    assert os.environ['EDI_E11_COMPOSER_BROWSER_PHASE'] == binding['phase']
    assert binding['phase'] in {
        'native-complete-final',
        'native-composer-browser-original-usage',
    }, 'An explicit fresh comparison phase is mandatory'
    expected_usage = 'native' if binding['phase'] == 'native-complete-final' else 'original'
    families = {
        'activity': 'native',
        'composer': 'native',
        'browser': 'native',
        'usage': expected_usage,
    }
    assert binding['family_phases'] == families
    assert _sha(frozen) == binding['frozen266_sha256']
    active_path = Path(__file__).with_name('native_cases.py').resolve(strict=True)
    assert _sha(active_path) == binding['active_native_cases_sha256']
    for row in binding['required_files'] + binding['production_files']:
        assert _sha(root / row['path']) == row['sha256'], row['path']
    receipt_path = _absolute(os.environ['EDI_E11_POST_BINARY_BOND'])
    expected = os.environ['EDI_E11_POST_BINARY_BOND_SHA256']
    assert len(expected) == 64 and all(character in '0123456789abcdef' for character in expected)
    assert expected == binding['current_bond_sha256']
    assert _sha(receipt_path) == expected
    receipt = json.loads(receipt_path.read_text())
    assert receipt['source'] == os.environ['EDI_E11_POST_SOURCE_SHA'] == binding['current_source']
    assert receipt['family_phases'] == families
    original_path = _absolute(os.environ['EDI_E11_COMPARISON_ORIGINAL_BINARY_BOND'])
    assert _sha(original_path) == binding['original_bond_sha256']
    original = json.loads(original_path.read_text())
    assert original['source'] == binding['original_source']
    assert original['family_phases'] == {**families, 'usage': 'original'}
    for name, value in binding['comparison_native'].items():
        assert receipt['native'][name] == value, name
        assert original['native'][name] == value, name
    for bond in (receipt, original):
        assert (
            _sha(_absolute(bond['native']['archive']))
            == binding['comparison_native']['archive_sha256']
        )
    assert receipt['bundled_runtime']['config_sha256'] == binding['current_runtime_config_sha256']
    assert (
        original['bundled_runtime']['config_sha256'] == binding['original_runtime_config_sha256']
    )
    for bond, key in (
        (receipt, 'current_runtime_config_sha256'),
        (original, 'original_runtime_config_sha256'),
    ):
        assert _sha(_absolute(bond['bundled_runtime']['config'])) == binding[key]
    for key, expected_hash in binding['compiled_caller_proof'].items():
        observed = receipt['generated_inputs'][key]
        assert observed['sha256'] == expected_hash, key
        assert _sha(_absolute(observed['path'])) == expected_hash, key
    assert receipt['selected_header_sha256'] == (
        '07cddf1a8fa777efac7c92a5133c3a1f659a2a5966495ef30d538b1905d946fe'
    )
    for row in binding['production_files']:
        if row['compiled']:
            assert receipt['compiled_sources'][row['path']] == row['sha256'], row['path']
    assert receipt['compiled_sources']['tests/integration/py/assistant_ui_probe/probe.cpp'] == (
        '1e5d1156dc1704dcb3e3b823427881d02a0964971b72de5875a0fe42f8bcde75'
    )
    assert (
        _sha(_absolute(os.environ['EDI_ASSISTANT_UI_PROBE']))
        == receipt['binaries']['assistant_real_owner_probe']['sha256']
    )
    historical87 = _absolute(os.environ['EDI_E11_ORIGINAL_BINARY_BOND'])
    assert _sha(historical87) == (
        '317201f07568bcdec51f93294b41554d9db7560c8ffe2739534a5868d7b1db5d'
    ), 'Original87 remains immutable protocol custody, never the fresh kit authority'
    if expected_usage == 'original':
        assert receipt == original
    _require_stable_dependencies(receipt, original)
    return root, frozen


def _require_stable_dependencies(receipt, original):
    for section, keys in {
        'compiler_kit': ['compiler_sha256', 'package_metadata'],
        'dependency_environment': ['root_lock_sha256', 'dependency_only_lock_sha256'],
        'gui_components': ['commit', 'pin_file_sha256', 'source_sha256'],
        'bundled_runtime': ['files'],
    }.items():
        for key in keys:
            assert receipt[section][key] == original[section][key], (section, key)


def _load_bound_module(name, path):
    path = _absolute(path)
    if name in sys.modules:
        existing = sys.modules[name]
        assert _absolute(existing.__file__) == path, 'No same-name module from another checkout'
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    with ExitStack() as rollback:
        sys.modules[name] = module
        rollback.callback(sys.modules.pop, name, None)
        spec.loader.exec_module(module)
        rollback.pop_all()
    return module


SOURCE_ROOT, FROZEN_PATH = _source_inputs()
ACTUAL = _load_bound_module(
    'test_e11_t5_dev_native_integration',
    SOURCE_ROOT / 'tests/system/py/test_e11_t5_dev_native_integration.py',
)
ERRORS = _load_bound_module(
    'e11_t5_original_qml_error_contract',
    SOURCE_ROOT / 'tests/system/py/e11_t5_original_qml_error_contract.py',
)
FROZEN = _load_bound_module('e11_original_frozen245', FROZEN_PATH)
ACTIVE_PATH = Path(__file__).with_name('native_cases.py').resolve(strict=True)
ACTIVE_CASES = _load_bound_module('e11_native256_cases', ACTIVE_PATH)
# Register the actual unchanged fixture object, preserving its strict teardown.
main_actor = ACTUAL.main_actor
REGISTRY = json.loads(Path(__file__).with_name('case_registry.json').read_text())
ACTIVE_REGISTRY = json.loads(Path(__file__).with_name('native_case_registry.json').read_text())


def elected_case(function_name, arguments):
    matches = [
        value
        for value in REGISTRY.values()
        if value['function'] == function_name and value['arguments'] == arguments
    ]
    assert len(matches) == 1, 'Missing, ambiguous or cross-case contracts remain unqualified'
    case = matches[0]
    path = Path(__file__).parent / case['contract']
    assert _sha(path) == case['contract_sha256'], 'The elected exact contract is immutable'
    return case, json.loads(path.read_text())


def active_elected_case(function_name, arguments):
    matches = [
        value
        for value in ACTIVE_REGISTRY.values()
        if value['function'] == function_name and value['arguments'] == arguments
    ]
    assert len(matches) == 1, 'Missing, ambiguous or cross-case contracts remain unqualified'
    case = matches[0]
    path = Path(__file__).parent / case['contract']
    assert _sha(path) == case['contract_sha256'], 'The elected exact contract is immutable'
    return case, json.loads(path.read_text())


ORDINARY = [
    pytest.param(
        'test_original_restore_keeps_only_actual_newer_input_and_publishes_current_text',
        {'input_transition': 'unchanged'},
        id='restore_unchanged',
    ),
    pytest.param(
        'test_original_restore_keeps_only_actual_newer_input_and_publishes_current_text',
        {'input_transition': 'preedit_cancel'},
        id='restore_preedit_cancel',
    ),
    pytest.param(
        'test_original_restore_keeps_only_actual_newer_input_and_publishes_current_text',
        {'input_transition': 'ime_commit'},
        id='restore_ime_commit',
    ),
    pytest.param(
        'test_original_restore_keeps_only_actual_newer_input_and_publishes_current_text',
        {'input_transition': 'preedit_active'},
        id='restore_preedit_active',
    ),
    pytest.param(
        'test_original_composer_clear_preserves_active_ime_then_clears_settled_capture',
        {},
        id='composer_ime_clear',
    ),
]
RECORDING = [
    pytest.param(
        'test_original_browser_opens_before_late_current_owner_refresh', {}, id='browser_open'
    ),
    pytest.param(
        'test_original_browser_row_activation_precedes_current_owner_selection',
        {'activation_effect': 'restore_owner'},
        id='browser_restore_owner',
    ),
    pytest.param(
        'test_original_browser_row_activation_precedes_current_owner_selection',
        {'activation_effect': 'retire_account'},
        id='browser_retire_account',
    ),
    pytest.param(
        'test_original_browser_row_activation_precedes_current_owner_selection',
        {'activation_effect': 'leave_null'},
        id='browser_leave_null',
    ),
    pytest.param(
        'test_original_browser_footer_dependencies_remain_live_with_null_view_owner',
        {},
        id='browser_footer',
    ),
    pytest.param(
        'test_original_composer_revision_effects_precede_null_owner_text_publication',
        {},
        id='composer_null_publication',
    ),
]


class CommandScopes:
    """Observe source-site ranges while delegating the exact original bound method."""

    def __init__(self, actor, owner, function_name, case):
        self.actor = actor
        self.owner = owner
        self.function_name = function_name
        self.case = case
        self.contract_steps = {row['step'] for row in owner.contract['expected']}
        self.original = actor.command
        assert self.original.__self__ is actor
        assert self.original.__func__ is ACTUAL.MainActor.command
        self.depth = 0
        self.occurrences = Counter()

    def source_site(self):
        frame = sys._getframe(1)
        try:
            while frame:
                code = frame.f_code
                if code.co_filename == str(ACTIVE_PATH) and code.co_name == self.function_name:
                    return frame.f_lineno
                frame = frame.f_back
        finally:
            del frame
        raise AssertionError('Original command lacks its declared immutable245 caller')

    def __call__(self, operation, **arguments):
        if self.depth or self.owner._finished:
            return self.original(operation, **arguments)
        site = (self.source_site(), operation)
        self.occurrences[site] += 1
        label = ':'.join((
            self.function_name,
            str(site[0]),
            operation,
            str(self.occurrences[site]),
        ))
        if label in self.contract_steps:
            self.retain_and_require_profile(label)
        self.depth += 1
        try:
            return self.owner.step(label, lambda _actor: self.original(operation, **arguments))
        finally:
            self.depth -= 1

    def retain_and_require_profile(self, label):
        folder = self.actor.folder
        peer = json.loads((folder / 'peer.json').read_text())
        requests = [json.loads(line) for line in (folder / 'wire.jsonl').read_text().splitlines()]
        responses = [
            json.loads(line) for line in (folder / 'wire.sent.jsonl').read_text().splitlines()
        ]
        facts = {
            'step': label,
            'case': self.case,
            'last': self.actor.last,
            'peer': peer,
            'requests': requests,
            'responses': responses,
        }
        path = folder / ('original-profile-before-' + str(self.actor._command_sequence) + '.json')
        path.write_text(json.dumps(facts, indent=2))
        original_profile.require_peer(peer, self.case, folder, ACTUAL.FINAL)
        original_profile.require_census(self.actor.last['ui'], self.case)
        original_profile.require_model_wire(requests, responses)


def _recording_factory(stack, tmp_path, function_name, arguments):
    owners = []
    case, contract = active_elected_case(function_name, arguments)

    def create(turns, *, show_actions=False, hold_final=False):
        binary = _absolute(os.environ['EDI_ASSISTANT_UI_PROBE'])
        assert binary.is_file(), 'Use the exact normally built current Main/native observer'
        folder = tmp_path / ('intentional-actor-' + str(len(owners)))
        folder.mkdir()
        config = {'turns': turns}
        if hold_final:
            config['final_gate'] = str(folder / 'release-final')
        # This is the actual existing class/constructor, once. Install ownership
        # before initialization so constructor failure also reaches guarded258.
        initialize = ACTUAL.MainActor.__init__
        actor = ACTUAL.MainActor.__new__(ACTUAL.MainActor)
        actor._command_sequence = 0  # same original getattr(..., 0) starting state
        owner = ERRORS.IntentionalQmlHost(actor, contract=contract, recording_original=False)
        stack.enter_context(owner)
        owners.append(owner)
        actor.command = CommandScopes(actor, owner, function_name, case)
        initialize(actor, binary, folder, config, show_actions)
        return actor

    return create, owners


@pytest.mark.parametrize(('function_name', 'arguments'), ORDINARY)
def test_current_original_ordinary(function_name, arguments, main_actor):
    getattr(ACTIVE_CASES, function_name)(main_actor, **arguments)


@pytest.mark.parametrize(('function_name', 'arguments'), RECORDING)
def test_current_original_recording(function_name, arguments, tmp_path):
    with ExitStack() as stack:
        create, owners = _recording_factory(stack, tmp_path, function_name, arguments)
        getattr(ACTIVE_CASES, function_name)(create, **arguments)
        assert owners, 'A recording case must really own its original Main host'
