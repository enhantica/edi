// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_ENGINE_SETUP_HPP
#define EDI_APP_ENGINE_SETUP_HPP

#include <QString>
#include <memory>
#include "assistant_work_report.hpp"

class QQmlEngine;

namespace edi_app {
class Session;

// The engine setup the host and the Qt Quick Test runner share: the values the gui-components base
// reads from its host — a writable settings file and "not a test run".
void configure_engine(QQmlEngine& engine);
void configure_engine(QQmlEngine& engine, AssistantWorkReportOptions options);
void configure_engine(QQmlEngine& engine, std::unique_ptr<Session> session);
// ADR-0031 §3: the one app-settings store's file on the desktop, QSettings' ini file of the user scope
// (`~/.config/EasyScience/EasyDiffraction.ini` on Linux and macOS).
QString settings_store_path();
// The settings file the engine was configured with (the store, a demo or test run's fresh file, or the browser's
// copy); empty before configure_engine.
QString settings_file_path();
// In the browser, writes the settings file's current text to the page's storage at once, rather than at the next
// check (configure_engine), so a reload soon after a change finds it; nothing to do on the desktop, where the file
// is the store.
void store_settings_now();
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
