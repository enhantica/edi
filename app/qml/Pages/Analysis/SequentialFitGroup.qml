// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// `sequential_fit`: the scan declaration of a scan mode (scanning is E05).
EaElements.GroupRow {
    id: row

    property AnalysisViewModel analysis: null
    readonly property SequentialFitViewModel fit: analysis ? analysis.sequentialFit : null

    ValueField {
        editable: false
        fieldValue: row.fit ? row.fit.dataDir : ""
        label: qsTr("data directory")
        objectName: "sequentialFit.dataDir"
    }
    ValueField {
        editable: false
        fieldValue: row.fit ? row.fit.filePattern : ""
        label: qsTr("files")
        objectName: "sequentialFit.filePattern"
    }
    ValueField {
        editable: false
        fieldValue: row.fit ? row.fit.reverse : ""
        label: qsTr("reverse")
        objectName: "sequentialFit.reverse"
    }
}
