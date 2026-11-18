// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// The whole window starts without a single QML warning (a binding to something undefined, a missing property).
TestCase {
    name: "MainStartup"
    when: windowShown

    function test_startup_prints_no_qml_warning() {
        failOnWarning(/qml|QML|\.js:/);  // every QML message; the offscreen platform's own GL notices are not QML
        const component = Qt.createComponent("qrc:/qt/qml/edi/app/qml/Main.qml");
        verify(component.status === Component.Ready, component.errorString());
        const window = component.createObject(null);
        verify(window);
        window.visible = true;
        tryVerify(() => findChild(window, "likes.bar") !== null, 10000);
        wait(1500);  // the deferred pages and bindings settle
        const bar = findChild(window, "likes.bar");
        verify(bar.parent !== null, "the likes bar has a parent");
        window.destroy();
    }
}
