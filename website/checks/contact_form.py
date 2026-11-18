"""Check the Get in touch form's attachments and answers in a browser, offline.

The page is the site's own: the form markup from about/community.md, assets/contact-form.js and
site-components.css, and assets/feedback-form.js written by build.py from the app's wording and
Payload.js. Requests never leave the page: fetch is replaced by a stub that answers as the feedback
service would. Runs with the browser toolchain the app's web checks use (EDI_WASM_TOOLCHAIN,
default ~/.cache/edi-wasm).
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'surfaces/docs'


def page(directory: Path) -> Path:
    """The test page, with the site's form, script, styles and the app's wording."""
    spec = importlib.util.spec_from_file_location('site_build', ROOT / 'build.py')
    build = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT))
    spec.loader.exec_module(build)
    (directory / 'assets').mkdir(parents=True)
    build._write_feedback_form(directory)
    for name in ('contact-form.js', 'site-components.css'):
        shutil.copy2(DOCS / 'assets' / name, directory / 'assets' / name)
    markdown = (DOCS / 'about/community.md').read_text(encoding='utf-8')
    form = re.search(r'<form class="ed-contact-form".*?</form>', markdown, flags=re.DOTALL).group(
        0
    )
    index = directory / 'index.html'
    index.write_text(
        '<!doctype html><html><head><meta charset="utf-8">'
        '<link rel="stylesheet" href="assets/site-components.css"></head>'
        f'<body><article class="md-typeset">{form}</article>'
        '<script src="assets/feedback-form.js"></script>'
        '<script src="assets/contact-form.js"></script>'
        '</body></html>',
        encoding='utf-8',
    )
    return index


def main() -> None:
    toolchain = Path(os.environ.get('EDI_WASM_TOOLCHAIN', str(Path.home() / '.cache/edi-wasm')))
    nodes = sorted((toolchain / 'emsdk-4.0.7/node').glob('*/bin/node'))
    browsers = sorted(
        toolchain.glob(
            'chrome-*/chrome-headless-shell/*/chrome-headless-shell-linux64/chrome-headless-shell'
        )
    )
    if len(nodes) != 1 or not browsers:
        raise SystemExit(
            'contact_form: the browser toolchain (node and chrome-headless-shell) is missing'
        )
    with tempfile.TemporaryDirectory() as scratch:
        index = page(Path(scratch))
        subprocess.run(
            [
                str(nodes[0]),
                str(Path(__file__).with_name('contact_form_browser.mjs')),
                index.as_uri(),
                str(browsers[-1]),
                str(toolchain / 'playwright/node_modules/playwright-core/index.mjs'),
            ],
            check=True,
            timeout=120,
        )


if __name__ == '__main__':
    main()
