// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Components as EaComponents

// The one row type of every edi table (edi ADR-0017 §11): the base's ListViewDelegate, whose rows keep their
// alternating background, the current one too, with the list's accent marker on the current row and its number,
// a ListViewLabel with marksCurrentRow, bold in the accent colour.
EaComponents.ListViewDelegate {
    required property int index
}
