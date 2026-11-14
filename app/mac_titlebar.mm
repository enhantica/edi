// SPDX-License-Identifier: BSD-3-Clause
// Experiment: a merged title bar on macOS. The window title is hidden and the traffic lights move down to sit
// in our app bar, centred on its row; macOS lays them out again after a resize, so they are placed again then.
#import <AppKit/AppKit.h>
#include <QWindow>

namespace {
void place_traffic_lights(NSWindow* window, CGFloat bar_height, CGFloat left) {
    NSButton* close = [window standardWindowButton:NSWindowCloseButton];
    NSButton* minimize = [window standardWindowButton:NSWindowMiniaturizeButton];
    NSButton* zoom = [window standardWindowButton:NSWindowZoomButton];
    if (!close || !minimize || !zoom || (window.styleMask & NSWindowStyleMaskFullScreen)) return;
    NSView* container = close.superview.superview;
    NSRect frame = container.frame;
    frame.size.height = bar_height;
    frame.origin.y = NSHeight(window.frame) - bar_height;
    container.frame = frame;
    const CGFloat step = NSMinX(minimize.frame) - NSMinX(close.frame);
    NSArray<NSButton*>* buttons = @[close, minimize, zoom];
    for (NSUInteger i = 0; i < buttons.count; ++i) {
        NSButton* button = buttons[i];
        [button setFrameOrigin:NSMakePoint(left + i * step, (bar_height - NSHeight(button.frame)) / 2)];
    }
}
}  // namespace

void merge_mac_title_bar(QWindow* window, double bar_height) {
    auto* view = reinterpret_cast<NSView*>(window->winId());
    NSWindow* ns = view ? view.window : nil;
    if (!ns) return;
    ns.titleVisibility = NSWindowTitleHidden;
    const CGFloat height = bar_height, left = 20;
    place_traffic_lights(ns, height, left);
    for (NSNotificationName name : {NSWindowDidResizeNotification, NSWindowDidEndLiveResizeNotification,
                                     NSWindowDidExitFullScreenNotification, NSWindowDidBecomeKeyNotification}) {
        [[NSNotificationCenter defaultCenter] addObserverForName:name object:ns queue:nil
                                                      usingBlock:^(NSNotification*) { place_traffic_lights(ns, height, left); }];
    }
}
