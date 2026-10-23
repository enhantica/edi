"""Replay the actual shard selector with pytest replaced by an argument receipt."""

import json
import os
import shutil
import subprocess
import sys

from tests.fixtures.e09_t75_workflow import active


def shard_selection(root, scratch, event, platform, workflow, *, core_only=False):
    scripts = scratch / 'tools/ci'
    scripts.mkdir(parents=True)
    shutil.copy2(root / 'tools/ci/system-tests-part.sh', scripts)
    tests = scratch / 'tests'
    tests.mkdir()
    shutil.copy2(root / 'tests/test-groups.json', tests)
    binary = scratch / 'bin'
    binary.mkdir()
    python = binary / 'python'
    python.write_text(
        '#!' + sys.executable + '\nimport json, os, pathlib, sys\n'
        'if sys.argv[1:3] == ["-m", "pytest"]:\n'
        ' target=pathlib.Path(os.environ["PYTEST_RECEIPT"])\n'
        ' target.write_text(json.dumps(sys.argv[3:]))\n'
        'else: os.execv(sys.executable,[sys.executable,*sys.argv[1:]])\n'
    )
    python.chmod(0o755)
    env = {
        **os.environ,
        'PATH': str(binary) + ':' + os.environ['PATH'],
        'PYTEST_RECEIPT': str(scratch / 'selected.json'),
        'GITHUB_EVENT_NAME': event,
    }
    env.pop('EDI_RUN_NIGHTLY_ONLY', None)
    jobs = workflow['jobs']
    for job in jobs.values():
        for step in job.get('steps', []):
            if 'system-tests-part' not in step.get('run', ''):
                continue
            for key, value in {**job.get('env', {}), **step.get('env', {})}.items():
                if key != 'EDI_RUN_NIGHTLY_ONLY':
                    continue
                if '${{' in str(value):
                    expression = str(value).replace('matrix.platform', repr(platform))
                    resolved = (
                        'true'
                        if active({'if': expression}, event, core_only=core_only)
                        else 'false'
                    )
                else:
                    resolved = str(value)
                env[key] = resolved
    result = subprocess.run(
        ['bash', str(scripts / 'system-tests-part.sh'), '1', '3'],
        cwd=scratch,
        env=env,
        capture_output=True,
        text=True,
        timeout=2,
        check=False,
    )
    assert result.returncode == 0, (
        'The actual system-shard selector must complete its offline receipt'
    )
    marker = scratch / 'selected.json'
    assert marker.is_file(), 'The selector must reach its real pytest argument boundary'
    return json.loads(marker.read_text())
