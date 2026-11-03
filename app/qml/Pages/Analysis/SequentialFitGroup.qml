// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// `sequential_fit`: the scan declaration of a scan mode (scanning is E05).
EaElements.GroupRow {
    id: row
    spacing: AppSizes.inputSpacing

    property AnalysisViewModel analysis: null
    readonly property SequentialFitViewModel fit: analysis ? analysis.sequentialFit : null

    ValueField {
        objectName: "sequentialFit.dataDir"
        editable: false
        uid: "sequential_fit.data_dir"
        fieldValue: row.fit ? row.fit.dataDir : ""
    }
    ValueField {
        objectName: "sequentialFit.filePattern"
        editable: false
        uid: "sequential_fit.file_pattern"
        fieldValue: row.fit ? row.fit.filePattern : ""
    }
    ValueField {
        objectName: "sequentialFit.reverse"
        editable: false
        uid: "sequential_fit.reverse"
        fieldValue: row.fit ? row.fit.reverse : ""
    }
}
