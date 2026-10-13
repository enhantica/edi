"""Real project load/save byte witnesses belong to the integration boundary.

The original byte pins and all assertions remain in their retained helpers.
Native serialization, input archive extraction and filesystem work are exercised
here under the integration runtime bound; the unit limit remains unchanged.
"""

from tests.unit.py import test_c11_t4_cw_selection as cw
from tests.unit.py import test_c11_t56_project_identity as identity


def test_c11_t4_existing_tof_writer_goldens_remain_byte_exact(tmp_path):
    cw.require_existing_tof_writer_goldens(tmp_path)


def test_c11_t56_datablock_bytes_match_pre_fix_regression_pins(tmp_path):
    identity.require_datablock_regression_pins(tmp_path)
