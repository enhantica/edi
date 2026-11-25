"""Read-only linked-structure wiring and actual display-binding execution."""

import hashlib
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.fixtures.native_process import native_executable, native_static_library
from tests.fixtures.table_display import gui_base
from tests.integration.py.test_scan_app_contract import (
    block,
    control_type,
    item,
    javascript,
    property_value,
)
from tests.integration.py.test_table_display import run_functions

ROOT = Path(__file__).resolve().parents[3]


def source(path):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', (ROOT / path).read_text(), flags=re.DOTALL)


def fraction_cell(text):
    name = 'linkedStructure.weightFraction.${row.index}'
    assert control_type(text, name) == 'DerivedCell', (
        'Linked structures must display the fraction through the shared derived cell'
    )
    return item(text, name)


def check_cell(cell, derived):
    for binding, role in (('fractionValue', 'value'), ('fractionError', 'uncertainty')):
        assert property_value(cell, binding) == f'known ? row.weightFraction.{role} : 0', (
            'The derived cell reads its own weight-fraction value and uncertainty roles'
        )
    assert property_value(cell, 'shownValue') == (
        'known ? Session.valueText("linked_structure.weight_fraction", fractionValue, '
        'fractionError) : ""'
    ), 'The table shows the common value-only presentation for the live fraction'
    assert (
        property_value(cell, 'fullValue') == 'known ? NumberText.plainFull(fractionValue) : ""'
    ), 'The popup receives the complete fraction independently of the fitted table text'
    assert (
        property_value(cell, 'uid') == '"linked_structure.weight_fraction"'
        and 'row.model.scale.fullName' in property_value(cell, 'derivedName')
        and property_value(cell, 'derivedName').endswith('+ "weight_fraction" : ""')
    ), 'The popup retains the saved linked-structure identity and dictionary UID'
    assert property_value(cell, 'uncertainty') == (
        'known ? Session.suText("linked_structure.weight_fraction", fractionValue, '
        'fractionError) : ""'
    ), 'The popup receives the separately formatted uncertainty'
    assert (
        property_value(derived, 'readOnly') == 'true'
        and re.search(r'(?m)^\s*property bool editable:\s*false\s*$', derived)
        and not re.search(r'(?m)^\s*(editable|onCommitted):', cell)
    ), 'The linked fraction grants neither inline editing nor popup writes'
    assert property_value(derived, 'menuValue') == 'fullValue !== "" ? fullValue : shownValue', (
        'The shared popup selects the full value whenever it is available'
    )
    assert 'shownValue !== ""' in property_value(derived, 'clickOpensMenu'), (
        'A known read-only fraction opens the shared popup and an empty fraction does not'
    )
    parameter = property_value(derived, 'parameter')
    assert all(
        f'"{field}": {value}' in parameter
        for field, value in {
            'value': 'cell.fittedValue',
            'error': 'cell.uncertainty',
            'fittable': 'true',
            'fit': 'false',
        }.items()
    ), 'The ordinary shared popup receives the separate s.u. and a clear Free box'
    free = block(derived, 'Binding {')
    editor = block(block(derived, 'editorComponent: Component {'), 'EaElements.TextField {')
    assert (
        property_value(free, 'target') == 'cell.fitCheckBox'
        and property_value(free, 'property') == '"enabled"'
        and property_value(free, 'value') == 'false'
        and property_value(editor, 'readOnly') == '!cell.editable'
    ), 'The real popup leaves Free disabled and its derived fraction value read-only'


def check_empty_cell_text(cell, derived):
    bindings = ''.join(
        f'const {name}=({property_value(cell, name)});'
        for name in (
            'known',
            'fractionValue',
            'fractionError',
            'shownValue',
            'fullValue',
            'uncertainty',
        )
    )
    observed = javascript(
        'const unexpected=()=>{throw Error("Missing fraction was formatted")};'
        'const Session={valueText:unexpected,suText:unexpected};'
        'const NumberText={plainFull:unexpected}; const editable=false;'
        'const result=[undefined,{}].map(weightFraction=>{const row={weightFraction};'
        + bindings
        + 'return [shownValue,fullValue,uncertainty,('
        + property_value(derived, 'clickOpensMenu')
        + ')];});console.log(JSON.stringify(result));'
    )
    assert observed == [['', '', '', False]] * 2, (
        'Unavailable and disabled empty fractions have no value, s.u., or active popup'
    )


def test_linked_structure_table_displays_weight_fraction_without_an_editor(fraction_bridge):
    text = source('app/qml/Pages/Experiment/LinkedStructureGroup.qml')
    assert re.search(r'HeaderLabel\s*\{[^}]*uid:\s*"linked_structure.weight_fraction"', text), (
        'Linked structures must display a weight fraction column'
    )
    cell = fraction_cell(text)
    derived = source('app/qml/Components/DerivedCell.qml')
    check_cell(cell, derived)
    check_empty_cell_text(cell, derived)
    broken = cell.replace(': ""', ': "missing"')
    assert broken != cell, 'The empty-value escape reaches the actual unknown-fraction binding'
    with pytest.raises(AssertionError):
        check_empty_cell_text(broken, derived)
    value = subprocess.check_output(
        [str(fraction_bridge), 'linked_structure.weight_fraction', '1', '0'], text=True
    )
    assert value == '1\t', 'The real dictionary bridge shows exact single-phase unity without s.u.'
    for old, new in (
        ('row.weightFraction.value', '0'),
        ('row.weightFraction.uncertainty', '0'),
        ('Session.valueText(', 'Session.suText('),
        ('NumberText.plainFull(fractionValue)', 'shownValue'),
    ):
        assert old in cell, 'The app escape must reach its real bound role or read-only flag'
        with pytest.raises(AssertionError):
            check_cell(cell.replace(old, new), derived)
    for old, new in (
        ('readOnly: true', 'readOnly: false'),
        ('"fit": false', '"fit": true'),
        ('value: false', 'value: true'),
    ):
        assert old in derived, 'Each escape reaches the shared popup or cell declaration'
        with pytest.raises(AssertionError):
            check_cell(cell, derived.replace(old, new, 1))


def check_fraction_routing(model):
    direct = re.search(
        r'static_cast<int>\(names.indexOf\(id\)\),\s*weight_fraction_cell\(\*link\)', model
    )
    fast_single = (
        re.search(
            r'if\s*\(enabled_links\s*>\s*1\)\s*\{\s*'
            r'return weight_fraction_cell\(link\);\s*\}',
            model,
        )
        and re.search(r'return QVariantMap\(\);\s*\};', model)
        and (
            re.search(
                r'if\s*\(link.enabled.get\(\)\)\s*\{\s*return QVariantMap\{\{'
                r'QStringLiteral\("value"\), 1.0\}',
                model,
            )
            and re.search(r'QStringLiteral\("uncertainty"\), 0.0', model)
            and re.search(r'static_cast<int>\(names.indexOf\(id\)\),\s*fraction\(\*link\)', model)
        )
    )
    assert direct or fast_single, (
        'Enabled rows supply their live fraction or exact single-phase unity without s.u.'
    )


def test_weight_fraction_role_and_menu_preserve_live_uncertainty_and_single_phase_unity(
    fraction_bridge,
):
    model = source('app/src/experiment_models.cpp')
    assert re.search(r'fraction\s*=\s*edi::weight_fraction\(link\)', model), (
        'The app role must obtain the live derived linked-structure result'
    )
    assert re.search(r'QStringLiteral\("value"\)\s*,\s*fraction->value', model), (
        'The weight-fraction role must carry the live derived value'
    )
    assert re.search(r'QStringLiteral\("uncertainty"\)\s*,\s*fraction->uncertainty', model), (
        'The weight-fraction role must carry the live derived uncertainty'
    )
    check_fraction_routing(model)
    value = subprocess.check_output(
        [str(fraction_bridge), 'linked_structure.weight_fraction', '0.375', '0.012'], text=True
    )
    assert value == '0.375\t0.012', (
        'The real bridge rounds a nontrivial fraction by IUCr and retains the separate uncertainty'
    )
    if 'fraction(*link)' in model:
        for old, new in (
            ('enabled_links > 1', 'enabled_links > 0'),
            ('link.enabled.get()', 'true'),
            ('QStringLiteral("value"), 1.0', 'QStringLiteral("value"), 0.5'),
            ('QStringLiteral("uncertainty"), 0.0', 'QStringLiteral("uncertainty"), 0.1'),
        ):
            assert old in model, 'Fraction routing escapes must reach their actual model branch'
            with pytest.raises(AssertionError):
                check_fraction_routing(model.replace(old, new))
    cmake = source('cmake/EdiGuiBase.cmake')
    components = cmake[cmake.index('edi_gui_base_module(edi_gui_components') :]
    assert re.search(r'\bListViewParameter\b', components.split('REPLACED')[0]), (
        'The weight-fraction menu ships from the pinned upstream ListViewParameter'
    )
    assert 'ListViewParameter' in components.split('REPLACED')[1].split(')')[0], (
        'The declared parameter overlay supplies the qualified-name link menu'
    )
    overlay = (ROOT / 'app/qml/Base/Gui/Components/ListViewParameter.qml').read_text()
    assert all(
        'parameter.' + role in property_value(overlay, role) for role in ('value', 'error')
    ), 'The shipped parameter overlay consumes the live value and separate uncertainty'
    assert 'control.openContextMenu(menuArea)' in overlay and 'control.fullName' in overlay, (
        'The actual parameter menu retains its context action and datablock-qualified name'
    )
    reference = ROOT / 'tests/fixtures/table_display/ListViewParameter.qml'
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == gui_base.PARAMETER_SHA256, (
        'The menu reference is the byte-exact upstream parameter cell at the pinned revision'
    )
    control = reference.read_text()
    assert 'control.openContextMenu(menuArea)' in control, (
        'The read-only parameter must retain its ordinary value context menu'
    )
    assert re.search(
        r'visible:\s*\(control.fittable\s*\|\|\s*control.readOnly\)\s*&&\s*control.error', control
    ), 'A read-only derived value must show its uncertainty in the context menu'
    assert re.search(r'text:\s*control.error\b', control), (
        'The parameter menu must display the separate uncertainty role'
    )
    assert re.search(r'visible:\s*control.fittable\s*&&\s*!control.readOnly', control), (
        'A read-only value must hide the menu free checkbox'
    )


@pytest.fixture(scope='module')
def fraction_bridge(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp('fraction-bridge')
    build = Path(sys.modules['edi._edi'].__file__).resolve().parents[2]
    cache = (build / 'CMakeCache.txt').read_text()
    sdk_match = re.search(r'^crysta_DIR:(?:PATH|UNINITIALIZED)=(.+)$', cache, re.MULTILINE)
    assert sdk_match, 'The actual consumer cache declares its SDK package directory'
    sdk = sdk_match[1]
    compiler = re.search(r'^CMAKE_CXX_COMPILER:FILEPATH=(.+)$', cache, re.MULTILINE)[1]
    core = native_static_library(build / 'core/libedi_core.a')
    assert core.is_file(), 'The display bridge must link the actual prepared native Edi core'
    output = tmp_path / 'build'
    commands = [
        [
            'cmake',
            '-S',
            str(ROOT / 'tests/fixtures/fraction_display_native'),
            '-B',
            str(output),
            '-G',
            'Ninja',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_CXX_COMPILER=' + compiler,
            '-Dcrysta_DIR=' + sdk,
            '-DEDI_INCLUDE=' + str(ROOT / 'core/include'),
            '-DEDI_CORE=' + str(core),
        ],
        ['cmake', '--build', str(output), '--config', 'Release', '--parallel', '2'],
    ]
    deadline = time.monotonic() + 20
    for command in commands:
        remaining = deadline - time.monotonic()
        assert remaining > 0, 'The native display bridge retains its original total build budget'
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=remaining
        )
        assert result.returncode == 0, (
            'The fraction witness links the actual consumer core and its declared SDK: '
            + result.stdout
            + result.stderr
        )
    native = native_executable(output / 'fraction')
    assert native.is_file(), 'The display bridge requires its real compiled native executable'
    return native


def test_single_fraction_cell_renders_unity_and_preserves_multiphase_formatting(fraction_bridge):
    actual = run_functions(
        ROOT / 'app/qml/Globals/NumberText.qml',
        [],
        [{'name': 'fraction', 'args': args} for args in ([1.0, 0], [0.375, 0.012], [None, 0])],
        consumer='fraction',
        bridge=str(fraction_bridge),
    )
    assert actual == [
        {'value': '1', 'error': ''},
        {'value': '0.375', 'error': '0.012'},
        {'value': '', 'error': ''},
    ], (
        'The real cell uses dictionary unity, IUCr value and separate s.u.; '
        'absent values stay empty'
    )
