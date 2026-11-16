"""Pause only actual callback delivery so a PTY can resize before the real host renders."""

import sys

import edi
from edi import __main__ as cli

real_fit = edi.Analysis.fit


def fit(self, **kwargs):
    actual = kwargs.get('on_file_complete')

    def complete(record):
        sys.stderr.write('EDI_PROGRESS_BOUNDARY\n')
        sys.stderr.flush()
        if sys.stdin.readline().strip() != 'continue':
            raise RuntimeError('The real callback requires its PTY resize acknowledgement')
        if actual is not None:
            actual(record)

    kwargs['on_file_complete'] = complete
    return real_fit(self, **kwargs)


edi.Analysis.fit = fit
raise SystemExit(cli.main(sys.argv[1:]))
