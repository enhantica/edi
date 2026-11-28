# SPDX-License-Identifier: BSD-3-Clause
"""Say whether this pull-request run is crysta's final round (edi ADR-0083).

The requester sets the repository variable FINAL_ROUND_<pr> to the full edi head of a final round
and deletes it when the pull request closes. A run is the final round only when that value is its
own head, so a later push does not inherit it; anything else, a malformed value included, is an
ordinary round.

    FINAL_ROUND=<the variable's value> python3 tools/ci/crysta_final_round.py
        prints `final=true` or `final=false`; the reason goes to stderr

The workflow sets FINAL_ROUND from
    ${{ vars[format('FINAL_ROUND_{0}', github.event.pull_request.number)] }}
"""

from __future__ import annotations

import os
import sys

from crysta_subject import COMMIT, RefusedError, edi_of


def final(value: str, head: str, number: str) -> tuple[bool, str]:
    """Whether the variable names this head, and why."""
    if not number:
        return False, 'the run is not of a pull request'
    if not value:
        return False, f'FINAL_ROUND_{number} is not set'
    if not COMMIT.fullmatch(value):
        return False, f'FINAL_ROUND_{number} is not a full commit id'
    if value != head:
        return False, f'FINAL_ROUND_{number} names {value}, not this head {head}'
    return True, f'FINAL_ROUND_{number} names this head {head}'


def main() -> int:
    try:
        head, number = edi_of()
    except (RefusedError, OSError, ValueError) as refusal:
        print(f'crysta-final-round: REFUSED: {refusal}', file=sys.stderr)
        return 1
    is_final, reason = final(os.environ.get('FINAL_ROUND', ''), head, number)
    print(f'final={str(is_final).lower()}')
    print(f'crysta-final-round: {reason}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
