"""Real model-to-HTML text embedding, including an attempted script-content escape."""

import json
from html.parser import HTMLParser
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = json.loads((ROOT / 'tests/fixtures/report_units/reference.json').read_text())


class Contents(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.model = None
        self.current = None
        self.heading = None
        self.headings = []
        self.script_count = 0

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == 'script':
            self.script_count += 1
            if attributes.get('id') == 'edi-report-model':
                assert attributes.get('type') == 'application/json', (
                    'The report model element must be inert application/json script content'
                )
                self.current = []
        if tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.heading = []

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)
        if self.heading is not None:
            self.heading.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.current is not None:
            self.model = ''.join(self.current)
            self.current = None
        if tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'} and self.heading is not None:
            self.headings.append(''.join(self.heading))
            self.heading = None


@pytest.mark.parametrize(
    'title', [REFERENCE['hostile_title'], '\U0001d6c2 & "quotes" and \'apostrophe\'']
)
def test_html_embeds_json_without_script_or_entity_injection(title):
    project = edi.Project(name='literal_report')
    assert hasattr(project, 'report'), (
        'The real report writer must be available through Project.report'
    )
    project.metadata.title = title
    html = project.report.as_html(offline=False)
    contents = Contents()
    contents.feed(html)
    assert contents.model is not None, (
        'The HTML must carry the actual versioned report model element'
    )
    assert not any(char in contents.model for char in '<>&\u2028\u2029'), (
        'Inline JSON must escape HTML syntax and both Unicode script-content separators'
    )
    assert json.loads(contents.model)['project']['title'] == title, (
        'Parsing the escaped JSON must recover every byte of the original project title'
    )
    assert any(title in heading for heading in contents.headings), (
        'The rendered heading must show project text literally through HTML entity escaping'
    )
    assert '<script>alert(1)</script>' not in html, (
        'A project title must never escape its text position to create an executable script'
    )
