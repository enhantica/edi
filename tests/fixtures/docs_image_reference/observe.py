# SPDX-License-Identifier: BSD-3-Clause
"""Read real built-page images and computed CSS through a filesystem-only browser transport."""

import argparse
import json
import mimetypes
import os
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright


class ContentImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.present = False
        self.canonical = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'link' and values.get('rel') == 'canonical':
            self.canonical = values.get('href')
        if tag in {'main', 'article'}:
            self.depth += 1
        if self.depth and tag in {'img', 'image'}:
            self.present = True

    def handle_endtag(self, tag):
        if tag in {'main', 'article'}:
            self.depth = max(0, self.depth - 1)


OBSERVE = r"""() => {
    function rgba(css) {
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = 1;
        const context = canvas.getContext('2d');
        context.fillStyle = css;
        context.fillRect(0, 0, 1, 1);
        return [...context.getImageData(0, 0, 1, 1).data].map(v => v / 255);
    }
    function over(foreground, background) {
        return foreground.slice(0, 3).map((v, i) =>
            v * foreground[3] + background[i] * (1 - foreground[3]));
    }
    function pageBackground(element) {
        const parents = [];
        for (let p = element.closest('main') || document.body; p; p = p.parentElement)
            parents.push(p);
        let colour = [1, 1, 1];
        for (const p of parents.reverse())
            colour = over(rgba(getComputedStyle(p).backgroundColor), colour);
        return colour;
    }
    function path(element) {
        const steps = [];
        for (let p = element; p && p !== document.body; p = p.parentElement)
            steps.push(p.localName + ':' + [...p.parentElement.children].indexOf(p));
        return steps.reverse().join('/');
    }
    const selector = 'main img, article img, main svg image, article svg image';
    return [...document.querySelectorAll(selector)]
        .filter((element, index, all) => all.indexOf(element) === index)
        .filter(element => {
            for (let p = element; p; p = p.parentElement) {
                const current = getComputedStyle(p);
                if (current.display === 'none' || current.visibility === 'hidden' ||
                    Number(current.opacity) === 0) return false;
            }
            return true;
        }).map(element => {
            const svg = element.closest('svg');
            const container = element.closest('figure') || element.closest('picture') ||
                svg || element.parentElement;
            const key = path(container) + '|' + (element.getAttribute('alt') || '');
            const raw = element.currentSrc || element.getAttribute('src') ||
                element.getAttribute('href') ||
                element.getAttributeNS('http://www.w3.org/1999/xlink', 'href');
            const source = raw ? new URL(raw, document.baseURI).href : '';
            const background = pageBackground(element);
            const frame = svg && svg.querySelector('.gui-image-frame');
            let border = [0, 0, 0, 0], width = 0;
            if (frame) {
                const style = getComputedStyle(frame);
                border = rgba(style.stroke);
                border[3] *= Number(style.strokeOpacity) * Number(style.opacity);
                width = parseFloat(style.strokeWidth);
            } else {
                for (let p = element; p && p.localName !== 'article'; p = p.parentElement) {
                    const style = getComputedStyle(p);
                    if (parseFloat(style.borderTopWidth) > 0 &&
                        style.borderTopStyle !== 'none') {
                        border = rgba(style.borderTopColor);
                        width = parseFloat(style.borderTopWidth);
                        break;
                    }
                }
            }
            return {key, source, page: background, border: over(border, background),
                borderAlpha: border[3], borderWidth: width,
                loaded: element.localName === 'image' ||
                    (element.complete && element.naturalWidth > 0)};
        });
}"""


def local_route(site, prefix, route):
    url = urlparse(route.request.url)
    if url.hostname != 'docs.invalid':
        route.abort()
        return
    if not url.path.startswith(prefix):
        route.abort()
        return
    target = (site / unquote(url.path[len(prefix) :])).resolve()
    if not target.is_relative_to(site):
        route.abort()
        return
    if target.is_dir():
        target /= 'index.html'
    if not target.is_file():
        route.fulfill(status=404, body='Missing local site resource')
        return
    route.fulfill(
        status=200,
        body=target.read_bytes(),
        content_type=mimetypes.guess_type(target.name)[0] or 'application/octet-stream',
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    site = args.site.resolve(strict=True)
    print('Reading built documentation images with a local browser transport', flush=True)
    root_reader = ContentImages()
    root_reader.feed((site / 'index.html').read_text(encoding='utf-8'))
    prefix = urlparse(root_reader.canonical or '/').path
    if prefix.endswith('index.html'):
        prefix = prefix.removesuffix('index.html')
    if not prefix.endswith('/'):
        prefix += '/'
    documents = []
    for path in sorted(site.rglob('*.html')):
        relative = path.relative_to(site)
        if relative.parts[0] in {'assets', 'webapp'}:
            continue
        reader = ContentImages()
        reader.feed(path.read_text(encoding='utf-8'))
        if reader.present:
            documents.append(relative.as_posix())
    result = {'pages': documents, 'images': [], 'transport': 'local files only', 'prefix': prefix}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get('BROWSER_EXECUTABLE'),
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-background-networking',
                '--host-resolver-rules=MAP * ~NOTFOUND',
            ],
        )
        for theme, scheme in [('light', 'default'), ('dark', 'slate')]:
            context = browser.new_context(
                color_scheme=theme, viewport={'width': 1440, 'height': 1100}
            )

            context.route('**/*', lambda route: local_route(site, prefix, route))
            page = context.new_page()
            for document in documents:
                page.goto('https://docs.invalid' + prefix + document, wait_until='load')
                page.evaluate(
                    r"""scheme => {
                    const selector = 'input[type=radio][data-md-color-scheme="' + scheme + '"]';
                    const input = document.querySelector(selector);
                    if (input) input.click();
                    for (const image of document.images) image.loading = 'eager';
                    const detailsElements = document.querySelectorAll(
                        'main details, article details');
                    for (const details of detailsElements)
                        if (!details.open) details.querySelector('summary')?.click();
                }""",
                    scheme,
                )
                page.wait_for_function(
                    '(scheme) => document.body.dataset.mdColorScheme === scheme',
                    arg=scheme,
                    timeout=2000,
                )
                tabs = page.evaluate("""() => [...document.querySelectorAll(
                    '.md-content .tabbed-labels label')].map(label => label.htmlFor)""")
                for selected in [None, *tabs]:
                    if selected:
                        page.evaluate(
                            r"""id => {
                            const selector = 'label[for="' + CSS.escape(id) + '"]';
                            const label = document.querySelector(selector);
                            const ancestors = [];
                            for (let p = label.parentElement; p; p = p.parentElement)
                                if (p.classList.contains('tabbed-block')) ancestors.push(p);
                            for (const block of ancestors.reverse()) {
                                const index = [...block.parentElement.children].indexOf(block);
                                const set = block.parentElement.parentElement;
                                const inputs = set.querySelectorAll(':scope > input[type=radio]');
                                inputs[index]?.click();
                            }
                            label.click();
                        }""",
                            selected,
                        )
                    page.evaluate("""() => new Promise(resolve =>
                        requestAnimationFrame(() => requestAnimationFrame(resolve)))""")
                    page.wait_for_function(
                        """() => [...document.querySelectorAll(
                        'main img, article img')].filter(image =>
                        getComputedStyle(image).display !== 'none')
                        .every(image => image.complete)""",
                        timeout=3000,
                    )
                    rows = page.evaluate(OBSERVE)
                    result['images'].extend(
                        {**row, 'document': document, 'theme': theme} for row in rows
                    )
                print('Observed', theme, document, flush=True)
            context.close()
        browser.close()
    args.output.write_text(json.dumps(result), encoding='utf-8')


if __name__ == '__main__':
    main()
