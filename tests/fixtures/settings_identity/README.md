# Native settings probe

The probe compiles complete production functions from `engine_setup.cpp` with Qt Core. The
preparer copies bounded source spans unchanged, records the provider digest, and refuses missing
or ambiguous boundaries. No QML host, engine binary or sibling product checkout is used.

From the app Pixi environment, prepare and build it before running the Python gate:

```sh
python tests/fixtures/settings_identity/prepare.py . build/settings-identity
cmake -S tests/fixtures/settings_identity -B build/settings-identity -G Ninja -DCMAKE_PREFIX_PATH="$CONDA_PREFIX"
cmake --build build/settings-identity --parallel 2
python tests/fixtures/settings_identity/prepare.py --stamp . build/settings-identity
```

`EDI_SETTINGS_PROBE_DIR` selects another build directory. Each test checks the copied production
functions against the source and verifies the stamped fixture and executable hashes. The process
receives private settings, home and data folders. Integer and boolean preferences are read using
QSettings' typed accessors, matching consumers of an INI store.
