# Work on your desktop

The desktop application uses the same visual workspace as the web app and works with local project folders.

## Local files

Open a project from disk and save it to a local location. You can inspect the project files or use that project from Python and the CLI.

## Choose your starting point

Use the [web app](browser.md) to explore the current application immediately. The edi repository also provides the desktop application for building from source.

## Run a development checkout

For an existing edi development environment, the repository provides:

```console
pixi run -e app app-build
pixi run -e app app-run
```

Building requires the repository's configured dependencies, including access to the crysta SDK. See [contributor documentation](https://enhantica.github.io/edi/dev/) for development setup.

## Learn once

The [workspace tour](workspace.md), [refinement guide](refine.md) and [report guide](reports.md) apply to the visual application in either environment.
