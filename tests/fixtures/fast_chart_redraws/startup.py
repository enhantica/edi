"""Separate the declared startup renderer report from application diagnostics."""

import re

from tests.fixtures.fast_chart_redraws.timing import backend_identity

_REPORT = re.compile(
    r'edi: graphics: (?P<api>[A-Za-z][A-Za-z0-9 ]*)'
    r'(?:, renderer (?P<renderer>[^\r\n]+))?, '
    r'(?P<classification>software rendering \(no GPU\)|hardware rendering)'
)


def split_renderer_reports(output):
    """Recognise complete report lines; preserve every other byte as a diagnostic."""
    reports, diagnostics = [], []
    for line in output.splitlines(keepends=True):
        match = _REPORT.fullmatch(line.removesuffix('\n').removesuffix('\r'))
        if match:
            api, renderer = match['api'], match['renderer'] or ''
            try:
                observed = backend_identity({'api': api, 'renderer': renderer})
            except (TypeError, ValueError):
                observed = None
            software = match['classification'] == 'software rendering (no GPU)'
            complete_fields = (
                api == api.strip()
                and renderer == renderer.strip()
                and (api == 'OpenGL' or not renderer)
            )
            if observed is not None and complete_fields and observed['software'] == software:
                reports.append({'api': api, 'renderer': renderer, 'software': software})
                continue
        diagnostics.append(line)
    return reports, ''.join(diagnostics)
