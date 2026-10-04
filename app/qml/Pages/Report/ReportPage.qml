// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Report page (easydiffractionbeta Pages/Summary): the report as Qt rich text in a read-only text
// area — project information, crystal data, data collection, the fit; Export summary disabled until
// the report task; every project file in Text.
WorkflowPage {
    id: page

    readonly property ProjectViewModel project: Session.project

    pageName: "report"
    defaultInfo: project ? "" : qsTr("No summary generated")
    mainTabs: [
        EaElements.TabButton {
            objectName: "mainArea.report.tab.summary"
            text: qsTr("Summary")
        }
    ]
    mainItems: [
        Flickable {
            contentHeight: reportText.implicitHeight
            clip: true
            ScrollBar.vertical: EaElements.ScrollBar {
                policy: ScrollBar.AsNeeded
                interactive: false
            }

            EaElements.TextArea {
                id: reportText
                objectName: "report.text"
                width: parent.width
                padding: AppSizes.reportPadding
                readOnly: true
                textFormat: TextEdit.RichText
                wrapMode: TextEdit.Wrap
                text: page.project ? page.project.report.richText : ""
            }
        }
    ]
    textEnabled: project !== null
    basicItem: Component {
        EaComponents.SideBarColumn {
            ExportSummaryGroup {}
        }
    }
    textItem: Component {
        TextTab {
            source: page.project ? page.project.projectText : null
            underContinue: false
        }
    }
    continueVisible: false
}
