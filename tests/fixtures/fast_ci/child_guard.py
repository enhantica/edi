"""Observe Python helper launches in the child that actually launches the normal app."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


def install():
    root = Path(os.environ['EDI_GATE_ROOT'])
    spec = importlib.util.spec_from_file_location(
        'edi_gate_policy', root / 'tests/fixtures/fast_ci/policy.py'
    )
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    log = os.environ['EDI_GATE_PROCESS_LOG']

    def audit(event, args):
        if event not in {'subprocess.Popen', 'os.system', 'os.exec', 'os.spawn', 'os.posix_spawn'}:
            return
        argv = args[0] if event == 'os.system' else args[1]
        if isinstance(argv, bytes):
            argv = argv.decode()
        words = list(argv) if isinstance(argv, (tuple, list)) else policy.command_tokens(argv)
        blocked = policy.app_command(words)
        with Path(log).open('a', encoding='utf-8') as receipt:
            receipt.write(json.dumps({'argv': words, 'blocked': blocked}) + '\n')
        if blocked:
            message = 'A PR Python helper attempted a private app build before execution'
            raise RuntimeError(message)

    original = subprocess.Popen

    class ObservedPopen(original):
        def __init__(self, args, **kwargs):
            if (
                '--test-observer' in args
                and 'scan-screen' in args
                and os.environ.get('EDI_GATE_SETTINGS_ONLY') == '1'
            ):
                kwargs['env'] = {
                    **(kwargs.get('env') or os.environ),
                    'SCAN_SCREEN_SETTINGS_ONLY': '1',
                }
            super().__init__(args, **kwargs)

    subprocess.Popen = ObservedPopen
    original_run = subprocess.run

    def observed_run(args, **kwargs):
        result = original_run(args, **kwargs)
        if '--test-observer' in args and 'scan-screen' in args and os.environ.get('EDI_GATE_ONCE'):
            Path(os.environ['EDI_GATE_ONCE']).write_text(
                json.dumps({
                    'argv': list(args),
                    'returncode': result.returncode,
                }),
                encoding='utf-8',
            )
            # This gate observes reuse, not the nightly frame/scan population.
            # Stop only after an actual successful native request, never before launch.
            raise SystemExit(77)
        return result

    subprocess.run = observed_run
    sys.addaudithook(audit)
