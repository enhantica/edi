"""Read the browser model actually embedded by the public report HTML writer."""

import copy
import json
from html.parser import HTMLParser
from pathlib import Path

from tests.fixtures.native_ui_script.runner import run_javascript


class EmbeddedModel(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.active = False
        self.parts = []
        self.matches = 0

    def handle_starttag(self, tag, attrs):
        self.active = tag == 'script' and dict(attrs).get('id') == 'edi-report-model'
        self.matches += int(self.active)

    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


def browser_model(document):
    # Inputs remain independently authored. Browser layout/camera projection is
    # implementation data consumed by the actual renderer, never an oracle.
    result = run_javascript(
        '__nativeOutput.push(__nativeFixture.reportDocument('
        + json.dumps(json.dumps(document, ensure_ascii=False, allow_nan=False))
        + '));',
        timeout=10,
    )
    if result.returncode:
        raise AssertionError('The actual public report HTML writer must execute: ' + result.stderr)
    parser = EmbeddedModel()
    parser.feed(result.stdout)
    if parser.matches != 1:
        raise AssertionError('The delivered HTML must contain exactly one browser model')
    return json.loads(''.join(parser.parts))


def complete_schema(authored):
    """Supply schema-only fields for the old partial browser fixture.

    The committed seed is a labelled schema fixture. Authored fields and array
    membership always take priority; it supplies no expected renderer outputs.
    """
    seed = json.loads(
        (
            Path(__file__).resolve().parents[1] / 'report_integer_domain/schema-seed.json'
        ).read_text()
    )

    def fill(value, template):
        if isinstance(value, dict) and isinstance(template, dict):
            return {
                key: fill(value[key], default) if key in value else copy.deepcopy(default)
                for key, default in template.items()
            } | {key: copy.deepcopy(item) for key, item in value.items() if key not in template}
        if isinstance(value, list) and isinstance(template, list) and template:
            return [fill(item, template[0]) for item in value]
        return copy.deepcopy(value)

    return fill(authored, seed)
