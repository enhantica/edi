import QtQuick
import QtTest
import edi.app
TestCase {
    name: "E04MissingPropertyEscape"
    function test_missing_property() {
        failOnWarning(/.*/);
        const object = Qt.createQmlObject('import QtQuick; import edi.app; QtObject { property real broken: Session.e04MissingProperty }', this);
        verify(object !== null, "I10: the broken fixture reaches the QML warning channel");
    }
}
