# SPDX-License-Identifier: BSD-3-Clause
"""Prepare the SmartScreen file submission for a published release (edi ADR-0091).

Microsoft has no submission API for developers, so a person submits the Windows online installer
by hand while a fresh download still shows the SmartScreen warning. This finds that installer among
the release's files (the .exe itself, or inside the ZIP of releases before single-file installers),
copies it with the text to paste into `--output`, and returns the steps as Markdown for the run's
summary. Nothing here may stop a release: the caller only warns when it fails.
"""

import argparse
import json
import os
import shutil
import zipfile
from pathlib import Path

FORM = 'https://www.microsoft.com/en-us/wdsi/filesubmission'


def find_installer(assets: Path, version: str, output: Path) -> Path:
    """The Windows online installer in `output`: copied, or taken out of its ZIP."""
    stem = f'EasyDiffraction-Installer-{version}-Windows-x64'
    executable = assets / f'{stem}.exe'
    output.mkdir(parents=True, exist_ok=True)
    if executable.is_file():
        return Path(shutil.copy2(executable, output / executable.name))
    archive = assets / f'{stem}.zip'
    if archive.is_file():
        with zipfile.ZipFile(archive) as zipped:
            names = [
                name for name in zipped.namelist() if name.endswith('.exe') and '/' not in name
            ]
            if len(names) != 1:
                raise RuntimeError(f'{archive.name} holds no single installer .exe')
            target = output / names[0]
            target.write_bytes(zipped.read(names[0]))
            return target
    raise RuntimeError(f'the release has no {stem}.exe or .zip')


def information(version: str, repo: str, installer: Path) -> str:
    sentences = [
        f'EasyDiffraction {version}, a free, open-source diffraction data analysis application',
        'from the European Spallation Source ERIC (Lund, Sweden). This is its signed Windows',
        'online installer,',
        f'published at https://github.com/{repo}/releases/tag/v{version}; the source is',
        f'https://github.com/{repo}. The installer is signed by European Spallation Source ERIC',
        'through DigiCert. SmartScreen shows the unrecognized-app warning because the',
        f'code-signing certificate is new and has no reputation yet. File: {installer.name}.',
    ]
    return ' '.join(sentences) + '\n'


def steps(version: str, installer: Path, text: str) -> str:
    """The submission steps for the run's summary page."""
    fields = [
        ('Product', 'Microsoft Defender Smartscreen'),
        ('Company name', 'European Spallation Source ERIC'),
        ('What do you believe this file is?', 'Incorrectly detected as malware/malicious'),
        ('Detection name', 'SmartScreen: unrecognized app'),
        ('File', f'{installer.name} (the artifact smartscreen-submission of this run)'),
    ]
    rows = '\n'.join(f'| {name} | {value} |' for name, value in fields)
    return (
        f'## SmartScreen submission for EasyDiffraction {version}\n\n'
        'Submit **only while a fresh download of the installer still shows the "Windows '
        'protected your PC" warning**; once it is gone, there is nothing to submit.\n\n'
        f'1. Download the artifact **smartscreen-submission** of this run and unzip it.\n'
        f'2. Open {FORM} and sign in as a software developer.\n'
        '3. Fill in the form:\n\n'
        '| Field | Value |\n| --- | --- |\n'
        f'{rows}\n\n'
        '4. Paste into "Additional information":\n\n'
        f'```\n{text}```\n'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--publication', type=Path, required=True)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    release = json.loads((args.publication / 'release.json').read_text(encoding='utf-8'))
    version = release['version']
    installer = find_installer(args.publication / 'assets', version, args.output)
    text = information(version, args.repo, installer)
    (args.output / 'additional-information.txt').write_text(text, encoding='utf-8')
    summary = steps(version, installer, text)
    target = os.environ.get('GITHUB_STEP_SUMMARY')
    if target:
        with Path(target).open('a', encoding='utf-8') as stream:
            stream.write(summary)
    print(summary)


if __name__ == '__main__':
    main()
