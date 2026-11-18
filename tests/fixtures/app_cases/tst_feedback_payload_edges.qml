// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import "../../../app/feedback/Payload.js" as Payload

// The payload builder's edges: text that is not UTF-8, the whole log beside its preview.
TestCase {
    name: "FeedbackPayloadEdges"

    function base64Of(bytes) {
        return Payload.bytesBase64(bytes);
    }
    function textOf(file) {
        return Payload.utf8Text(Payload.base64Bytes(file.data));
    }

    function test_bytes_that_are_not_utf8_become_replacement_characters() {
        const cases = [[[0x61, 0xf4, 0xbf, 0xbf, 0xbf, 0x62], "past U+10FFFF"], [[0x61, 0xed, 0xa0, 0x80, 0x62], "a surrogate"], [[0x61, 0xe0, 0x80, 0xaf, 0x62], "an overlong form"], [[0x61, 0xe2, 0x82], "cut short at the end"]];
        for (const [bytes, what] of cases) {
            const payload = Payload.buildPayload("problem", "x", false, null, "", "", "", null, "", [
                {
                    "name": "a.txt",
                    "type": "text/plain",
                    "size": bytes.length,
                    "data": base64Of(bytes)
                }
            ]);
            const text = textOf(payload.attachments[0]);
            verify(text.startsWith("a�"), `${what}: ${JSON.stringify(text)}`);
            verify(text.indexOf("�") > 0, what);
        }
        compare(Payload.utf8Text([0xf0, 0x9f, 0x98, 0x80]), "\u{1F600}", "a valid four-byte character stays");
    }
    function test_a_cut_log_preview_goes_with_the_whole_log() {
        const log = "# app: 1\n" + "a line of the run\n".repeat(5000);
        const payload = Payload.buildPayload("problem", "x", true, {}, log, "", "", null, "", []);
        verify(payload.log.length <= Payload.maxLogCharacters, "the preview fits the body");
        compare(payload.fullLog, log, "the whole log beside it");
        verify(Payload.wireText(payload, true).indexOf("attached as log.txt") > 0, "the preview names it");
        verify(Payload.wireText(payload, true).length < log.length, "and does not show it twice");
        const short = Payload.buildPayload("problem", "x", true, {}, "# app: 1\nshort\n", "", "", null, "", []);
        compare(short.fullLog, undefined, "a log that fits needs no copy");
    }
    function test_a_201_without_the_whole_log_is_named() {
        verify(Payload.logUnconfirmed('{"number":7,"logAttached":false}'));
        verify(!Payload.logUnconfirmed('{"number":7}'));
    }
}
