"""Replay the rendered clipping observer against the shared table and its escape.

This checks the observer and shared table only; it is not a full app/SDK replay.
Copies the retained gui-components archive and the production ListView into an
isolated runner directory. No sibling checkout is consulted at test runtime.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QML = """import QtQuick
import QtTest
import EasyApplication.Gui.Components as Components
import "TableBoundary.js" as Boundary
Item {
    id: surface
    width: 900
    height: 800
    ListModel { id: rows }
    Components.ListView {
        id: table
        width: 600
        maxRowCountShow: 4
        model: rows
        columnWidths: [-1]
        header: Components.ListViewHeader {
            Text { text: "Value"; height: parent.height }
        }
        delegate: Components.ListViewDelegate {
            required property int index
            required property string label
            Text { text: label; height: parent.height }
        }
    }
    TestCase {
        id: test
        name: "SharedTableBoundaryReplay"
        when: windowShown
        function test_rendered_boundary() {
            for (let i = 0; i < 12; ++i) rows.append({label: "row " + i});
            verify(waitForPolish(table), "The shared production table completes real layout");
            table.forceLayout();
            const next = table.itemAtIndex(4);
            verify(next !== null, "The shared production table creates its actual next row");
            Boundary.check(test, table, next, surface);
        }
    }
}
"""


COLUMN_QML = """import QtQuick
import QtTest
import EasyApplication.Gui.Components as Components
import EasyApplication.Gui.Style as EaStyle
import "RenderedTable.js" as Render
Item {
    id: surface
    width: 900
    height: 800
    TextMetrics { id: ink }
    ListModel { id: rows }
    Components.ListView {
        id: table
        width: 600
        maxRowCountShow: 4
        model: rows
        columnWidths: @@WIDTHS@@
        header: Components.ListViewHeader {
            Components.TableViewLabel { text: "id" }
            Components.TableViewLabel { text: "type" }
            Components.TableViewLabel { text: "WL" }
            Components.TableViewLabel { text: "" }
        }
        delegate: Components.ListViewDelegate {
            required property int index
            required property string label
            Components.TableViewLabel { text: label }
            Components.TableViewLabel { text: "Si" }
            Components.TableViewLabel { text: "a" }
            Components.TableViewLabel {
                text: "minus-circle"
                font.family: EaStyle.Fonts.iconsFamily
            }
        }
    }
    TestCase {
        name: "SharedTableColumnReplay"
        when: windowShown
        @@HELPERS@@
        function test_fixed_column_fit() {
            rows.append({label: "phase"});
            verify(waitForPolish(table), "Supplied fixed cells complete shared table layout");
            table.forceLayout();
            const body = Render.cells(table.itemAtIndex(0));
            compare(body.length, 4, "The shared delegate contains every fixed cell");
            assertSuppliedTextFits(body[0], "phase", "id");
            assertSuppliedTextFits(body[1], "Si", "type");
            assertSuppliedTextFits(body[2], "a", "WL");
            assertCellInkFits(body[3]);
        }
    }
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-src', type=Path, required=True)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    for variant in (
        'production',
        'no-clipping',
        'columns-fit',
        'id-one-pixel',
        'type-one-pixel',
        'wyckoff-one-pixel',
        'action-one-pixel',
    ):
        directory = args.destination / variant
        directory.mkdir()
        imports = directory / 'imports'
        shutil.copytree(args.archive_src / 'src/EasyApplication', imports / 'EasyApplication')
        gui = imports / 'EasyApplication/Gui'
        for qmldir in gui.glob('*/qmldir'):
            text = qmldir.read_text()
            text = text.replace(
                'module ' + qmldir.parent.name,
                'module EasyApplication.Gui.' + qmldir.parent.name,
                1,
            )
            qmldir.write_text(text)
        subject = (ROOT / 'app/qml/Base/Gui/Components/ListView.qml').read_text()
        if variant == 'no-clipping':
            assert subject.count('    clip: true') == 1, (
                'Owner note 28 escape must alter the single actual shared clipping boundary'
            )
            subject = subject.replace('    clip: true', '    clip: false')
        (gui / 'Components/ListView.qml').write_text(subject)
        shutil.copyfile(ROOT / 'tests/unit/app/TableBoundary.js', directory / 'TableBoundary.js')
        if variant in {'production', 'no-clipping'}:
            qml = QML
        else:
            gates = (ROOT / 'tests/unit/app/tst_table_geometry.qml').read_text()
            start = gates.index('        function assertCellInkFits(')
            end = gates.index('        function test_actual_column_geometry_data()', start)
            helpers = gates[start:end]
            widths = [90, 90, 90, 90]
            for index, name in enumerate(('id', 'type', 'wyckoff', 'action')):
                if variant == name + '-one-pixel':
                    widths[index] = 1
            qml = COLUMN_QML.replace('@@HELPERS@@', helpers).replace('@@WIDTHS@@', str(widths))
            shutil.copyfile(
                ROOT / 'tests/unit/app/RenderedTable.js', directory / 'RenderedTable.js'
            )
        (directory / 'tst_boundary.qml').write_text(qml)
        environment = {
            **os.environ,
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'QML2_IMPORT_PATH': str(imports),
            'QML_IMPORT_PATH': str(imports),
            'CI': 'true',
            'GITHUB_ACTIONS': 'true',
            'GITHUB_WORKSPACE': str(directory),
            'GITHUB_EVENT_NAME': 'pull_request',
        }
        result = subprocess.run(
            [str(args.runner), '-input', str(directory / 'tst_boundary.qml')],
            cwd=directory,
            env=environment,
            text=True,
            capture_output=True,
            timeout=25,
            check=False,
        )
        (args.destination / (variant + '.log')).write_text(result.stdout + result.stderr)
        if variant in {'production', 'columns-fit'}:
            assert result.returncode == 0, (
                'Owner note 28 shared table control must pass its boundary and pixel calibration'
            )
        elif variant == 'no-clipping':
            assert (
                result.returncode != 0
                and 'effective ancestor clip at the half-row boundary' in result.stdout
            ), 'Owner note 28 no-clipping escape must reach the effective boundary refusal'
        else:
            assert result.returncode != 0 and (
                'fits both its independently supplied content and heading' in result.stdout
                or 'viewport fits its independently measured ink' in result.stdout
            ), 'Owner compact-column escapes must reach the supplied text or glyph fit refusal'
        print(f'{variant}: exit {result.returncode}; {args.destination / (variant + ".log")}')


if __name__ == '__main__':
    main()
