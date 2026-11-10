#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Exercise the real homepage in Chromium or native Safari, with shared assertions."""

from __future__ import annotations

import argparse
import base64
import functools
import hashlib
import http.server
import json
import os
import threading
import time
from html.parser import HTMLParser
from pathlib import Path

# Each browser driver is optional: Playwright drives Chromium and Selenium drives Safari.
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
try:
    from selenium import webdriver
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.by import By
except ImportError:
    webdriver = ActionChains = By = None

ROOT = Path(__file__).resolve().parents[1]
STATE = "document.querySelector('[data-network-hero]')?.__pulseController?.snapshot()"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serve the built site without per-request terminal noise."""

    def log_message(self, *args: object) -> None:
        pass


class Browser:
    """Drive Chromium through Playwright or Safari through WebDriver with one interface."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.errors: list[str] = []
        if kind == 'safari':
            self.driver = webdriver.Safari()
            self.driver.set_script_timeout(15)
            self.version = self.driver.capabilities.get('browserVersion')
        else:
            self.playwright = sync_playwright().start()
            executable = os.environ.get('BROWSER_EXECUTABLE')
            self.browser = self.playwright.chromium.launch(
                executable_path=executable,
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
            )
            kwargs = {}
            self.context = self.browser.new_context(
                viewport={'width': 1440, 'height': 1000}, **kwargs
            )
            self.page = self.context.new_page()
            self.page.on('pageerror', lambda error: self.errors.append(str(error)))
            self.page.on(
                'response',
                lambda response: (
                    self.errors.append(f'HTTP {response.status}: {response.url}')
                    if '127.0.0.1' in response.url and response.status >= 400
                    else None
                ),
            )
            self.version = self.browser.version

    def execute(self, script: str, arg: object = None) -> object:
        if self.kind == 'safari':
            return self.driver.execute_script('const arg = arguments[0];\n' + script, arg)
        return self.page.evaluate('(arg) => {\n' + script + '\n}', arg)

    def goto(self, url: str) -> None:
        if self.kind == 'safari':
            self.driver.get(url)
        else:
            self.page.goto(url, wait_until='networkidle')

    def back(self) -> None:
        if self.kind == 'safari':
            self.driver.back()
        else:
            self.page.go_back(wait_until='networkidle')

    @staticmethod
    def wait(seconds: float = 0.2) -> None:
        time.sleep(seconds)

    def until(self, expression: str, timeout: float = 10) -> object:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.execute('return Boolean(' + expression + ');')
            if result:
                return result
            self.wait(0.05)
        details = self.execute(
            'return {state:'
            + STATE
            + ',nativeReduced:matchMedia("(prefers-reduced-motion: reduce)").matches};'
        )
        raise AssertionError('Timed out: ' + expression + ' ' + json.dumps(details))

    def viewport(self, width: int, height: int) -> None:
        if self.kind == 'safari':
            self.driver.set_window_rect(width=width, height=height)
        else:
            self.page.set_viewport_size({'width': width, 'height': height})
        self.wait()

    def hover(self, selector: str) -> None:
        if self.kind == 'safari':
            ActionChains(self.driver).move_to_element(
                self.driver.find_element(By.CSS_SELECTOR, selector)
            ).perform()
        else:
            self.page.locator(selector).hover()
        self.wait(0.2)

    def shot(self, path: Path) -> None:
        if self.kind == 'safari':
            path.write_bytes(base64.b64decode(self.driver.get_screenshot_as_base64()))
        else:
            self.page.screenshot(path=str(path))

    def close(self) -> None:
        if self.kind == 'safari':
            self.driver.quit()
        else:
            self.context.close()
            self.browser.close()
            self.playwright.stop()


class Artwork(HTMLParser):
    """Collect the path signatures of each group in the network artwork."""

    def __init__(self) -> None:
        super().__init__()
        self.group = None
        self.signatures = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == 'g':
            self.group = values.get('id')
        if tag == 'path' and self.group:
            self.signatures.append((
                self.group,
                values.get('d'),
                values.get('stroke'),
                values.get('stroke-opacity'),
            ))

    def handle_endtag(self, tag: str) -> None:
        if tag == 'g':
            self.group = None


def require(condition: object, message: object = 'Verification failed') -> None:
    if not condition:
        raise AssertionError(message)


def check_artwork() -> None:
    artwork = Artwork()
    artwork.feed((ROOT / 'surfaces/overrides/partials/network.svg').read_text())
    expected = json.loads((ROOT / 'checks/network-artwork.json').read_text())
    digest = hashlib.sha256(
        json.dumps(artwork.signatures, separators=(',', ':')).encode()
    ).hexdigest()
    require(
        digest == expected['approved_path_sha256'], 'Approved geometry/individual fades changed'
    )
    require(len(artwork.signatures) == 148)


FRAGMENTS = (
    r"""
const svg = document.querySelector('.network-linework');
const edges = [...svg.querySelectorAll(':scope > g:not([data-pulses]) > path')].map(p =>
  p.getAttribute('d').match(/[-+]?(?:\d*\.)?\d+(?:e[-+]?\d+)?/gi).map(Number));
function onEdge(x,y,e) {
  const [ax,ay,bx,by]=e, dx=bx-ax,dy=by-ay;
  const t=((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy);
  return t>=-.0001 && t<=1.0001 && Math.abs((x-ax)*dy-(y-ay)*dx)/Math.hypot(dx,dy)<.003;
}
for (const path of svg.querySelectorAll('[data-pulses] path:not([display=none])')) {
  const [x,y,xx,yy]=path.getAttribute('d').match(/[-+]?(?:\d*\.)?\d+(?:e[-+]?\d+)?/gi).map(Number);
"""
    '  if (!edges.some(e=>onEdge(x,y,e)&&onEdge(xx,yy,e))) '
    "throw Error('A trail cuts away from a mesh edge');\n"
    r"""  if (+path.getAttribute('stroke-opacity')>.6501) throw Error('Excessive pulse opacity');
  if (getComputedStyle(path).strokeLinecap!=='butt') throw Error('Round pulse caps');
}
const state = document.querySelector('[data-network-hero]').__pulseController.snapshot();
for (const pulse of state.pulses) {
  if (pulse.speed<280 || pulse.speed>840 || pulse.tailLength<57 || pulse.tailLength>74 ||
      pulse.life<6 || pulse.life>10) throw Error('Pulse settings outside owner-approved ranges');
  for (let i=1;i<pulse.route.length;i++) {
    const a=pulse.route[i-1],b=pulse.route[i];
    if (a.to.x!==b.from.x || a.to.y!==b.from.y) throw Error('Disconnected route');
  }
}
return state;
"""
)


def _check_layouts(browser: Browser, output: Path, results: list) -> None:
    for width, height in [(1440, 1000), (1920, 1080), (390, 844)]:
        browser.viewport(width, height)
        layout = browser.execute("""
const hero=document.querySelector('[data-network-hero]'), \
art=hero.querySelector('.network-linework');
const h=hero.getBoundingClientRect(), a=art.getBoundingClientRect();
const copy=document.querySelector('.ed-landing__copy').getBoundingClientRect();
const title=document.querySelector('.ed-landing__copy h1'), \
intro=document.querySelector('.ed-landing__intro');
const nav=document.querySelector('.ed-landing__interfaces');
const home=document.querySelector('.md-tabs__link'), range=document.createRange();
range.selectNodeContents(home);
const frame=document.querySelector('.ed-landing__preview'), image=frame.querySelector('img');
const f=frame.getBoundingClientRect(), i=image.getBoundingClientRect(), fs=getComputedStyle(frame);
return {width:innerWidth, heroWidth:h.width, \
overflow:document.documentElement.scrollWidth>innerWidth,
 aligned:Math.abs(copy.left-range.getBoundingClientRect().left)<1,
 bleed:f.right-document.documentElement.clientWidth,
 frame:{border:fs.borderTopColor,width:fs.borderTopWidth,\
radius:parseFloat(fs.borderTopLeftRadius),relativeRadius:fs.borderTopLeftRadius.includes('%'),\
crop:f.top+1-i.top,expectedCrop:i.width*62/2992},
 fullWidth:Math.abs(h.left)<1 && Math.abs(a.left)<1 && Math.abs(h.width-a.width)<1,
 textAbove:nav.getBoundingClientRect().bottom<title.getBoundingClientRect().top,
 introFits:intro.getBoundingClientRect().width<=title.getBoundingClientRect().width+.1,
 links:[...nav.querySelectorAll('a')].map(e=>({label:e.innerText.trim(),\
underline:getComputedStyle(e).textDecorationLine})),
 slots:hero.__pulseController.snapshot().pulses.length,
 transformMatched:['upper-bank','lower-bank'].every(id=>hero.querySelector('#'+id).getAttribute(\
'transform')===hero.querySelector('[data-pulse-bank="'+id+'"]').getAttribute('transform')),
 noControls:hero.querySelectorAll('[data-pulse-toggle]').length===0,
 pointFree:!art.querySelector('circle,ellipse,polygon'),
 banks:[...art.querySelectorAll(':scope > g:not([data-pulses])')].map(g=>{const \
m=g.getScreenCTM();return {x:Math.hypot(m.a,m.b),y:Math.hypot(m.c,m.d)}})};
""")
        require(
            not layout['overflow'] and layout['fullWidth'] and layout['textAbove'],
            layout,
        )
        if layout['width'] > 1280:
            require(layout['aligned'] and 0 < layout['bleed'] < 80, layout)
        frame = layout['frame']
        require(frame['border'] == 'rgb(229, 229, 229)' and frame['width'] == '1px', frame)
        require(
            frame['relativeRadius']
            and abs(frame['radius'] - 1.2) < 0.0001
            and abs(frame['crop'] - frame['expectedCrop']) < 0.2,
            frame,
        )
        require(
            layout['introFits']
            and layout['transformMatched']
            and layout['noControls']
            and layout['pointFree'],
            (
                "Failed: layout['introFits']\n            and layout['transformMatched']\n   "
                "         and layout['noControls']\n            and layo"
            ),
        )
        require(
            all(link['underline'] == 'none' for link in layout['links']),
            "Failed: all(link['underline'] == 'none' for link in layout['links'])",
        )
        require(
            layout['slots'] == (4 if layout['heroWidth'] <= 520 else 6),
            'Responsive spark count differs from the selected design',
        )
        require(
            all(abs(bank['x'] - bank['y']) < 0.001 for bank in layout['banks']), 'Distorted mesh'
        )
        results.append({'requested_width': width, 'layout': layout})
        browser.shot(output / f'{browser.kind}-{width}.png')


def _check_hover(browser: Browser) -> None:
    """Check that hovering a homepage button changes its colour but not its size."""
    browser.viewport(1440, 1000)
    for selector in [
        '.ed-landing__actions .md-button:not(.md-button--primary)',
        '.ed-landing__actions .md-button--primary',
    ]:
        browser.hover('.md-header .md-logo')
        normal = browser.execute(
            'const e=document.querySelector(arg),r=e.getBoundingClientRect(),'
            's=getComputedStyle(e);return {w:r.width,h:r.height,font:s.fontSize,'
            'weight:s.fontWeight,bg:s.backgroundColor,opacity:s.opacity};',
            selector,
        )
        browser.hover(selector)
        hover = browser.execute(
            'const e=document.querySelector(arg),r=e.getBoundingClientRect(),'
            's=getComputedStyle(e);return {w:r.width,h:r.height,font:s.fontSize,'
            'weight:s.fontWeight,bg:s.backgroundColor,opacity:s.opacity};',
            selector,
        )
        require(all(abs(normal[k] - hover[k]) < 0.05 for k in ['w', 'h']), (normal, hover))
        require(
            normal['font'] == hover['font'] and normal['weight'] == hover['weight'],
            "Failed: normal['font'] == hover['font'] and normal['weight'] == hover['weight']",
        )
        require(
            normal['bg'] != hover['bg'] or normal['opacity'] != hover['opacity'],
            "Failed: normal['bg'] != hover['bg'] or normal['opacity'] != hover['opacity']",
        )


def _check_motion(browser: Browser, initial: dict) -> None:
    browser.until(STATE + '.running')
    browser.wait(2.2)
    after = browser.execute(FRAGMENTS)
    for before_pulse, after_pulse in zip(initial['pulses'], after['pulses'], strict=True):
        if (
            not before_pulse['waiting']
            and not after_pulse['waiting']
            and after_pulse['age'] > before_pulse['age']
        ):
            require(
                after_pulse['currentSpeed'] == before_pulse['currentSpeed'],
                'Spark speed must stay constant through its run',
            )
    require(
        any(a['age'] != b['age'] for a, b in zip(after['pulses'], initial['pulses'], strict=True)),
        'Spark lifetimes must advance or restart while visible',
    )
    require(
        len({round(p['speed'], 4) for p in after['pulses']}) > 1,
        "Failed: len({round(p['speed'], 4) for p in after['pulses']}) > 1",
    )
    browser.execute(
        "const e=document.createElement('div'); e.id='check-spacer';"
        "e.style.height='200vh';document.body.append(e);window.scrollTo(0,"
        "document.querySelector('[data-network-hero]').offsetHeight+300);"
    )
    browser.until('!' + STATE + '.running')
    paused = browser.execute('return ' + STATE + ';')
    browser.wait(0.4)
    require(
        browser.execute('return ' + STATE + '.pulses[0].age;') == paused['pulses'][0]['age'],
        (
            "Failed: browser.execute('return ' + STATE + '.pulses[0].age;') == "
            "paused['pulses'][0]['age']"
        ),
    )
    browser.execute("window.scrollTo(0,0);document.getElementById('check-spacer').remove();")
    browser.until(STATE + '.running')
    # Simulate the visibility boundary; OS reduced motion is checked natively below.
    browser.execute(
        "Object.defineProperty(document,'hidden',{configurable:true,value:true});"
        "document.dispatchEvent(new Event('visibilitychange'));"
    )
    require(
        not browser.execute('return ' + STATE + '.running;'),
        "Failed: not browser.execute('return ' + STATE + '.running;')",
    )
    frozen = browser.execute('return ' + STATE + '.pulses[0].age;')
    browser.wait(0.3)
    require(
        browser.execute('return ' + STATE + '.pulses[0].age;') == frozen,
        "Failed: browser.execute('return ' + STATE + '.pulses[0].age;') == frozen",
    )
    browser.execute(
        "delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));"
    )
    browser.until(STATE + '.running')


def _check_lifecycle(browser: Browser, base: str, output: Path) -> None:
    """Check that the animation mounts once and stops when the page is hidden or left."""
    browser.execute('window.__ediNetworkMount();window.__ediNetworkMount();')
    require(
        browser.execute("return document.querySelectorAll('[data-pulses]').length;") == 1,
        (
            'Failed: browser.execute("return '
            "document.querySelectorAll('[data-pulses]').length;\") == 1"
        ),
    )
    browser.execute("window.dispatchEvent(new PageTransitionEvent('pagehide'));")
    require(
        browser.execute("return document.querySelectorAll('[data-pulses]').length;") == 0,
        (
            'Failed: browser.execute("return '
            "document.querySelectorAll('[data-pulses]').length;\") == 0"
        ),
    )
    browser.execute("window.dispatchEvent(new PageTransitionEvent('pageshow'));")
    browser.until(STATE)
    require(
        browser.execute("return document.querySelectorAll('[data-pulses]').length;") == 1,
        (
            'Failed: browser.execute("return '
            "document.querySelectorAll('[data-pulses]').length;\") == 1"
        ),
    )
    browser.execute(
        "window.__detachedHero=document.querySelector('[data-network-hero]');"
        'window.__detachedHero.remove();'
    )
    browser.until('!window.__detachedHero.__pulseController')
    require(
        browser.execute("return window.__detachedHero.querySelectorAll('[data-pulses]').length;")
        == 0,
        (
            'Failed: browser.execute("return '
            "window.__detachedHero.querySelectorAll('[data-pulses]').length;\")\n        == "
            '0'
        ),
    )
    browser.execute(
        "document.querySelector('.md-main__inner').prepend(window.__detachedHero);"
        'window.__ediNetworkMount();'
    )
    browser.until(STATE)
    browser.execute(
        'document.querySelector(\'.md-header [title="Switch to dark mode"]\')?.click();'
    )
    browser.wait(0.2)
    browser.shot(output / f'{browser.kind}-dark.png')
    browser.goto(base + 'user-guide/')
    require(
        browser.execute("return document.querySelectorAll('[data-pulses]').length;") == 0,
        (
            'Failed: browser.execute("return '
            "document.querySelectorAll('[data-pulses]').length;\") == 0"
        ),
    )
    browser.back()
    browser.until(STATE)
    require(
        browser.execute("return document.querySelectorAll('[data-pulses]').length;") == 1,
        (
            'Failed: browser.execute("return '
            "document.querySelectorAll('[data-pulses]').length;\") == 1"
        ),
    )


def _check_reduced_motion(browser: Browser, base: str, output: Path) -> None:
    print('Native reduced-motion preference and no-JavaScript fallback', flush=True)
    browser.page.emulate_media(reduced_motion='reduce')
    browser.until('!' + STATE + '.requestedPlaying')
    require(
        not browser.execute('return ' + STATE + '.framePending;'),
        "Failed: not browser.execute('return ' + STATE + '.framePending;')",
    )
    browser.page.reload(wait_until='networkidle')
    browser.until(STATE)
    require(
        not browser.execute('return ' + STATE + '.running;'),
        "Failed: not browser.execute('return ' + STATE + '.running;')",
    )
    browser.page.emulate_media(reduced_motion='no-preference')
    browser.until(STATE + '.running')
    static = browser.browser.new_context(
        java_script_enabled=False, viewport={'width': 390, 'height': 844}
    )
    page = static.new_page()
    page.goto(base, wait_until='networkidle')
    require(
        page.locator('.network-linework > g > path').count() == 148,
        "Failed: page.locator('.network-linework > g > path').count() == 148",
    )
    require(
        page.locator('[data-pulses]').count() == 0,
        "Failed: page.locator('[data-pulses]').count() == 0",
    )
    page.screenshot(path=str(output / 'chromium-no-js.png'))
    static.close()


def _record_motion(browser: Browser, base: str, output: Path) -> None:
    print('Recording integrated motion', flush=True)
    clip = browser.browser.new_context(
        viewport={'width': 1440, 'height': 1000},
        record_video_dir=str(output / 'video'),
        record_video_size={'width': 1440, 'height': 1000},
    )
    page = clip.new_page()
    page.goto(base, wait_until='networkidle')
    page.wait_for_function(
        'document.querySelector("[data-network-hero]").dataset.running === "true"'
    )
    page.wait_for_timeout(10000)
    clip.close()


def exercise(browser: Browser, base: str, output: Path, *, record: bool) -> dict:
    results = []
    browser.goto(base)
    browser.until(STATE)
    browser.wait(0.4)
    print('Homepage / layout / native hover', flush=True)
    browser.execute(
        'window.__networkErrors=[]; window.addEventListener("error",'
        'e=>window.__networkErrors.push(e.message));'
    )
    _check_layouts(browser, output, results)
    _check_hover(browser)
    print('Motion / route geometry / offscreen / visibility / lifecycle', flush=True)
    browser.hover('.md-header .md-logo')
    initial = browser.execute('return ' + STATE + ';')
    if not initial['reducedMotion']:
        _check_motion(browser, initial)
    _check_lifecycle(browser, base, output)
    if browser.kind == 'chromium':
        _check_reduced_motion(browser, base, output)
    require(
        not browser.execute('return window.__networkErrors || [];'),
        "Failed: not browser.execute('return window.__networkErrors || [];')",
    )
    require(not browser.errors, browser.errors)
    if record and browser.kind == 'chromium':
        _record_motion(browser, base, output)
    return {
        'browser': browser.kind,
        'version': browser.version,
        'checks': results,
        'motion_and_lifecycle': 'PASS',
        'errors': browser.errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'safari'], default='chromium')
    parser.add_argument('--output', type=Path, default=ROOT / '_build-checks/network-checks')
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    check_artwork()
    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / '_build'))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    browser = Browser(args.browser)
    try:
        report = exercise(
            browser, f'http://127.0.0.1:{server.server_port}/', args.output, record=args.record
        )
        (args.output / f'{args.browser}.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)
    finally:
        browser.close()
        server.shutdown()


if __name__ == '__main__':
    main()
