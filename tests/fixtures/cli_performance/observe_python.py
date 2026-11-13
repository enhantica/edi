"""Trace real setter calls and real operations; forward every call to shipped code."""

import json
import os
import sys
from pathlib import Path

import edi
from edi import __main__ as cli

events = []
for name, seed in [('_set_engine_threads', 5), ('_set_scan_workers', 7)]:
    real = getattr(cli._native, name)
    real(seed)

    def forward(value, actual=real, setting=name):
        actual(value)
        events.append({'kind': setting, 'value': value})

    setattr(cli._native, name, forward)

real_fit = cli._fit


def fit(project, **kwargs):
    events.append({'kind': 'fit'})
    return real_fit(project, **kwargs)


cli._fit = fit
real_calculate = edi.Analysis.calculate


def calculate(self):
    events.append({'kind': 'calc'})
    return real_calculate(self)


edi.Analysis.calculate = calculate
try:
    raise SystemExit(cli.main(sys.argv[1:]))
finally:
    Path(os.environ['EDI_CLI_PERFORMANCE_TRACE']).write_text(json.dumps(events), encoding='utf-8')
