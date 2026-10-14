"""Observe the public save facade after a real filesystem publication failure."""

import json
import sys

import edi

project = edi.Project.load(sys.argv[1])
try:
    if sys.argv[2] == 'save_html':
        project.report.save_html(sys.argv[3], offline=False)
    else:
        project.report.save()
except (OSError, RuntimeError, ValueError) as error:
    print(
        json.dumps({
            'failed': True,
            'error': str(error),
            'live': project.report.check(),
            'disk': edi.Project.load(sys.argv[1]).report.check(),
        })
    )
else:
    print(json.dumps({'failed': False}))
