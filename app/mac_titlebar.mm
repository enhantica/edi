// SPDX-License-Identifier: BSD-3-Clause
// Experiment: hide the window title that macOS still draws over a merged title bar.
#import <AppKit/AppKit.h>
#include <QWindow>

void hide_mac_window_title(QWindow* window) {
    auto* view = reinterpret_cast<NSView*>(window->winId());
    if (view && view.window) view.window.titleVisibility = NSWindowTitleHidden;
}
