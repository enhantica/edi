// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

// edi's font set, built in place of the pinned base's Style/Fonts.qml (cmake/EdiGuiBase.cmake; ADR-0015 §10).
// The base's file loads Encode Sans and Nunito, which edi no longer bundles, and a loader without its file
// warns. This one keeps every name the base's components read (fontFamily, monoFontFamily, secondFontFamily,
// thirdFontFamily, iconsFamily) and loads only what edi bundles: PT Sans, PT Mono and Font Awesome from the
// base, Noto Sans and Baloo 2 from edi's resources.
QtObject {
    id: fonts

    // The base's faces
    property FontLoader ptSansRegular: FontLoader {
        source: fonts.fontPath("PT_Sans", "PTSans-Regular.ttf")
    }
    property FontLoader ptSansBold: FontLoader {
        source: fonts.fontPath("PT_Sans", "PTSans-Bold.ttf")
    }
    property FontLoader ptMono: FontLoader {
        source: fonts.fontPath("PT_Mono", "PTMono-Regular.ttf")
    }
    property FontLoader fontAwesomeSolid: FontLoader {
        source: fonts.fontPath("FontAwesome", "Font Awesome 5 Free-Solid-900.otf")
    }

    // edi's faces. Noto Sans and Noto Sans Mono draw every character PT Sans and PT Mono lack, registered by
    // the host (engine_setup.cpp); Noto Sans Light the large light placeholder text; Baloo 2 the wordmark.
    property FontLoader notoSansLight: FontLoader {
        source: fonts.fontPath("Noto_Sans", "NotoSans-Light.ttf")
    }
    property FontLoader baloo2Regular: FontLoader {
        source: fonts.fontPath("Baloo_2", "Baloo2-Regular.ttf")
    }
    property FontLoader baloo2SemiBold: FontLoader {
        source: fonts.fontPath("Baloo_2", "Baloo2-SemiBold.ttf")
    }

    // Font families, by the base's names
    readonly property string fontFamily: ptSansRegular.name
    readonly property string fontSource: ptSansRegular.source
    readonly property string monoFontFamily: ptMono.name
    readonly property string secondFontFamily: notoSansLight.name
    readonly property string thirdFontFamily: baloo2Regular.name
    readonly property string iconsFamily: fontAwesomeSolid.name

    // Logic
    function fontPath(fontDirName, fontFileName) {
        const fontsDirPath = Qt.resolvedUrl("../Resources/Fonts");
        return fontsDirPath + "/" + fontDirName + "/" + fontFileName;
    }
}
