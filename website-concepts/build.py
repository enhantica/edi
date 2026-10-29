# SPDX-License-Identifier: BSD-3-Clause
"""Build the public-website design alternatives without the native edi toolchain."""

from __future__ import annotations

import argparse
import importlib.metadata
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
CONCEPTS = {
    'surfaces': (
        'Choose your interface',
        'Application, Python and CLI have their own top-level sections.',
    ),
    'workflows': (
        'Follow your workflow',
        'Shared guides explain the science; interface tabs show how to do it.',
    ),
}


def _check_links(root: Path, base_url: str | None) -> None:
    prefix = urlsplit(base_url).path.rstrip('/') if base_url else ''
    errors = []

    class Links(HTMLParser):
        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag not in {'a', 'img', 'script', 'link'}:
                return
            for key, value in attrs:
                if key not in {'href', 'src'} or not value:
                    continue
                parsed = urlsplit(value)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                path = unquote(parsed.path)
                if path.startswith('/'):
                    if prefix and path.startswith(prefix + '/'):
                        path = path[len(prefix) :]
                    target = root / path.lstrip('/')
                else:
                    target = self.file.parent / path
                target = target.resolve()
                if target.is_dir():
                    target /= 'index.html'
                if not target.is_relative_to(root) or not target.is_file():
                    errors.append(f'{self.file.relative_to(root)}: {value}')

    for file in root.rglob('*.html'):
        parser = Links()
        parser.file = file
        parser.feed(file.read_text(encoding='utf-8'))
    if errors:
        raise SystemExit('Broken generated links/assets:\n' + '\n'.join(errors[:10]))
    print('Generated internal links and assets: PASS', flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('concept', choices=[*CONCEPTS, 'all'], nargs='?', default='all')
    parser.add_argument('--base-url', help='Public site root, including the repository URL prefix')
    args = parser.parse_args()
    if args.base_url:
        parsed = urlsplit(args.base_url)
        if (
            parsed.scheme not in {'http', 'https'}
            or not parsed.netloc
            or parsed.query
            or parsed.fragment
        ):
            parser.error('--base-url must be an HTTP(S) URL without a query or fragment')
        args.base_url = args.base_url.rstrip('/') + '/'
    version = importlib.metadata.version('zensical')
    if version != '0.0.73':
        raise SystemExit(f'Expected Zensical 0.0.73; found {version}. Install requirements.txt.')
    names = list(CONCEPTS) if args.concept == 'all' else [args.concept]
    for name in names:
        config = ROOT / name / 'mkdocs.yml'
        temporary = None
        if args.base_url:
            text, count = re.subn(
                r'^site_url:.*$',
                f'site_url: {args.base_url}{name}/',
                config.read_text(encoding='utf-8'),
                flags=re.MULTILINE,
            )
            if count != 1:
                raise SystemExit(f'{name}: expected exactly one site_url setting')
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=config.parent,
                prefix='.preview-',
                suffix='.yml',
                encoding='utf-8',
                delete=False,
            ) as stream:
                stream.write(text)
                temporary = Path(stream.name)
            config = temporary
        try:
            subprocess.run(
                [sys.executable, '-m', 'zensical', 'build', '--strict', '-f', str(config)],
                cwd=ROOT / name,
                check=True,
            )
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
        built = ROOT / name / 'site'
        if not (built / 'index.html').is_file():
            raise SystemExit(f'{name}: the build did not produce its homepage')
        assembled = ROOT / '_build' / name
        if assembled.exists():
            shutil.rmtree(assembled)
        shutil.copytree(built, assembled)
    cards = ''.join(
        f'<a class="concept" href="{name}/"><span>CONCEPT {label}</span>'
        f'<h2>{title}</h2><p>{description}</p><b>Explore concept →</b></a>'
        for label, (name, (title, description)) in zip(('A', 'B'), CONCEPTS.items(), strict=True)
    )
    output = ROOT / '_build'
    output.mkdir(exist_ok=True)
    template = (ROOT / 'gallery.html').read_text(encoding='utf-8')
    (output / 'index.html').write_text(template.replace('{{cards}}', cards), encoding='utf-8')
    _check_links(output.resolve(), args.base_url)
    command = f'python -m http.server 8873 --bind 127.0.0.1 --directory {output}'
    print(f'Preview: {command}', flush=True)


if __name__ == '__main__':
    main()
