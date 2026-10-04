// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

// The check a numeric field applies to typed text before anything reaches the model: `Number()`
// reads text that is not a number as NaN and an empty text as 0, and an integer property drops a
// fraction, so each would be written as a value the user never typed.
QtObject {
    // Why `text` is refused as a value of the kind `accepts` ("text", "number" or "integer"), or ""
    // when it is one. Text is never refused here; the core's rules refuse it once committed.
    function refusal(text: string, accepts: string): string {
        if (accepts === "text")
            return "";
        const number = text.trim() === "" ? NaN : Number(text);
        if (!isFinite(number))
            return qsTr("'%1' is not a number").arg(text);
        if (accepts === "integer" && !Number.isInteger(number))
            return qsTr("'%1' is not a whole number").arg(text);
        return "";
    }
}
