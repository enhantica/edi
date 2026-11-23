# SPDX-License-Identifier: BSD-3-Clause
"""Capture every page of the installer and its maintenance tool, in light and in dark.

Builds the small marker installer the protocol check uses (no app build), then runs it with the
pages saving themselves (Installer.qs, EDI_INSTALLER_CAPTURE) and moving on: on Windows and macOS
once per theme with the system's own appearance set, on Linux in light only. --marker-only builds
the marker installer and prints its path, for the macOS accessibility check (a11y-check.sh).
After each install the installed maintenance tool runs the same way, then the installation is
removed. The PNGs go to --output for a run artifact; nothing is committed.
"""

import argparse
import json
import os
import subprocess
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


def marker_stage(root: Path) -> Path:
    stage = root / 'marker-stage'
    app = stage / (
        'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
        if SYSTEM == 'macos'
        else 'bin/EasyDiffraction' + SUFFIX
    )
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


class ScreenFrames(threading.Thread):
    """Windows: a screenshot about every second while a wizard runs, kept when it changed.

    A process the wizard starts cannot take one there, so the pages are captured from here; each
    page shows for 2.5 s (Installer.qs) and so appears in at least one frame.
    """

    def __init__(self, pages: Path, prefix: str) -> None:
        super().__init__(daemon=True)
        self.pages, self.prefix, self.done, self.count = pages, prefix, threading.Event(), 0

    def run(self) -> None:
        last = b''
        scratch = self.pages / f'{self.prefix}-scratch.png'
        while not self.done.is_set():
            subprocess.run(
                ['powershell', '-NoProfile', '-Command', SCREEN.format(file=scratch)],
                capture_output=True, timeout=60, check=False,
            )  # fmt: skip
            if scratch.exists():
                data = scratch.read_bytes()
                if data != last:
                    self.count += 1
                    (self.pages / f'{self.prefix}-{self.count:02d}.png').write_bytes(data)
                    last = data
                scratch.unlink()


def run_pages(command: list, env: dict, log: Path, pages: Path | None = None) -> None:
    """Run a wizard whose pages move on by themselves; it ends at its last page."""
    frames = ScreenFrames(pages, log.stem) if SYSTEM == 'windows' and pages else None
    if frames:
        frames.start()
    try:
        _run_wizard(command, env, log)
    finally:
        if frames:
            frames.done.set()
            frames.join(timeout=90)


def _run_wizard(command: list, env: dict, log: Path) -> None:
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run(
            # On Windows the wizard stays attached, and logs, only with --verbose.
            [*command, '--verbose'] if SYSTEM == 'windows' else command,
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=240, check=False,
        )  # fmt: skip
        stream.write(f'\nexit {result.returncode}\n')
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
    """The system appearance, read by each app as it starts."""
    if theme == 'dark':
        subprocess.run(['defaults', 'write', '-g', 'AppleInterfaceStyle', 'Dark'], check=True)
    else:
        subprocess.run(['defaults', 'delete', '-g', 'AppleInterfaceStyle'], check=False)


def marker_installer(tools: Path, work: Path) -> Path:
    """The offline marker installer's download."""
    repository = (work / 'repository-unused').as_uri() + '/'
    with patch('package.repository_urls', return_value=(repository,)):
        package_app(marker_stage(work), tools, work / 'offline', '2026.11.0')
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
    for theme in ('light',) if SYSTEM == 'linux' else ('light', 'dark'):
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
        if 'DISPLAY' in os.environ:
            env['DISPLAY'] = os.environ['DISPLAY']
        installer = installer_command(
            installer_from_download(download, work / f'unpacked-{theme}')
        )
        run_pages([str(installer)], env, output / f'installer-{theme}.log', pages)
        target = home / 'EasyDiffraction'
        if SYSTEM == 'windows':
            # Program Files with administrator rights (the runner has them), else the user's.
            candidates = [
                Path(os.environ.get('PROGRAMFILES', r'C:\Program Files')) / 'EasyDiffraction',
                Path(env.get('LOCALAPPDATA', str(home))) / 'Programs/EasyDiffraction',
            ]
            target = next((path for path in candidates if path.exists()), candidates[0])
        elif SYSTEM == 'macos':
            target = Path('/Applications/EasyDiffraction')
        maintenance = target / (
            'MaintenanceTool.app/Contents/MacOS/MaintenanceTool'
            if SYSTEM == 'macos'
            else 'MaintenanceTool' + SUFFIX
        )
        if maintenance.exists():
            run_pages([str(maintenance)], env, output / f'maintenance-{theme}.log', pages)
        if maintenance.exists():  # the captured run removes the installation; this is the backstop
            subprocess.run(
                [str(maintenance), '--confirm-command', '--default-answer', 'purge'],
                env={k: v for k, v in env.items() if k != 'EDI_INSTALLER_CAPTURE'},
                timeout=240,
                check=False,
            )
    if SYSTEM == 'macos':
        set_macos_theme('light')
    print(f'{len(list(pages.glob("*.png")))} page captures in {pages}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--tools', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--marker-only', action='store_true')
    args = parser.parse_args()
    os.environ.pop('EDI_CODESIGN', None)  # the marker installer is never signed
    if args.marker_only:
        work = args.output.resolve()
        work.mkdir(parents=True)
        print(
            installer_from_download(
                marker_installer(args.tools.resolve(), work), work / 'unpacked'
            )
        )
        return
    capture(args.tools.resolve(), args.output)


if __name__ == '__main__':
    main()
