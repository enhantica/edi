// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// edi's Theme and Qt's colour scheme: Light and Dark override; System follows the browser's prefers-color-scheme in
// the web app (edi #123) and the platform on the desktop.
TestCase {
    name: "ColorScheme"

    function test_light_and_dark_override_everything() {
        for (const browser of [-1, 0, 1]) {
            compare(ApplicationInfo.schemeFor(0, browser), Qt.ColorScheme.Light);
            compare(ApplicationInfo.schemeFor(1, browser), Qt.ColorScheme.Dark);
        }
    }
    function test_system_follows_the_browser_in_the_web_app() {
        compare(ApplicationInfo.schemeFor(2, 1), Qt.ColorScheme.Dark);
        compare(ApplicationInfo.schemeFor(2, 0), Qt.ColorScheme.Light);
    }
    function test_system_is_the_platform_on_the_desktop() {
        compare(ApplicationInfo.schemeFor(2, -1), Qt.ColorScheme.Unknown);
    }
}
