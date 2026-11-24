# SPDX-License-Identifier: BSD-3-Clause
"""Capture every page of the installer and its maintenance tool, in light and in dark.

Builds the small marker installer the protocol check uses (no app build), then runs it with the
pages saving themselves (Installer.qs, EDI_INSTALLER_CAPTURE) and moving on: on Windows and macOS
once per theme with the system's own appearance set, on Linux in light only. --marker-only builds
the marker installer and prints its path, for the macOS accessibility check (a11y-check.sh).
After each install the installed maintenance tool runs the same way, then the installation is
removed. The PNGs go to --output for a run artifact; nothing is committed.

The walks write every page they show to pages/pages.log, in order (Installer.qs). The run fails
unless that list is exactly the expected (page, mode, theme) sequence and each page that has a
picture has one: no page missing, none extra. What each maintenance mode did is checked on disk.
"""

import argparse
import json
import os
import plistlib
import re
import subprocess
import tempfile
import threading
import time
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
                ['powershell', '-NoProfile', '-Command', SCREEN.format(file=scratch)],
                capture_output=True, timeout=60, check=False,
            )  # fmt: skip
            if scratch.exists():
                pictured = before.rsplit('-', 1)[0] not in UNPICTURED
                if before and pictured and before == current_page(self.pages):
                    scratch.replace(self.pages / f'{before}.png')
                else:
                    scratch.unlink()


def run_pages(
    command: list, env: dict, log: Path, pages: Path | None = None, allowed: tuple = (0,)
) -> None:
    """Run a wizard whose pages move on by themselves; it ends at its last page."""
    frames = ScreenFrames(pages, log.stem) if SYSTEM == 'windows' and pages else None
    if frames:
        frames.start()
    try:
        _run_wizard(command, env, log, allowed)
    finally:
        if frames:
            frames.done.set()
            frames.join(timeout=90)


def _run_wizard(command: list, env: dict, log: Path, allowed: tuple = (0,)) -> None:
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run(
            # On Windows the wizard stays attached, and logs, only with --verbose.
            [*command, '--verbose'] if SYSTEM == 'windows' else command,
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=240, check=False,
        )  # fmt: skip
        stream.write(f'\nexit {result.returncode}\n')
    if result.returncode not in allowed:
        raise RuntimeError(f'{command[0]} ended with {result.returncode}; its log is {log}')
    # On Windows the wizard can return at once and go on in a process of its own: wait for it.
    deadline = time.monotonic() + 240
    image = Path(command[0]).name
    while SYSTEM == 'windows' and running(image):
        if time.monotonic() > deadline:
            raise RuntimeError(f'{image} still runs after 240 s')
        time.sleep(2)


SCREEN = (
    'Add-Type -AssemblyName System.Windows.Forms,System.Drawing; '
    '$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; '
    '$i=New-Object System.Drawing.Bitmap $b.Width,$b.Height; '
    '$g=[System.Drawing.Graphics]::FromImage($i); '
    '$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); '
    "$i.Save('{file}')"
)


def probe_screen(pages: Path, output: Path) -> None:
    """Whether this Windows session can take a screenshot at all, written to screen-probe.log."""
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', SCREEN.format(file=pages / 'probe.png')],
        capture_output=True, text=True, timeout=60, check=False,
    )  # fmt: skip
    (output / 'screen-probe.log').write_text(
        f'exit {result.returncode}\n{result.stdout}\n{result.stderr}', encoding='utf-8'
    )


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
    mounted = [e['dev-entry'] for e in entities if e.get('mount-point') == str(mount)]
    if len(mounted) != 1:
        raise RuntimeError(f'hdiutil did not mount {image} at {mount}: {entities}')
    # The whole image's device (/dev/diskN), not only its volume's slice.
    device = re.match(r'/dev/disk\d+', mounted[0]).group(0)
    try:
        subprocess.run(['open', str(mount)], check=True, timeout=60)
        time.sleep(4)
        subprocess.run(
            ['screencapture', '-x', str(pages / f'disk-image-{theme}.png')], check=True, timeout=60
        )
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
        package_app(stage, tools, work / 'offline', '2026.11.0')
    app = stage / APP_MARKER
    app.write_text('updated marker\n')
    package_app(stage, tools, work / 'online', '2026.11.1', repository)
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
    # Linux cannot be given a dark palette here, so light only; Windows and macOS set their own.
    themes = ('light',) if SYSTEM == 'linux' else ('light', 'dark')
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
            [str(installer), f'TargetDir={target}'], env, output / f'installer-{theme}.log', pages
        )
        maintenance = target / (
            'MaintenanceTool.app/Contents/MacOS/MaintenanceTool'
            if SYSTEM == 'macos'
            else 'MaintenanceTool' + SUFFIX
        )
        if not maintenance.exists():
            raise RuntimeError(f'The installer left no maintenance tool in {target}')
        app = target / APP_MARKER
        assistant = target / ASSISTANT_RUNTIME / 'assistant.txt'
        if app.read_text(encoding='utf-8') != 'marker\n' or assistant.exists():
            raise RuntimeError(
                f'The capture installation is not the first version alone: {target}'
            )
        # Each maintenance mode in turn; removing everything comes last.
        for mode in ('add', 'update', 'remove'):
            run_pages(
                [str(maintenance)],
                env | {'EDI_INSTALLER_MAINTENANCE_MODE': mode},
                output / f'maintenance-{mode}-{theme}.log',
                pages,
                # A tool that updated itself hands over to its restart (1) or the walk closes it
                # (3); require_pages still demands its pages.
                allowed=(0, 1, 3),
            )
            check_maintenance(mode, target, app, assistant, maintenance)
        if maintenance.exists():  # the captured run removes the installation; this is the backstop
            subprocess.run(
                [str(maintenance), '--confirm-command', '--default-answer', 'purge'],
                env={k: v for k, v in env.items() if k != 'EDI_INSTALLER_CAPTURE'},
                timeout=240,
                check=False,
            )
    if SYSTEM == 'macos':
        set_macos_theme('light')
    require_pages(pages, themes)
    print(f'{len(list(pages.glob("*.png")))} page captures in {pages}')


def check_maintenance(
    mode: str, target: Path, app: Path, assistant: Path, maintenance: Path
) -> None:
    """What a maintenance mode did to the installation, read from disk, not from its pages."""
    if mode == 'add' and not (
        assistant.exists()
        and assistant.read_text(encoding='utf-8') == 'optional assistant marker\n'
    ):
        raise RuntimeError('Adding components did not install the assistant')
    if mode == 'update' and not (
        app.exists() and app.read_text(encoding='utf-8') == 'updated marker\n'
    ):
        raise RuntimeError('Updating did not install the newer version')
    if mode == 'remove' and (app.exists() or assistant.exists() or maintenance.exists()):
        raise RuntimeError(f'Removing left the installation behind in {target}')


# Every page each walk shows, in order. The installer passes its welcome and summary pages by
# itself and takes no picture of them; every other page has one.
WALKS = {
    'installer': [
        'Introduction',
        'TargetDirectory',
        'ReadyForInstallation',
        'PerformInstallation',
        'Finished',
    ],
    'maintenance-add': [
        'Introduction',
        'AssistantForm',
        'ReadyForInstallation',
        'PerformInstallation',
        'Finished',
    ],
    'maintenance-update': [
        'Introduction',
        'ReadyForInstallation',
        'PerformInstallation',
        'Finished',
    ],
    'maintenance-remove': [
        'Introduction',
        'ReadyForInstallation',
        'PerformInstallation',
        'Finished',
    ],
}
UNPICTURED = {'installer-Introduction', 'installer-ReadyForInstallation'}


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
