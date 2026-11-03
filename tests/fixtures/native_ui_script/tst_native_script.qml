import QtQuick
import QtTest
import edi.app
import EdiNativeScriptFixture 1.0
TestCase {
    name: "NativeUiScriptWitness"
    when: windowShown
    function test_actual_native_script() {
        const result = NativeScriptFixture.execute(ApplicationInfo);
        verify(result.ok, "The actual native UI witness must execute: " + result.error);
    }
}
