"""gate 8: joint CLI fit/save uses its own declared corpus copy."""

from __future__ import annotations

from test_e05_t1_cli_fit_save import CASES, run_cli_fit_save_reopen_and_undo


def test_cli_joint_fit_save_reopen_and_undo(tmp_path):
    case = next(c for c in CASES if c['id'] == 'pd-neut-tof_ncaf-wish-3bank_start-5')
    run_cli_fit_save_reopen_and_undo(case, tmp_path)
