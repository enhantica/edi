# Interface entry pages

The entry pages share `interface.html`, `interfaces.css` and the existing themed image dialog. Their text covers interaction and setup, while the shared User guide and Physics retain scientific explanations.

## Downloads

Set the `url` for each platform in [distributions.json](distributions.json), then build. A null URL produces a disabled button. Do not use release links from the older application. Add architecture-specific choices when actual release artifacts are known.

The canonical desktop download section is `application/desktop/#download`; the homepage Desktop app shortcut links straight there. Command Line has a separate standalone download section and a Python-package setup route. Its usage examples offer invocation tabs with matching arguments.

## Real notebook and terminal captures

The fixture comes from the GUI capture manifest, so importing another GUI example selects the same case here. The current notebook plotting cell expects constant-wavelength powder data. Use an edi build whose Python bindings are available, and a runtime containing JupyterLab, nbformat, nbclient, ipykernel and Plotly. The documentation environment needs Playwright and a browser.

```sh
python website-concepts/capture_interfaces.py \
  --edi-root /absolute/path/to/edi \
  --runtime-python /absolute/path/to/edi/.pixi/envs/app/bin/python \
  --output /absolute/path/to/new-capture
python website-concepts/build.py surfaces
```

The script currently selects the native extension from `build/assistant-dev/python/edi`. It executes the notebook, opens that notebook in JupyterLab, then runs the CLI in a real terminal and checks its screen buffer for convergence. Terminal canvas pixels are not exposed through ordinary DOM text or reliably represented by page-level WebSocket events. Jupyter settings and workspace state are isolated so restored tabs and first-run notifications cannot contaminate captures.

The outputs include the actual screenshots, executed notebook, unchanged input project archive, CLI transcript and source/script identity. The application hero reuses the homepage image and the same title-bar crop. Image URLs use content hashes.

```sh
python website-concepts/checks/interface_pages_browser.py --output /absolute/path/to/evidence
```

This checks desktop/mobile preview sizing, image enlargement, the Home download shortcut, pending download controls and CLI argument parity. Native Safari runs through the same browser check on macOS; the first hosted attempt could not start a Safari WebDriver session, so no Safari pass is claimed.
