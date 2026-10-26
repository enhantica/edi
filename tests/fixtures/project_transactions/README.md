# Save and open transaction observer

Inputs: the committed edi tree, its pinned SDK installed at `build/crysta-prefix`, and the app and default Pixi environments. The builder archives committed sources; it ignores uncommitted production changes and refuses when those differ from the checkout.

```sh
export CCACHE_DIR=/tmp/edi-transaction-ccache
export CI=true
export GITHUB_ACTIONS=true
export GITHUB_EVENT_NAME=push
export GITHUB_WORKSPACE="$PWD"
pixi run -e app python -m tests.fixtures.project_transactions.build \
  --root "$PWD" --sdk "$PWD/build/crysta-prefix" \
  --output "$PWD/build/transaction-observer"
export EDI_TRANSACTION_RECEIPT="$PWD/build/transaction-observer/observer/receipt.json"
export PYTHONPATH="$PWD/tools/checks${PYTHONPATH:+:$PYTHONPATH}"
export EDI_FIXTURE_COST_LOG="$PWD/build/transaction-observer/fixture-costs.json"
pixi run python -m pytest tests/system/py/test_project_transactions.py \
  tests/system/py/test_save_exact_values.py tests/system/py/test_save_mixed_backgrounds.py \
  -vv --durations=0 -p fixture_costs
```

The browser observations use the pinned Chromium and Node toolchains resolved by the browser fixture. The Session observer holds asynchronous browser I/O at the native link boundary. The browser-handle observations execute the production JavaScript in Chromium.
