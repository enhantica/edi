// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_WEB_PAGE_HOOKS_HPP
#define EDI_APP_WEB_PAGE_HOOKS_HPP

class QQmlApplicationEngine;

namespace edi_app {

// The web build's page hooks for the browser checks, which cannot reach controls inside Qt's dialogs or the rows of
// a recycled table through the page's accessibility tree. Nothing elsewhere.
//  - window.ediDevelopDiagnostics(action): "open" opens Preferences, selects Develop and opens Diagnostics through
//    their own controls; "read" returns the dialogs' state, the text Diagnostics shows and the text ApplicationInfo
//    provides; "close" closes both and resolves once they have closed.
//  - window.ediControlGeometry(name): the one visible item of that name's scene rectangle and state, read only.
//  - window.ediFitProgress(): the status bar's fit progress text, its visibility and whether the fit is running.
//  - window.ediOpenExample(id): Session::openExample(id) on the bundled examples, returning its result.
void install_web_page_hooks(QQmlApplicationEngine& engine);

}  // namespace edi_app

#endif  // EDI_APP_WEB_PAGE_HOOKS_HPP
