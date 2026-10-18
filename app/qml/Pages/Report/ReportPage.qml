// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Report page (edi ADR-0036; the owner's notes 30 and 31, and the sidebar of 2026-10-13): the report's live preview
// in the main area, drawn from the report model; the sidebar's Export and Contents; reports/report.edi in Text.
WorkflowPage {
    id: page

    readonly property ProjectViewModel project: Session.project
    readonly property ReportViewModel report: project ? project.report : null
    // Export's save that waits for the project's calculation to end.
    property bool savePending: false

    pageName: "report"
    defaultInfo: project ? "" : qsTr("No report generated")
    mainTabs: [
        IconTabButton {
            objectName: "mainArea.report.tab.report"
            // The view's name, text only (edi ADR-0017 §2).
            text: qsTr("Report")
        }
    ]
    mainItems: [
        ReportPreview {
            id: reportPreview
            objectName: "report.preview"
            report: page.report
            // Drawn while the page is shown, and while a save waits for a calculation: a PDF takes its figures.
            drawn: page.current || page.savePending
        }
    ]
    textEnabled: project !== null
    basicItem: Component {
        EaComponents.SideBarColumn {
            ExportGroup {
                report: page.report
                preview: reportPreview
                shown: page.current
                onSavePendingChanged: page.savePending = savePending
            }
            ContentsGroup {
                report: page.report
                shown: page.current
            }
        }
    }
    textItem: Component {
        TextTab {
            source: page.project ? page.project.reportText : null
            underContinue: false
        }
    }
    continueVisible: false

    // The report's charts take the app's colour scheme.
    Binding {
        target: page.report
        property: "colourScheme"
        value: Preferences.colourScheme
        when: page.report !== null
    }

    // The report rebuilds at once only while this page is shown.
    Binding {
        target: page.report
        property: "active"
        value: page.current
        when: page.report !== null
    }
}
