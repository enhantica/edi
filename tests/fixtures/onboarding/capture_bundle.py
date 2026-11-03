"""Generate the native capture prerequisite outside per-node acceptance timing."""

import os
import subprocess
from pathlib import Path

if __name__ == '__main__':
    source = Path(__file__).resolve().parents[3]
    output = Path(
        os.environ.get('EDI_ONBOARDING_CAPTURE_BUNDLE', source / 'build/onboarding-capture')
    )
    subprocess.run(['bash', str(source / 'tools/docs/capture-gui.sh'), str(output)], check=True)
