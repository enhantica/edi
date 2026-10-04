# SPDX-License-Identifier: BSD-3-Clause
# Sourced by the UI test (ADR-0015 §10): the platform the demo capture runs on, where the app draws as it
# does for users, with FreeType. macOS runs on cocoa, whose FreeType engine the app requires and whose macOS
# offscreen counterpart lacks; cocoa needs a logged-in window session, and without one the gate stops here
# naming the session it found, never falling back to another platform. Linux runs on an X display of its own
# (app_x_display). The Qt test runner checks behaviour, not pixels, and runs on offscreen on every
# platform (app_tests_main.cpp).
app_capture_platform() {
    if [ -n "${QT_QPA_PLATFORM:-}" ]; then
        return 0  # the caller's choice; the app still refuses a platform without FreeType
    fi
    if [ "$(uname -s)" = Darwin ]; then
        local session
        session=$(launchctl managername 2>/dev/null || echo unknown)
        if [ "$session" != Aqua ]; then
            echo "$1: macOS runs the app on cocoa, which needs a logged-in window session; this process is in the '$session' session" >&2
            return 1
        fi
        export QT_QPA_PLATFORM=cocoa
    else
        app_x_display "$1"
    fi
}

# The Linux capture draws through Qt Quick's OpenGL renderer, as on a desktop and as cocoa does on macOS:
# the offscreen platform has only the software renderer, which cannot run the base's shader effects (the
# popups' backgrounds and shadows). Everything comes from the app environment: Weston's headless backend
# runs a rootful Xwayland of the capture's size, the app runs on it through xcb, and Mesa's llvmpipe draws
# its OpenGL. (conda-forge's Mesa has no Wayland EGL platform, so the app cannot be a Wayland client of
# Weston itself.) Both servers stop when the calling script exits.
app_x_display() {
    local runtime
    runtime=$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/edi-xdg.XXXXXX")  # A cancel cannot strand it
    XDG_RUNTIME_DIR="$runtime" weston --backend=headless --renderer=pixman --width=1280 --height=768 \
        --socket=edi-app --idle-time=0 >"$runtime/weston.log" 2>&1 &
    APP_DISPLAY_PIDS=$!
    trap 'kill $APP_DISPLAY_PIDS 2>/dev/null; wait $APP_DISPLAY_PIDS 2>/dev/null; rm -rf "'"$runtime"'"' EXIT
    _app_await "$1" "$APP_DISPLAY_PIDS" "[ -S '$runtime/edi-app' ]" "Weston" "$runtime/weston.log" || return 1
    XDG_RUNTIME_DIR="$runtime" WAYLAND_DISPLAY=edi-app Xwayland -geometry 1280x768 -shm -nolisten tcp \
        -displayfd 5 5>"$runtime/display" >"$runtime/xwayland.log" 2>&1 &
    local xwayland=$!
    APP_DISPLAY_PIDS="$xwayland $APP_DISPLAY_PIDS"
    _app_await "$1" "$xwayland" "[ -s '$runtime/display' ]" "Xwayland" "$runtime/xwayland.log" || return 1
    export DISPLAY=":$(cat "$runtime/display")" QT_QPA_PLATFORM=xcb
    export APP_DISPLAY="Xwayland on headless Weston, Mesa llvmpipe OpenGL"
    # Mesa's llvmpipe from the environment, whatever GPU or other vendor library the host has.
    export __EGL_VENDOR_LIBRARY_FILENAMES="$CONDA_PREFIX/share/glvnd/egl_vendor.d/50_mesa.json"
    export __GLX_VENDOR_LIBRARY_NAME=mesa GALLIUM_DRIVER=llvmpipe
}

# _app_await <gate> <pid> <ready-test> <server> <log>: up to 10 s for the server to become ready; a server
# that exits or never gets there stops the gate with its log.
_app_await() {
    local attempt
    for attempt in $(seq 1 100); do
        eval "$3" && return 0
        kill -0 "$2" 2>/dev/null || break
        sleep 0.1
    done
    echo "$1: the headless display's $4 did not start:" >&2
    cat "$5" >&2
    return 1
}
