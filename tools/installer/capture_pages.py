# SPDX-License-Identifier: BSD-3-Clause
"""Capture every page of the installer and its maintenance tool, in light and in dark.

Builds the small marker installer the protocol check uses (no app build), then runs it with the
pages saving themselves (Installer.qs, EDI_INSTALLER_CAPTURE) and moving on: on Windows and macOS
once per theme with the system's own appearance set, on Linux with a KDE colour scheme for dark
(the palette Qt reads from kdeglobals). --marker-only builds the marker installer and prints its
path, for the macOS accessibility check (a11y-check.sh). After each install the installed
maintenance tool runs the same way, then the installation is removed. The PNGs go to --output for
a run artifact; nothing is committed.

The walks write every page they show to pages/pages.log, in order (Installer.qs). The run fails
unless that list is exactly the expected (page, mode, theme) sequence and each page that has a
picture has one: no page missing, none extra. What each maintenance mode did is checked on disk.
"""

import argparse
import base64
import contextlib
import ctypes
import json
import os
import plistlib
import re
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

from package import (
    ASSISTANT_RUNTIME,
    SUFFIX,
    SYSTEM,
    clean_environment,
    installer_from_download,
    package_app,
)
from protocol_check import installer_command

PERSONALIZE = r'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'


# The marker app's one file, relative to the stage and to the installation.
APP_MARKER = Path(
    'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
    if SYSTEM == 'macos'
    else 'bin/EasyDiffraction' + SUFFIX
)


def marker_stage(root: Path) -> Path:
    stage = root / 'marker-stage'
    app = stage / APP_MARKER
    app.parent.mkdir(parents=True)
    app.write_text('marker\n')
    assistant = stage / ASSISTANT_RUNTIME / 'assistant.txt'
    assistant.parent.mkdir(parents=True)
    assistant.write_text('optional assistant marker\n')
    return stage


def set_windows_theme(theme: str) -> None:
    value = '0' if theme == 'dark' else '1'
    for name in ('AppsUseLightTheme', 'SystemUsesLightTheme'):
        subprocess.run(
            ['reg', 'add', PERSONALIZE, '/v', name, '/t', 'REG_DWORD', '/d', value, '/f'],
            check=True,
        )


def running(image: str) -> bool:
    """Whether a Windows process with this executable name still runs."""
    listed = subprocess.run(
        ['tasklist', '/FI', f'IMAGENAME eq {image}', '/NH'],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    return image.lower() in listed.stdout.lower()


def current_page(pages: Path) -> str:
    """The page a walk shows now: the last line of its page log, or '' before the first page."""
    log = pages / 'pages.log'
    lines = log.read_text(encoding='utf-8').split() if log.exists() else []
    return lines[-1] if lines else ''


class ScreenFrames(threading.Thread):
    """Windows: a screenshot about every second while a wizard runs, named after its page.

    A process the wizard starts cannot take one there, so the pages are captured from here. A
    frame is kept as <page>.png only when the page log names the same page before and after it,
    and only for a page that has a picture.
    """

    def __init__(self, pages: Path, prefix: str) -> None:
        super().__init__(daemon=True)
        self.pages, self.prefix, self.done = pages, prefix, threading.Event()

    def run(self) -> None:
        scratch = self.pages / f'{self.prefix}-scratch.png'
        while not self.done.is_set():
            before = current_page(self.pages)
            subprocess.run(
                powershell(SCREEN.format(file=scratch)),
                capture_output=True, timeout=60, check=False,
            )  # fmt: skip
            if scratch.exists():
                pictured = before.rsplit('-', 1)[0] not in UNPICTURED
                if before and pictured and before == current_page(self.pages):
                    scratch.replace(self.pages / f'{before}.png')
                else:
                    scratch.unlink()


@contextlib.contextmanager
def screen_frames(pages: Path, prefix: str) -> Iterator[None]:
    """Windows: screenshots while wizards run (ScreenFrames); elsewhere pages take their own."""
    frames = ScreenFrames(pages, prefix) if SYSTEM == 'windows' else None
    if frames:
        frames.start()
    try:
        yield
    finally:
        if frames:
            frames.done.set()
            frames.join(timeout=90)


def run_pages(
    command: list, env: dict, log: Path, pages: Path, finished: str, allowed: tuple = (0,)
) -> None:
    """Run a wizard whose pages move on by themselves; it ends at its last page, `finished`."""
    with screen_frames(pages, log.stem):
        _run_wizard(command, env, log, pages, finished, allowed)


def start_wizard(command: list, env: dict, log: Path) -> subprocess.Popen:
    """A wizard the walk leaves open on a pop-up or a refusal; stop_wizard ends it."""
    stream = log.open('w', encoding='utf-8')
    process = subprocess.Popen(
        [*command, '--verbose'] if SYSTEM == 'windows' else command,
        env=env, stdout=stream, stderr=subprocess.STDOUT,
    )  # fmt: skip
    process.log_stream = stream
    return process


def wait_picture(pages: Path, picture: str, process: subprocess.Popen, log: Path) -> None:
    """Wait until `picture` is taken; the wizard stays on that state until it is stopped."""
    deadline = time.monotonic() + 180
    while not (pages / picture).exists():
        # On Windows the wizard can go on in a process of its own, so this one ending says nothing.
        if SYSTEM != 'windows' and process.poll() is not None:
            raise RuntimeError(
                f'{process.args[0]} ended with {process.returncode} before {picture}; see {log}'
            )
        if time.monotonic() > deadline:
            raise RuntimeError(f'No {picture} after 180 s; see {log}')
        time.sleep(1)
    # The grab writes its file a moment after it starts; on Windows a later frame is surer.
    time.sleep(3)


def stop_wizard(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.kill()
    process.wait(timeout=60)
    # The wizard that went on in a process of its own (Windows) is ended by its name.
    image = Path(process.args[0]).name
    if SYSTEM == 'windows' and running(image):
        subprocess.run(['taskkill', '/F', '/IM', image], capture_output=True, check=False)
    process.log_stream.close()


def _run_wizard(
    command: list, env: dict, log: Path, pages: Path, finished: str, allowed: tuple
) -> None:
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run(
            # On Windows the wizard stays attached, and logs, only with --verbose.
            [*command, '--verbose'] if SYSTEM == 'windows' else command,
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=240, check=False,
        )  # fmt: skip
        stream.write(f'\nexit {result.returncode}\n')
    rc = result.returncode
    # On Windows the wizard can return at once and go on in a process of its own: wait for it.
    deadline = time.monotonic() + 240
    image = Path(command[0]).name
    while SYSTEM == 'windows' and running(image):
        if time.monotonic() > deadline:
            raise RuntimeError(f'{image} still runs after 240 s')
        time.sleep(2)
    walked = current_page(pages) == finished
    # The Framework on Linux crashes as it quits (SIGSEGV) after the walk is done; that alone
    # passes, and only once the walk showed its last page.
    quit_crash = SYSTEM == 'linux' and rc == -11 and walked
    # A maintenance tool left on its last page's Cancel button ends with 1 after its work
    # (Installer.qs), so 1 also needs that last page shown.
    if not quit_crash and (rc not in allowed or (rc == 1 and not walked)):
        raise RuntimeError(f'{command[0]} ended with {rc}; its log is {log}')


# The foreground window only (the wizard, or its pop-up), as DWM draws it: GetWindowRect would add
# the invisible resize border. DPI aware, so the rectangle and the copy are in the same pixels.
# With no foreground window the whole screen is taken.
SCREEN = (
    'Add-Type -AssemblyName System.Windows.Forms,System.Drawing; '
    "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
    'public struct EdiRect {{ public int L, T, R, B; }} '
    'public static class EdiWindow {{ '
    '[DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); '
    '[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow(); '
    '[DllImport("dwmapi.dll")] public static extern int DwmGetWindowAttribute('
    "IntPtr w, int a, out EdiRect r, int s); }}'; "
    '[void][EdiWindow]::SetProcessDPIAware(); '
    '$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; '
    '$r=New-Object EdiRect; '
    '$h=[EdiWindow]::GetForegroundWindow(); '
    'if ($h -ne [IntPtr]::Zero -and [EdiWindow]::DwmGetWindowAttribute($h, 9, [ref]$r, 16) -eq 0 '
    '-and $r.R -gt $r.L -and $r.B -gt $r.T) '
    '{{ $b=New-Object System.Drawing.Rectangle $r.L,$r.T,($r.R-$r.L),($r.B-$r.T) }}; '
    '$i=New-Object System.Drawing.Bitmap $b.Width,$b.Height; '
    '$g=[System.Drawing.Graphics]::FromImage($i); '
    '$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); '
    "$i.Save('{file}')"
)


def powershell(script: str) -> list:
    """A PowerShell command line for `script`, encoded so its quotes reach it as written."""
    encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    return ['powershell', '-NoProfile', '-EncodedCommand', encoded]


def probe_screen(pages: Path, output: Path) -> None:
    """Whether this Windows session can take a screenshot at all, written to screen-probe.log."""
    result = subprocess.run(
        powershell(SCREEN.format(file=pages / 'probe.png')),
        capture_output=True, text=True, timeout=60, check=False,
    )  # fmt: skip
    (output / 'screen-probe.log').write_text(
        f'exit {result.returncode}\n{result.stdout}\n{result.stderr}', encoding='utf-8'
    )


# KDE's Breeze Dark colours, as kdeglobals holds them: on Linux Qt takes its palette from them when
# the desktop is KDE, as a KDE user in dark mode sees the installer.
BREEZE_DARK = """[General]
ColorScheme=BreezeDark

[Colors:Window]
BackgroundNormal=32,35,38
ForegroundNormal=252,252,252

[Colors:View]
BackgroundNormal=20,22,24
ForegroundNormal=252,252,252

[Colors:Button]
BackgroundNormal=41,44,48
ForegroundNormal=252,252,252

[Colors:Selection]
BackgroundNormal=61,174,233
ForegroundNormal=252,252,252

[Colors:Tooltip]
BackgroundNormal=41,44,48
ForegroundNormal=252,252,252
"""


def kde_dark(home: Path) -> dict:
    """Linux: the environment of a KDE session in Breeze Dark, its kdeglobals written in `home`."""
    for folder in (home / 'config', home / '.kde/share/config'):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'kdeglobals').write_text(BREEZE_DARK, encoding='utf-8')
    return {
        'XDG_CURRENT_DESKTOP': 'KDE',
        'KDE_SESSION_VERSION': '5',
        'KDEHOME': str(home / '.kde'),
    }


def set_macos_theme(theme: str) -> None:
    """The system appearance, switched live as its settings do; Qt follows only a live switch."""
    dark = 'true' if theme == 'dark' else 'false'
    script = (
        'tell application "System Events" to tell appearance preferences'
        f' to set dark mode to {dark}'
    )
    subprocess.run(['osascript', '-e', script], check=True, timeout=60)


# Closes only the Finder windows showing the folder given as the script's argument.
CLOSE_WINDOW = (
    'tell application "Finder" to close (every window whose target is '
    '(POSIX file (item 1 of argv) as alias))'
)


# The window number of Finder's front window (listed first), for screencapture -l.
FINDER_WINDOW = (
    "ObjC.import('CoreGraphics');"
    ' var w = ObjC.deepUnwrap(ObjC.castRefToObject($.CGWindowListCopyWindowInfo(1, 0)))'
    ".filter(function (x) { return x.kCGWindowOwnerName == 'Finder' && x.kCGWindowLayer == 0; });"
    " w.length ? String(w[0].kCGWindowNumber) : ''"
)


def capture_disk_image(image: Path, pages: Path, theme: str) -> None:
    """macOS: the disk image's Finder window as users see it once the download opens.

    Mounted at a folder of its own, so another volume of the same name is never the one shown,
    closed or detached.
    """
    mount = Path(tempfile.mkdtemp(prefix='edi-disk-image-'))
    attached = subprocess.run(
        ['hdiutil', 'attach', str(image), '-mountpoint', str(mount), '-plist'],
        capture_output=True, check=True, timeout=120,
    )  # fmt: skip
    entities = plistlib.loads(attached.stdout)['system-entities']
    # hdiutil names the mount point with its links resolved (/private/var/... for /var/...).
    mounted = [e['dev-entry'] for e in entities if e.get('mount-point') == os.path.realpath(mount)]
    if len(mounted) != 1:
        raise RuntimeError(f'hdiutil did not mount {image} at {mount}: {entities}')
    # The whole image's device (/dev/diskN), not only its volume's slice.
    device = re.match(r'/dev/disk\d+', mounted[0]).group(0)
    try:
        subprocess.run(['open', str(mount)], check=True, timeout=60)
        time.sleep(4)
        picture = pages / f'disk-image-{theme}.png'
        # Finder's front window only, without its shadow (the whole screen if none is found).
        window = subprocess.run(
            ['osascript', '-l', 'JavaScript', '-e', FINDER_WINDOW],
            capture_output=True, text=True, check=True, timeout=60,
        ).stdout.strip()  # fmt: skip
        subprocess.run(
            ['screencapture', '-x', '-o', *([f'-l{window}'] if window else []), str(picture)],
            check=True, timeout=60,
        )  # fmt: skip
    finally:
        subprocess.run(
            [
                'osascript',
                '-e', 'on run argv',
                '-e', CLOSE_WINDOW,
                '-e', 'end run',
                str(mount),
            ],
            check=False, timeout=60,
        )  # fmt: skip
        subprocess.run(['hdiutil', 'detach', device], check=False, timeout=120)
        if mount.exists() and not any(mount.iterdir()):
            mount.rmdir()


def marker_installer(tools: Path, work: Path) -> Path:
    """The offline marker installer's download, whose repository holds a newer version.

    The maintenance tool then has components to add and an update to apply, as protocol_check.py
    sets it up, so every one of its modes shows its pages.
    """
    stage = marker_stage(work)
    repository = (work / 'online/repository').as_uri() + '/'
    with patch('package.repository_urls', return_value=(repository,)):
        package_app(stage, tools, work / 'offline', '26.17')
    app = stage / APP_MARKER
    app.write_text('updated marker\n')
    (stage / ASSISTANT_RUNTIME / 'assistant.txt').write_text('updated assistant marker\n')
    package_app(stage, tools, work / 'online', '26.18', repository)
    metadata = (work / 'offline/installer.json').read_text()
    return work / 'offline' / json.loads(metadata)['download']


def capture(tools: Path, output: Path) -> None:
    output = output.resolve()
    work = output / 'work'
    work.mkdir(parents=True)
    pages = output / 'pages'
    pages.mkdir()
    if SYSTEM == 'windows':
        probe_screen(pages, output)
    download = marker_installer(tools, work)
    themes = ('light', 'dark')
    for theme in themes:
        home = work / f'home-{theme}'
        home.mkdir()
        env = clean_environment(home)
        env.pop('QT_QPA_PLATFORM', None)  # the wizard shows itself on the display the job provides
        env.pop('QT_QUICK_BACKEND', None)
        env['EDI_INSTALLER_CAPTURE'] = str(pages)
        if SYSTEM == 'windows':
            set_windows_theme(theme)
        else:
            env['EDI_INSTALLER_THEME'] = theme
        if SYSTEM == 'macos':
            set_macos_theme(theme)
            capture_disk_image(download, pages, theme)
        if SYSTEM == 'linux' and theme == 'dark':
            env |= kde_dark(home)
        if 'DISPLAY' in os.environ:
            env['DISPLAY'] = os.environ['DISPLAY']
        installer = installer_command(
            installer_from_download(download, work / f'unpacked-{theme}')
        )
        # A fresh folder of its own: maintenance and cleanup touch only this installation.
        target = home / 'EasyDiffraction'
        if target.exists():
            raise RuntimeError(f'The capture target already exists: {target}')
        run_pages(
            [str(installer), f'TargetDir={target}'],
            env,
            output / f'installer-{theme}.log',
            pages,
            f'installer-Finished-{theme}',
        )
        # The install page's assistant box starts ticked, so the walk installs the assistant too.
        check_installation(target, '', 'installing')
        walk_installed(installer, target, env, output, pages, theme)
        # Updating both, turning the assistant over (so removing it here), removing everything.
        for mode in ('update', 'add', 'remove'):
            walk_maintenance(mode, target, env, output, pages, theme)
        # Updating where the assistant is not installed, on an installation of its own made from
        # the command line.
        for mode, components in (('updatewithout', []),):
            target = home / mode
            subprocess.run(
                [
                    str(installer), '--root', str(target), '--accept-licenses',
                    '--default-answer', '--confirm-command', 'install', *components,
                ],
                # As a captured install, so its progress page is held (holdProgress).
                env=env | {'EDI_INSTALLER_CAPTURE': str(work / 'headless')},
                check=True, timeout=240,
            )  # fmt: skip
            check_installation(target, '' if components else 'none', 'installing')
            walk_maintenance(mode, target, env, output, pages, theme)
            purge(target, env)
        walk_locked(installer, home, env, output, pages, theme)
        icon_check(pages, theme)
    if SYSTEM == 'macos':
        set_macos_theme('light')
    require_pages(pages, themes)
    print(f'{len(list(pages.glob("*.png")))} page captures in {pages}')


def walk_installed(
    installer: Path, target: Path, env: dict, output: Path, pages: Path, theme: str
) -> None:
    """The installer again over its installation: its warning, then Install leaving the page."""
    state = env | {'EDI_INSTALLER_CAPTURE_STATE': 'installed'}
    log = output / f'installer-installed-{theme}.log'
    with screen_frames(pages, log.stem):
        process = start_wizard([str(installer), f'TargetDir={target}'], state, log)
        try:
            wait_picture(pages, f'installer-installed-InstallPressed-{theme}.png', process, log)
        finally:
            stop_wizard(process)
    check_installation(target, '', 'installing')


def second_installer(installer: Path) -> Path:
    """The installer under another file name, as a second download would be.

    The Framework refuses a second copy of the same file outright (a lock named after it); another
    one starts and finds the download cache locked, the state users meet (Installer.qs, LOCKED).
    """
    if SYSTEM == 'macos':
        bundle = installer.parents[2]
        copy = bundle.with_name(f'{bundle.stem}-second.app')
        if not copy.exists():
            shutil.copytree(bundle, copy, symlinks=True)
        renamed = copy / 'Contents/MacOS' / f'{installer.name}-second'
        if not renamed.exists():
            shutil.copy2(copy / 'Contents/MacOS' / installer.name, renamed)
        return renamed
    copy = installer.with_name(f'{installer.stem}-second{installer.suffix}')
    if not copy.exists():
        shutil.copy2(installer, copy)
    return copy


# Linux only for now: the X server moves the pointer onto a button by its own call, so one picture
# shows a hovered secondary button. Windows and macOS do not take that picture.
HOVER = {'EDI_INSTALLER_CAPTURE_HOVER': '1'} if SYSTEM == 'linux' else {}


def point_at_cancel(pages: Path, page: str, process: subprocess.Popen, log: Path) -> None:
    """Once the walk notes `page`, put the pointer on the window's Cancel button.

    The window is found as the screen's one non-black area (the grab trims the same way); Cancel is
    the last button, its centre 62 px from the window's right edge and 31 from its bottom.
    """
    deadline = time.monotonic() + 120
    while current_page(pages) != page:
        if process.poll() is not None or time.monotonic() > deadline:
            raise RuntimeError(f'The walk never showed {page}; see {log}')
        time.sleep(0.2)
    area = subprocess.run(
        ['import', '-window', 'root', '-format', '%@', 'info:'],
        capture_output=True, text=True, check=True, timeout=60,
    ).stdout  # fmt: skip
    width, height, left, top = map(int, re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', area).groups())
    x11 = ctypes.CDLL('libX11.so.6')
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XDefaultRootWindow.restype = ctypes.c_ulong
    x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XWarpPointer.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int]
    x11.XWarpPointer.argtypes += [
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_int,
        ctypes.c_int,
    ]
    x11.XFlush.argtypes = x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    display = x11.XOpenDisplay(None)
    if not display:
        raise RuntimeError('No X display to move the pointer on')
    try:
        root = x11.XDefaultRootWindow(display)
        x11.XWarpPointer(display, 0, root, 0, 0, 0, 0, left + width - 62, top + height - 31)
        x11.XFlush(display)
    finally:
        x11.XCloseDisplay(display)


def walk_locked(
    installer: Path, home: Path, env: dict, output: Path, pages: Path, theme: str
) -> None:
    """One installer asks whether to quit while a second starts, which finds the first's lock."""
    first_log = output / f'installer-quit-{theme}.log'
    second_log = output / f'installer-locked-{theme}.log'
    with screen_frames(pages, first_log.stem):
        first = start_wizard(
            [str(installer), f'TargetDir={home / "quit"}'],
            env | {'EDI_INSTALLER_CAPTURE_STATE': 'quit'} | HOVER,
            first_log,
        )
        try:
            if HOVER:
                point_at_cancel(pages, f'installer-quit-CancelHover-{theme}', first, first_log)
            wait_picture(pages, f'installer-quit-Quit-{theme}.png', first, first_log)
            second = start_wizard(
                [str(second_installer(installer)), f'TargetDir={home / "locked"}'],
                env | {'EDI_INSTALLER_CAPTURE_STATE': 'locked'},
                second_log,
            )
            try:
                wait_picture(
                    pages, f'installer-locked-Introduction-{theme}.png', second, second_log
                )
            finally:
                stop_wizard(second)
        finally:
            stop_wizard(first)


# The icon check (Installer.qs, InstallerChrome.qss): a wizard button's icon (Back), an icon in a
# page's message (the warning over an installation) and one in a pop-up, each a picture of its own.
ICON_CHECK = {
    'button': 'installer-installed-TargetDirectory',
    'message': 'installer-installed-TargetDirectory',
    'popup': 'installer-quit-Quit',
}


def icon_check(pages: Path, theme: str) -> None:
    for name, source in ICON_CHECK.items():
        shutil.copy2(
            pages / f'{source}-{theme}.png', pages / f'installer-iconcheck-{name}-{theme}.png'
        )


def extra_pictures(theme: str) -> set:
    """The pictures made from the walks' own: the icon check."""
    return {f'installer-iconcheck-{name}-{theme}.png' for name in ICON_CHECK}


MAINTENANCE_TOOL = Path(
    'MaintenanceTool.app/Contents/MacOS/MaintenanceTool'
    if SYSTEM == 'macos'
    else 'MaintenanceTool' + SUFFIX
)
# What each maintenance mode leaves on disk: the app's and the assistant's text.
LEFT = {
    'installing': ('marker', 'optional assistant marker'),
    'update': ('updated marker', 'updated assistant marker'),
    'add': ('updated marker', None),
    'remove': (None, None),
    'updatewithout': ('updated marker', None),
}


def walk_maintenance(
    mode: str, target: Path, env: dict, output: Path, pages: Path, theme: str
) -> None:
    run_pages(
        [str(target / MAINTENANCE_TOOL)],
        env | {'EDI_INSTALLER_MAINTENANCE_MODE': mode},
        output / f'maintenance-{mode}-{theme}.log',
        pages,
        f'maintenance-{mode}-Finished-{theme}',
        # Left on its Cancel button (1) or closed by the walk (3); require_pages still demands its
        # pages.
        allowed=(0, 1, 3),
    )
    if mode == 'remove':
        # On Windows the maintenance tool cannot delete its own running executable; a helper it
        # starts deletes it and the folder after it quits. Give that a minute, then name the rest.
        deadline = time.monotonic() + 60
        while target.exists() and time.monotonic() < deadline:
            time.sleep(2)
    check_installation(target, '', mode)


def check_installation(target: Path, assistant: str, mode: str) -> None:
    """What is on disk after a mode, read from there, not from its pages."""

    def text(path: Path) -> str | None:
        return path.read_text(encoding='utf-8').strip() if path.exists() else None

    wanted = LEFT[mode] if assistant != 'none' else (LEFT[mode][0], None)
    found = text(target / APP_MARKER), text(target / ASSISTANT_RUNTIME / 'assistant.txt')
    tool = (target / MAINTENANCE_TOOL).exists()
    if found != wanted or tool != (mode != 'remove'):
        rest = sorted(str(path.relative_to(target)) for path in target.rglob('*'))
        raise RuntimeError(
            f'After {mode}, {target} holds app and assistant {found}, not {wanted}; maintenance'
            f' tool {"present" if tool else "absent"}; all that is left: {rest[:40]}'
        )


def purge(target: Path, env: dict) -> None:
    subprocess.run(
        [str(target / MAINTENANCE_TOOL), '--confirm-command', '--default-answer', 'purge'],
        env={k: v for k, v in env.items() if k != 'EDI_INSTALLER_CAPTURE'},
        timeout=240,
        check=False,
    )


# Every page each walk shows, in order. The installer passes its welcome and summary pages by
# itself and takes no picture of them; every other page has one.
# Updating goes straight to its summary; changing components asks about the assistant first.
UPDATING = ['Introduction', 'ReadyForInstallation', 'PerformInstallation', 'Finished']
CHANGING = [
    'Introduction',
    'AssistantForm',
    'ReadyForInstallation',
    'PerformInstallation',
    'Finished',
]
WALKS = {
    'installer': [
        'Introduction',
        'TargetDirectory',
        'ReadyForInstallation',
        'PerformInstallation',
        'Finished',
    ],
    # Over the installation: its warning, then the page staying when Install is pressed (the walk
    # stops there).
    'installer-installed': ['Introduction', 'TargetDirectory', 'InstallPressed'],
    'maintenance-update': UPDATING,
    'maintenance-add': CHANGING,
    'maintenance-remove': [
        'Introduction',
        'ReadyForInstallation',
        'PerformInstallation',
        'Finished',
    ],
    'maintenance-updatewithout': UPDATING,
    # Cancel asks whether to quit (a pop-up) and the walk stops there, holding its lock while a
    # second installer starts and stays on its first page saying so.
    'installer-quit': [
        'Introduction',
        'TargetDirectory',
        *(['CancelHover'] if HOVER else []),
        'Quit',
    ],
    'installer-locked': ['Introduction'],
}
UNPICTURED = {
    'installer-Introduction',
    'installer-ReadyForInstallation',
    'installer-installed-Introduction',
    'installer-quit-Introduction',
    'installer-quit-TargetDirectory',
}


def expected_pages(themes: tuple) -> list:
    """The (mode, page, theme) sequence the capture run shows, as the page log names it."""
    return [
        f'{mode}-{page}-{theme}' for theme in themes for mode, walk in WALKS.items()
        for page in walk
    ]  # fmt: skip


def require_pages(pages: Path, themes: tuple) -> None:
    """Fail unless the walks showed exactly the expected pages in order, each with its picture."""
    log = pages / 'pages.log'
    shown = log.read_text(encoding='utf-8').split() if log.exists() else []
    expected = expected_pages(themes)
    if shown != expected:
        raise RuntimeError(
            'The walks did not show the expected pages in order.\n'
            f'shown:    {", ".join(shown) or "none"}\nexpected: {", ".join(expected)}'
        )
    pictured = {f'{page}.png' for page in expected if page.rsplit('-', 1)[0] not in UNPICTURED}
    if SYSTEM == 'macos':
        pictured |= {f'disk-image-{theme}.png' for theme in themes}
    pictured |= {name for theme in themes for name in extra_pictures(theme)}
    found = {path.name for path in pages.glob('*.png')} - {'probe.png'}
    missing, extra = sorted(pictured - found), sorted(found - pictured)
    if missing or extra:
        raise RuntimeError(
            f'Page pictures missing: {", ".join(missing) or "none"}; '
            f'not a page of the walks: {", ".join(extra) or "none"}'
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--tools', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument(
        '--marker-only', type=Path, help='only build the marker installer; write its path here'
    )
    args = parser.parse_args()
    os.environ.pop('EDI_CODESIGN', None)  # the marker installer is never signed
    if args.marker_only:
        work = args.output.resolve()
        work.mkdir(parents=True)
        download = marker_installer(args.tools.resolve(), work)
        app = installer_from_download(download, work / 'unpacked')
        args.marker_only.write_text(f'{app}\n', encoding='utf-8')
        return
    capture(args.tools.resolve(), args.output)


if __name__ == '__main__':
    main()
