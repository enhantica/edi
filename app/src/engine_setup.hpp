// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_ENGINE_SETUP_HPP
#define EDI_APP_ENGINE_SETUP_HPP

class QQmlEngine;

namespace edi_app {

// The engine setup the host and the Qt Quick Test runner share: the values the gui-components base
// reads from its host — a writable settings file and "not a test run".
void configure_engine(QQmlEngine& engine);
// The application's default font, before any QML loads: the base's bundled design font (PT Sans), without hinting, drawn by Qt Quick's own text
// rendering on every platform; every character PT Sans lacks comes from the bundled Noto Sans, every one PT Mono lacks from Noto Sans Mono. Call it
// once the QGuiApplication exists; the app uses only its bundled fonts.
void use_design_font();
// A demo capture or a test run must not read or write the user's saved settings (the base's Settings:
// window geometry, preferences, theme, project location): it points them, and any default QSettings, at
// a fresh directory that lives as long as the process; it aborts when that directory cannot be created.
// Call it before configure_engine().
void use_fresh_settings();
// Text renders with Qt's FreeType font engine (ADR-0015 §10). select_freetype_engine(), given main's
// arguments, completes QT_QPA_PLATFORM before the QGuiApplication exists: on macOS and Windows the default
// platform (cocoa, windows) gains fontengine=freetype; Linux platforms render with FreeType already.
// require_freetype_engine() then aborts unless the platform in use was started with the FreeType engine — a
// platform without it (macOS offscreen is CoreText-only) fails loudly, never falls back silently. It reads
// only public settings; the UI test's glyph comparison is the proof that FreeType renders.
void select_freetype_engine(int argc, char** argv);
void require_freetype_engine();

}  // namespace edi_app

#endif  // EDI_APP_ENGINE_SETUP_HPP
