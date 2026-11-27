// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// The fit results' agreement factors show whole, a single crystal's "undefined" too (D1).
Item {
    id: root

    width: 1400
    height: 900

    FitResultsDialog {
        id: dialog

        parent: root
    }

    TestCase {
        name: "FitResultsValues"
        when: windowShown

        function cleanup() {
            dialog.close();
            tryVerify(() => !dialog.visible);
            Session.closeProject();
        }
        function cells(item, found) {
            for (const child of item.children) {
                if (child.objectName.startsWith("fit.results.agreement.value."))
                    found.push(child);
                cells(child, found);
            }
            return found;
        }
        function test_every_value_shows_whole() {
            verify(Session.openProject(Qt.resolvedUrl("../../../docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_basic/project")), Session.lastError);
            const fit = Session.project.fit;
            tryVerify(() => fit.available, 30000);
            fit.start();
            tryVerify(() => !fit.running && fit.results.agreement !== null && fit.results.agreement.count > 0, 60000);
            dialog.open();
            tryVerify(() => dialog.opened);
            tryVerify(() => cells(dialog.contentItem, []).length > 2);
            const shown = cells(dialog.contentItem, []);
            verify(shown.some(cell => cell.number === "undefined"), shown.map(cell => cell.number).join(" "));
            for (const cell of shown) {
                compare(cell.text, cell.number);
                verify(!cell.truncated && cell.implicitWidth <= cell.width + 0.5, `${cell.number}: ${cell.implicitWidth} px in ${cell.width} px`);
            }
        }
    }
}
