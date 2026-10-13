import QtQuick
import QtTest
import EasyApplication.Gui.Style as EaStyle
import DisplayFontTests 1.0

TestCase {
    name: "BundledDisplayFonts"
    DisplayFontProof { id: proof }
    function test_actual_shaping_uses_only_packaged_faces_data() {
        return [
            { tag: "default-regular", family: EaStyle.Fonts.fontFamily, weight: 400, style: "", face: 400, corpus: "PT Sans" },
            { tag: "default-bold", family: EaStyle.Fonts.ptSansBold.name, weight: 700, style: "Bold", face: 700, corpus: "PT Sans", characters: "Bragg peaks" },
            { tag: "selected-noto", family: "Noto Sans", weight: 400, style: "Regular", face: 400, corpus: "Noto Sans" },
            { tag: "mono", family: EaStyle.Fonts.monoFontFamily, weight: 400, style: "", face: 400, corpus: "PT Mono" },
            { tag: "light", family: EaStyle.Fonts.secondFontFamily, weight: 300, style: "Light", face: 300, corpus: "Noto Sans" },
            { tag: "arrow", family: EaStyle.Fonts.encodeSansRegular.name, weight: 400, style: "", face: 400, corpus: "Encode Sans" },
            { tag: "icons", family: EaStyle.Fonts.iconsFamily, weight: 400, style: "", face: 900, corpus: "Font Awesome" }
        ];
    }
    function test_actual_shaping_uses_only_packaged_faces(data) {
        const characters = data.characters ?? proof.characters(data.corpus);
        verify(characters.length > 0, "The font gate must reach the production display alphabet");
        compare(proof.failures(characters, data.family, data.weight, data.style, data.face).join("\n"), "",
                "Actual Qt glyph runs must use a nonzero glyph from a packaged font, never a system face");
    }
    function test_unbundled_face_cannot_satisfy_coverage() {
        const family = proof.unbundledFamily();
        verify(family.length > 0, "The escape witness must load an actual unbundled test face");
        verify(proof.failures("A", family, 400, "", 400).length > 0,
               "An unbundled font must not satisfy the actual rendering-face invariant");
    }
}
