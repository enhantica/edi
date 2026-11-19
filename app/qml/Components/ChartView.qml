// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtGraphs
import edi.app

// Every chart uses edi's pointer layers. Never enter Qt Graphs' native hover
// renderer, which can retain a removed series until a later render (ADR-0044).
GraphsView {
    id: graph

    ChartHoverGuard {
        view: graph
    }
}
