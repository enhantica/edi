"""Observe settled Beta rows and exercise every column of the alignment gate.

Only the pinned external table and cell sources supply the reference layout.
The subject application's QML supplies the assertion observer, not the oracle.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BETA = 'ec1d04ee36036dd092fdd8b779e99767afca6e5d'
COMPONENTS = 'a573a9695e53a0807de197785e12f9facd06da05'
BEFORE = '215d5fa80d7e41b3cd759056f9fb21c5226922aa'
GATE = 'tests/unit/app/tst_table_owner_behaviours.qml'
BETA_FILE = 'easyDiffractionApp/Gui/Components/Pages/Analysis/SideBarBasic/Fittables.qml'
ASSIGNMENT = (
    'rowElement.children[columnIndex].horizontalAlignment = '
    'headerLabelItems[columnIndex].horizontalAlignment'
)

PROXIES = """pragma Singleton
import QtQuick
QtObject {
    property var main_fittables_data: [
        {value: 4.7, error: 0.1, min: 0, max: 10, fit: true, units: "Å"},
        {value: 8.1, error: 0.2, min: 1, max: 20, fit: false, units: "Å"}
    ]
    property var main: ({fitting: {isFittingNow: false}, experiment: {defined: true},
        backendHelpers: {toStdDevSmalestPrecision: function(value, error) {
            return {value: String(value), std_dev: String(error)};
        }}})
    function paramName(item, format) { return "Supplied parameter"; }
}
"""

HARNESS = """import QtQuick
import QtQuick.Controls
import QtTest
import EasyApplication.Gui.Logic as EaLogic
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents
import Gui.Globals as Globals
Item {
    id: surface
    width: 900
    height: 800
    property int selectedParamIndex: -1
    property var initialRows: []
    property var applicationWindow: ({height: 800})
    QtObject { id: slider; property real value: 0 }
    function updateSliderLimits() {}
    function updateSliderValue() {}
    @@TABLE@@
    TestCase {
        name: "BetaAlignmentReference"
        when: windowShown
        @@OBSERVER@@
        function test_settled_reference() {
            const headerAlignments = @@HEADER@@;
            const delegateAlignments = @@DELEGATE@@;
            tryCompare(tableView, "count", 2, 2000,
                "The pinned Beta table instantiates both independently supplied rows");
            tableView.forceLayout();
            verify(waitForPolish(tableView), "The pinned Beta table completes actual layout");
            tryVerify(() => surface.initialRows.length === 2, 2000,
                "Both Beta delegates record their initial state before the timer assignment");
            tryCompare(tableView, "referenceTimerCompleted", true, 2000,
                "The Beta timer finishes before any settled-row alignment is observed");
            const headers = tableView.headerItem.children[0].children;
            compare(headers.length, 8, "Beta retains all eight Analysis headers");
            for (let j = 0; j < 8; ++j)
                compare(headers[j].horizontalAlignment, headerAlignments[j],
                    "The external Beta header agrees with the independent direction vector");
            for (const initial of surface.initialRows)
                compare(initial, Array(8).fill(Text.AlignHCenter),
                    "Beta cells start centered before their table assigns alignment");
            for (let i = 0; i < 2; ++i) {
                const row = tableView.itemAtIndex(i);
                verify(row !== null, "The Beta reference exposes each actual rendered delegate");
                assertBetaDelegateAlignment(row.children[0].children, delegateAlignments);
            }
            console.info("BETA_ALIGNMENT=" + JSON.stringify({
                initial: surface.initialRows,
                header: Array.from(headers, cell => cell.horizontalAlignment),
                settled: [0, 1].map(i => Array.from(tableView.itemAtIndex(i).children[0].children,
                    cell => cell.horizontalAlignment))
            }));
        }
    }
}
"""


def git_show(repo: Path, revision: str, path: str) -> str:
    return subprocess.run(
        ['git', '-C', str(repo), 'show', f'{revision}:{path}'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def vector(source: str, name: str) -> str:
    match = re.search(rf'const {name} = (\[[^;]+\]);', source)
    if match is None:
        raise ValueError(f'Beta alignment replay requires the declared {name} vector')
    return match[1]


def reference_inputs(args):
    beta = git_show(args.beta_repo, BETA, BETA_FILE)
    table = beta.split('    // Table\n')[1]
    # Record actual declaration defaults before the reference's asynchronous timer.
    table = table.replace(
        'delegate: EaComponents.TableViewDelegate {',
        """delegate: EaComponents.TableViewDelegate {
            Component.onCompleted: surface.initialRows.push(
                Array.from(children[0].children, cell => cell.horizontalAlignment))
""",
        1,
    )
    gate = (ROOT / GATE).read_text()
    start = gate.index('    function assertBetaDelegateAlignment(')
    end = gate.index('    function test_analysis_alignment_units_and_available_height()', start)
    observer = gate[start:end]
    old_gate = git_show(ROOT, BEFORE, GATE)
    archive = subprocess.run(
        ['git', '-C', str(args.components_repo), 'archive', COMPONENTS, 'src/EasyApplication'],
        check=True,
        capture_output=True,
    ).stdout
    return {
        'table': table,
        'observer': observer,
        'gate': gate,
        'old_gate': old_gate,
        'archive': archive,
    }


def prepare_imports(archive, directory, variant):
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(directory, filter='data')
    imports = directory / 'src'
    gui = imports / 'EasyApplication/Gui'
    for qmldir in gui.glob('*/qmldir'):
        qmldir.write_text(
            qmldir.read_text().replace(
                'module ' + qmldir.parent.name,
                'module EasyApplication.Gui.' + qmldir.parent.name,
                1,
            )
        )
    subject = gui / 'Components/TableView.qml'
    source = subject.read_text()
    assert source.count(ASSIGNMENT) == 1, (
        'Note 26 reference replay must reach the unique actual delegate assignment'
    )
    trigger = 'onTriggered: setAllColumnsWidthAndAlignment()'
    assert source.count(trigger) == 1, (
        'Note 26 timer receipt must observe the unique post-creation assignment trigger'
    )
    source = source.replace(
        'id: listView', 'id: listView\n    property bool referenceTimerCompleted: false', 1
    )
    assignment = '' if variant == 'no-timer' else 'setAllColumnsWidthAndAlignment();'
    source = source.replace(
        trigger, 'onTriggered: { ' + assignment + ' referenceTimerCompleted = true; }'
    )
    if variant.startswith('column-'):
        index = int(variant.removeprefix('column-'))
        source = source.replace(
            ASSIGNMENT,
            ASSIGNMENT
            + (
                f'\n                                if (Number(columnIndex) === {index}) '
                'rowElement.children[columnIndex].horizontalAlignment = '
                'headerLabelItems[columnIndex].horizontalAlignment === Text.AlignHCenter '
                '? Text.AlignLeft : Text.AlignHCenter'
            ),
        )
    subject.write_text(source)
    globals_dir = imports / 'Gui/Globals'
    globals_dir.mkdir(parents=True)
    (globals_dir / 'qmldir').write_text('module Gui.Globals\nsingleton Proxies 1.0 Proxies.qml\n')
    (globals_dir / 'Proxies.qml').write_text(PROXIES)
    return imports


def run_variant(args, inputs, variant):
    directory = args.destination / variant
    directory.mkdir()
    imports = prepare_imports(inputs['archive'], directory, variant)
    qml = HARNESS.replace('@@TABLE@@', inputs['table']).replace('@@OBSERVER@@', inputs['observer'])
    qml = qml.replace('@@HEADER@@', vector(inputs['gate'], 'headerAlignments'))
    qml = qml.replace(
        '@@DELEGATE@@',
        vector(
            inputs['old_gate'] if variant == 'old-oracle' else inputs['gate'], 'delegateAlignments'
        ),
    )
    (directory / 'tst_alignment.qml').write_text(qml)
    environment = {
        **os.environ,
        'QT_QPA_PLATFORM': 'offscreen',
        'QT_QUICK_BACKEND': 'software',
        'QML_IMPORT_PATH': str(imports),
        'QML2_IMPORT_PATH': str(imports),
        'CI': 'true',
        'GITHUB_ACTIONS': 'true',
        'GITHUB_WORKSPACE': str(directory),
        'GITHUB_EVENT_NAME': 'pull_request',
    }
    result = subprocess.run(
        [str(args.runner), '-input', str(directory / 'tst_alignment.qml')],
        cwd=directory,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=25,
    )
    output = result.stdout + result.stderr
    (args.destination / f'{variant}.log').write_text(output)
    if variant == 'reference':
        assert result.returncode == 0, (
            'Note 26 independent settled Beta rows must pass the corrected alignment oracle'
        )
        match = re.search(r'BETA_ALIGNMENT=(\{[^\n]+\})', output)
        assert match is not None, (
            'Note 26 reference receipt must record initial, header and settled row vectors'
        )
        return {'exit': result.returncode, 'observed': json.loads(match[1])}
    index = int(variant.removeprefix('column-')) if variant.startswith('column-') else 1
    assert result.returncode != 0 and (
        'The rendered Analysis column follows the settled Beta alignment reference: ' + str(index)
        in output
    ), 'Note 26 every alignment escape must reach its intended rendered-column refusal'
    return {'exit': result.returncode}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--beta-repo', type=Path, required=True)
    parser.add_argument('--components-repo', type=Path, required=True)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    inputs = reference_inputs(args)
    receipts = {}
    for variant in ['reference', 'old-oracle', 'no-timer', *[f'column-{i}' for i in range(8)]]:
        receipts[variant] = run_variant(args, inputs, variant)
        print(
            f'{variant}: {receipts[variant]}; {args.destination / (variant + ".log")}', flush=True
        )
    (args.destination / 'receipt.json').write_text(
        json.dumps(
            {
                'beta': BETA,
                'components': COMPONENTS,
                'old_oracle': BEFORE,
                **receipts,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
