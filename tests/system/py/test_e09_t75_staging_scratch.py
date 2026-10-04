"""Seq44 sweep: corpus, CLI project and Linux UI staging share the CI job lifetime."""

# ruff: noqa: E501 — bounded external observation programs
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from tests.fixtures.e09_t75_commands import COMMANDS
from tests.fixtures.e09_t75_scratch import HOLD, directories, exercise

ROOT = Path(__file__).resolve().parents[3]


def program(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '#!'
        + sys.executable
        + '\nimport os,sys\nfrom pathlib import Path\n'
        + COMMANDS
        + HOLD
        + body
    )
    path.chmod(0o755)


@pytest.mark.parametrize('ending', ['finish', 'fail', 'term', 'kill'])
def test_public_ui_capture_scratch_follows_job_retirement(ending):
    with tempfile.TemporaryDirectory(prefix='ui-scratch-') as folder:
        ui_capture(Path(folder), ending)


def ui_capture(tmp_path, ending):
    repo = tmp_path / 'edi'
    shutil.copytree(ROOT / 'tools/ci', repo / 'tools/ci')
    binary = repo / 'build/app/app/edi_app'
    program(
        binary,
        '\nif len(sys.argv)!=3 or sys.argv[1:]!=["--demo","build/app/ui-actual"]: command_refuse("unsupported display operation")\nhold()\nPath(sys.argv[2]).mkdir(parents=True)\n',
    )
    program(
        binary.with_name('edi_app_ui_compare'),
        '\nif sys.argv[1:]!=["--actual","build/app/ui-actual","--expected","docs/dev/design/app-screenshots/edi","--diff","build/app/ui-diff"]: command_refuse("unsupported display operation")\nif not Path("build/app/ui-actual").is_dir(): sys.exit(65)\n',
    )
    bindir = tmp_path / 'bin'
    program(
        bindir / 'uname',
        '\nif sys.argv[1:]!=["-s"]: command_refuse("unsupported display operation")\nprint("Linux")\n',
    )
    program(
        bindir / 'weston',
        '\nimport socket,signal\nif sys.argv[1:]!=["--backend=headless","--renderer=pixman","--width=1280","--height=768","--socket=edi-app","--idle-time=0"]: command_refuse("unsupported display operation")\ns=socket.socket(socket.AF_UNIX);s.bind(str(Path(os.environ["XDG_RUNTIME_DIR"])/"edi-app"))\nsignal.signal(signal.SIGTERM,lambda *_: sys.exit(0))\nsignal.pause()\n',
    )
    program(
        bindir / 'Xwayland',
        '\nimport signal\nif sys.argv[1:]!=["-geometry","1280x768","-shm","-nolisten","tcp","-displayfd","5"]: command_refuse("unsupported display operation")\nos.write(5,b"99\\n")\nsignal.signal(signal.SIGTERM,lambda *_: sys.exit(0))\nsignal.pause()\n',
    )
    env = {k: v for k, v in os.environ.items() if k not in {'QT_QPA_PLATFORM', 'DISPLAY'}}
    env.update(PATH=str(bindir) + ':' + os.defpath, CONDA_PREFIX=str(tmp_path))
    directories(tmp_path, env)
    exercise(['bash', 'tools/ci/app-ui-test.sh'], repo, env, ending)


@pytest.mark.parametrize('route', ['corpus-policy', 'cli-settings', 'cli-execution'])
@pytest.mark.parametrize('ending', ['finish', 'fail', 'term', 'kill'])
def test_python_ci_staging_obeys_the_job_boundary(tmp_path, route, ending):
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'sample.edi').write_text('_sample.scale 2.5\n')
    (project / 'manifest.yml').write_text('cases: []\n')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('EDI_', 'CRYSTA_'))}
    env['EDI_CRYSTA_CORPUS_ROOT'] = str(project)
    directories(tmp_path, env)
    entry = tmp_path / 'staging-entry.py'
    prelude = (
        'import os,sys,runpy,shutil,subprocess,json\nfrom pathlib import Path\nfrom types import SimpleNamespace\n'
        + HOLD
        + 'project=Path('
        + repr(str(project))
        + ')\n'
        'class Project:\n'
        ' def fit(self): raise ValueError("unrepresented native fit")\n'
        ' fit_independent=fit_joint=fit_sequential=fit\n'
        ' @staticmethod\n'
        ' def load(path):\n'
        '  if Path(path)!=project: raise ValueError("unexpected native load")\n'
        '  return Project()\n'
        ' def save_as(self,path):\n'
        '  hold()\n'
        '  shutil.copytree(project,path)\n'
        'sys.modules["edi"]=SimpleNamespace(Project=Project,_descent_ids=lambda:[],_edi=SimpleNamespace(__file__=str(project/"native/module.so")))\n'
    )
    if route == 'corpus-policy':
        body = (
            'scope=runpy.run_path(' + repr(str(ROOT / 'tools/testing/fit_policy.py')) + ')\n'
            'scope["pytest_configure"](None)\n'
            'assert Path(os.environ["EDI_CRYSTA_CORPUS_ROOT"])!=project, " seq44 corpus must be staged before cancellation"\n'
            'hold()\nscope["pytest_sessionfinish"](None,0)\n'
        )
    else:
        body = 'scope=runpy.run_path(' + repr(str(ROOT / 'tools/checks/cli_projects.py')) + ')\n'
        if route == 'cli-settings':
            body += (
                'result=scope["loaded_settings"](project)\n'
                'assert result["scale"]["sample.edi:_sample.scale"]["value"]==2.5, " seq44 the native save handoff must reach the real settings reader"\n'
            )
        else:
            source = tmp_path / 'docs/user/cli/fixture'
            source.mkdir(parents=True)
            shutil.copytree(project, source / 'project')
            (source / 'expected.json').write_text(
                '{"quantities":{"rwp":{"value":2.5,"tol_abs":0}}}'
            )
            body += (
                'def invoke(argv,**kwargs):\n'
                ' if len(argv)!=9 or argv[:4]!=[sys.executable,"-m","edi","fit"] or argv[5:]!=["--report","machine","--verbosity","full"]: raise ValueError("unexpected fit invocation")\n'
                ' if not Path(argv[4],"sample.edi").is_file(): raise ValueError("fit did not receive the staged project")\n'
                ' hold()\n'
                ' return subprocess.CompletedProcess(argv,0,"status=done\\nrwp=2.5\\n","")\n'
                'subprocess.run=invoke\n'
                'result=scope["run_project"](project.parent,"fixture")\n'
                'assert not result, " seq44 the native execution handoff must reach the real result comparison"\n'
            )
    entry.write_text(prelude + body)
    exercise([sys.executable, str(entry)], ROOT, env, ending)
