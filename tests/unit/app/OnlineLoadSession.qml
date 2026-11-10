// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import ReportAcceptance 1.0

OnlineLoadCase {
    name: "OnlineLoadSession"
    required property url mailbox

    function test_dispatch() {
        console.info("ONLINE_READY");
        for (;;) {
            let request;
            tryVerify(() => {
                const file = SettingsProof.fileObservation(mailbox, "request");
                request = file.exists ? JSON.parse(file.text) : null;
                return request !== null;
            }, 45000, "The Python case sends a bounded request to the shared Qt host");
            verify(SettingsProof.remove(mailbox, "request"), "The host consumes each request once");
            if (request.case === "stop")
                return;

            let passed = false;
            try {
                const check = this["check_" + request.case];
                verify(typeof check === "function", "The requested case exists in the Qt host");
                if (request.tag) {
                    const data = this["check_" + request.case + "_data"]().find(row => row.tag === request.tag);
                    verify(data !== undefined, "The requested Qt data row exists");
                    check.call(this, data);
                } else {
                    check.call(this);
                }
                passed = true;
            } catch (error) {
                console.warn(String(error));
            } finally {
                cleanup();
            }
            console.info("ONLINE_RESULT " + JSON.stringify({id: request.id, passed}));
        }
    }
}
