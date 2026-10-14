"""Create offline GitHub Actions job evidence for timing boundary checks."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


def run_record(branch, durations, *, current=False):
    start = datetime(2026, 10, 12, 10, tzinfo=UTC)
    jobs = [
        {
            'id': index,
            'name': f'system · Linux · {index}/{len(durations)}',
            'status': 'completed',
            'conclusion': 'success',
            'started_at': start.isoformat(),
            'completed_at': (start + timedelta(seconds=seconds)).isoformat(),
        }
        for index, seconds in enumerate(durations, 1)
    ]
    jobs.append({
        'id': 99,
        'name': 'app · Linux',
        'status': 'completed',
        'conclusion': 'success',
        'started_at': start.isoformat(),
        'completed_at': (start + timedelta(hours=2)).isoformat(),
    })
    return {
        'id': 111 if current else 222,
        'head_branch': branch,
        'head_sha': ('c' if current else 'b') * 40,
        'event': 'pull_request' if current else 'push',
        'status': 'in_progress' if current else 'completed',
        'conclusion': None if current else 'success',
        'expected_system_shards': {'Linux': len(durations)},
        'jobs': jobs,
    }


def generate(root):
    root.mkdir(parents=True, exist_ok=True)
    for name, value in {
        'main': run_record('main', [2400, 2400, 2400]),
        'current': run_record('feature', [2520, 2640, 2340], current=True),
    }.items():
        (root / f'{name}.json').write_text(json.dumps(value, indent=2) + '\n')


if __name__ == '__main__':
    generate(Path(__file__).resolve().parent / 'records')
