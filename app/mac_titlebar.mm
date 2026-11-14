// SPDX-License-Identifier: BSD-3-Clause
// Experiment: a merged title bar on macOS. The window title is hidden; the traffic lights stay where macOS puts
// them, and the app bar's first button lines up with the red one (its left edge in points is returned).
#import <AppKit/AppKit.h>
#include <QWindow>

double merge_mac_title_bar(QWindow* window) {
    auto* view = reinterpret_cast<NSView*>(window->winId());
    NSWindow* ns = view ? view.window : nil;
    if (!ns) return -1;
    ns.titleVisibility = NSWindowTitleHidden;
    NSButton* close = [ns standardWindowButton:NSWindowCloseButton];
    return close ? NSMinX([close convertRect:close.bounds toView:nil]) : -1;
}
