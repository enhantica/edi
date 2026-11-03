"""Escape controls for the conductor's core/app artifact availability contract."""

import pytest

from tests.fixtures.native_ui_script import runner


def check_job_requirements(tmp_path, monkeypatch):
    missing = tmp_path / 'edi_app_tests'
    prefix = tmp_path / 'pixi-prefix'
    with monkeypatch.context() as patch:
        patch.delenv('EDI_APP_TEST_RUNNER', raising=False)
        patch.setattr(runner.sys, 'prefix', str(prefix))
        with (
            pytest.warns(pytest.PytestWarning, match='neither the artifact nor Qt6QuickTest'),
            pytest.raises(pytest.skip.Exception, match='neither the artifact nor Qt6QuickTest'),
        ):
            runner.require_runner(missing)
        config = prefix / 'lib/cmake/Qt6QuickTest/Qt6QuickTestConfig.cmake'
        config.parent.mkdir(parents=True)
        config.write_text('# authored capability presence; no application behavior\n')
        with pytest.raises(AssertionError, match='app-capable job must run app-build'):
            runner.require_runner(missing)
        config.unlink()
        patch.setenv('EDI_APP_TEST_RUNNER', str(missing))
        with pytest.raises(AssertionError, match='explicit EDI_APP_TEST_RUNNER'):
            runner.require_runner(missing)
        patch.delenv('EDI_APP_TEST_RUNNER')
        missing.write_text('authored non-executable artifact\n')
        with pytest.raises(AssertionError, match='real edi_app_tests runner'):
            runner.require_runner(missing)
        missing.unlink()
        missing.symlink_to(tmp_path / 'absent-target')
        with pytest.raises(AssertionError, match='real edi_app_tests runner'):
            runner.require_runner(missing)
        missing.unlink()
        # A core job that actually received an executable artifact may use it;
        # this check does not invoke or substitute the executable's behavior.
        missing.write_text('#!/bin/sh\nexit 99\n')
        missing.chmod(0o755)
        runner.require_runner(missing)
