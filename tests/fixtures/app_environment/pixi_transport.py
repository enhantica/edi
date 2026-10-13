"""Cold-prefix launcher transport, not installed packages or compiled-app evidence."""

import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
args = sys.argv[2:]
if args[0] != 'run' or args[args.index('-e') + 1] != 'app':
    raise SystemExit('The compiled app needs its declared app environment')
prefix = root / '.pixi/envs/app'
if not prefix.exists() and any(flag in args for flag in ('--as-is', '--no-install')):
    raise SystemExit('An absent app prefix cannot run with installation disabled')
prefix.mkdir(parents=True, exist_ok=True)
print(json.dumps({'kind': 'transport-only', 'environment': 'app', 'prefix': str(prefix)}))
