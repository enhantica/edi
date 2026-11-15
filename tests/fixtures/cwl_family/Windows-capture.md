# Original Windows rename reference

The missing file is `tch-regression-Windows.json`. It must be produced by a native Windows x64 build of these **unchanged original sources**:

| Subject | Repository | Exact commit |
| --- | --- | --- |
| Edi product | Original Edi repository | `7a8eabf53084332a10b90991907d2040e5365b6a` |
| Linked engine | `enhantica/crysta` | `b9f2267451adf1896463c706a87fea20790d28ac` |
| Harness/toolchain | Current Edi branch, including this helper | Record its exact checkout SHA in the job |

Use `windows-2022`, x64 MSVC toolset 14.44 (`ilammy/msvc-dev-cmd@v1`), and the current Edi frozen default Pixi environment. The old Edi Pixi manifest does not declare Windows, so do **not** invoke its Bash tasks or solve a replacement environment. The helper runs CMake directly inside the current locked Windows environment; the numerical sources remain at their original commits.

Check out all three repositories as separate folders, for example `harness`, `baseline-edi`, `baseline-engine`. Set `core.autocrlf=false` before checkout, retain LF input bytes, and use the existing Windows-compatible checkout exclusions from Edi CI for reserved filenames. The runner needs authorized access to the original repository containing this historical commit. Do not substitute the new public root commit if the old checkout fails.

After installing the current locked environment using `harness/.github/actions/setup-pixi` with `manifest-path: harness/pixi.toml`, run this single command in PowerShell:

```powershell
pixi run --manifest-path harness/pixi.toml --frozen --no-install --skip-deps `
  pwsh -NoProfile -File harness/tests/fixtures/cwl_family/capture_windows.ps1 `
  -Product baseline-edi -Engine baseline-engine `
  -Output "$env:RUNNER_TEMP/cwl-original-windows-$env:GITHUB_RUN_ID-$env:GITHUB_RUN_ATTEMPT"
```

The script configures the original engine as a Release C++ package, builds only `crysta_cli` and its original core, installs that exact package, and builds only Edi's original `_edi` target against it. It preserves a compiled CLI stamp, verifies the installed/native archive bytes agree, loads Edi's explicit original physical module and original Python package, verifies the module stamp and selected linked package, and calculates the two unchanged historical inputs (`tch`, `fcj`). It refuses later/dirty sources, wrong input bytes, unknown artifacts, a foreign import or an overridden SIMD selection.

Upload the complete output directory with `actions/upload-artifact@v4`, `if: always()`, `if-no-files-found: error`. The necessary review files are:

- `artifacts/tch-regression-Windows.json`: both complete finite little-endian float64 sample arrays, original product/engine identities, all four serialized-input hashes, actual Windows archive/CLI digests, module/generator digests and run identity.
- `artifacts/capture-provenance.json`: Python/native module and compiled-engine provenance.
- `artifacts/product-CMakeCache.txt`, `artifacts/engine-CMakeCache.txt`, `artifacts/product-tree.txt`, `artifacts/engine-tree.txt`.
- `capture.log`, `capture.exit`; also retain the two native build directories if a build fails, so its compiler/linker failure is actionable. An exit of 1 produces no acceptable pin. No scientific source patch is authorized by this capture recipe.

The historical TCH expectation cannot be borrowed from Linux or Darwin: the existing native-reference admission and its negative controls require an authentic pre-change capture for the selected host. The existing ADR-0057 rule still compares different known builds/platforms at `max(5e-9*abs(reference), 5e-10)`, checks every finite sample, and keeps repeated calculation exact within the current build. A genuine historical Windows archive digest supplies its actual build identity; no later numerical retake or Windows dispatch sidecar is needed to invent one.

The separately sealed, authorized continuous-integral FCJ model reference is already compared across platforms using that same unchanged rule. It stays byte-identical. Its five anti-retake controls still require the genuine Windows historical admission file before checking the model seal. No new FCJ model pin is requested.

After the artifact is reviewed, install only the authentic `tch-regression-Windows.json` in this fixture directory and replay the seven blocked nodes in `tests/integration/py/test_cwl_rename_bytes.py`, plus the full file's positive/negative controls. The reader's Windows platform/archive/input admission is prepared; no Windows pin is fabricated in this change. This recipe is statically prepared on Linux and is not a claim that PowerShell or the original Windows build has already succeeded.
