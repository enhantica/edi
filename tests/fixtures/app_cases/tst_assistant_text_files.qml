// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// A text file that is not UTF-8 can be attached to the assistant and read, its encoding named; a binary one cannot
// (edi ADR-0055).
TestCase {
    id: test

    name: "AssistantTextFiles"
    when: windowShown

    readonly property AssistantViewModel assistant: Session.assistant

    function attach(name) {
        const before = assistant.selectedFiles.count;
        const token = assistant.beginFileSelection();
        verify(token !== "", assistant.lastError);
        verify(assistant.addSelectedFiles(token, [Qt.resolvedUrl("assistant_files/" + name)]), assistant.lastError);
        tryCompare(assistant.selectedFiles, "count", before + 1, 10000);
        return before;
    }
    function cleanup() {
        while (assistant.selectedFiles.count > 0)
            verify(assistant.removeSelectedFile(assistant.selectedFiles.text(0, "id")), assistant.lastError);
    }

    function test_a_utf8() {
        compare(assistant.selectedFiles.text(attach("utf8.cif"), "format"), "unverified_text");
    }
    function test_b_windows_1252() {
        const row = attach("latin1.cif");
        compare(assistant.selectedFiles.text(row, "format"), "unverified_text_windows_1252");
        compare(assistant.selectedFiles.text(row, "textReadable"), "true");
    }
    function test_c_binary() {
        const row = attach("binary.cif");
        compare(assistant.selectedFiles.text(row, "format"), "unsupported_binary");
        compare(assistant.selectedFiles.text(row, "textReadable"), "false");
    }
}
