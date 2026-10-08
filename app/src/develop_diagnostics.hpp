// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_DEVELOP_DIAGNOSTICS_HPP
#define EDI_APP_DEVELOP_DIAGNOSTICS_HPP

class QQmlApplicationEngine;

namespace edi_app {

// The web build's window.ediDevelopDiagnostics(action), for the browser checks, which cannot reach the controls
// inside Qt's dialogs through the page's accessibility tree. "open" opens Preferences, selects Develop and opens
// Diagnostics through their own controls; "read" returns the dialogs' state, the text Diagnostics shows and the
// text ApplicationInfo provides; "close" closes both and resolves once they have closed. Nothing elsewhere.
void install_develop_diagnostics(QQmlApplicationEngine& engine);

}  // namespace edi_app

#endif  // EDI_APP_DEVELOP_DIAGNOSTICS_HPP
