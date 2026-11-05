---
template: interface.html
---

# Desktop application

Use native file dialogs and work directly with projects on your computer.

## Download

<!-- distribution:desktop -->
<div class="ed-downloads"><a class="md-button" href="https://github.com/enhantica/edi/releases" aria-label="Download for macOS">macOS</a>
<a class="md-button" href="https://github.com/enhantica/edi/releases" aria-label="Download for Windows">Windows</a>
<a class="md-button" href="https://github.com/enhantica/edi/releases" aria-label="Download for Linux">Linux</a></div>
<!-- /distribution -->

Open GitHub Releases and choose the online installer for your system. It downloads the application and its required components. Linux builds initially target Ubuntu 24.04 or newer. You can also use the [web app](browser.md).

## Install and update

Download the ZIP for your platform and extract the whole archive before opening the installer.
Keep the extracted files together: the Linux installer needs the accompanying `installer-runtime`
folder. Choose an installation folder and follow the installer steps. An internet connection is
required to download the application and its dependencies.

The initial builds support Windows x86-64, macOS Apple Silicon and Linux x86-64 on Ubuntu 24.04
or newer. Python and Qt do not need to be installed separately.

When a newer release is available, the application shows a red **Update** button. Save your changes
when prompted, then follow the maintenance tool. On the next launch, **What's new** shows the changes
since your previous version.

## Open local projects

Choose **Open project…** and select a folder or zip archive. You can also drop a project folder, its `project.edi` file or a zip archive onto the application window.

An archive opens as a temporary working copy. **Save** updates the archive when it is writable; otherwise the app asks where to save it.

## Save and share

**Save project as…** writes a folder or zip archive. Select **Save a copy** to write to another location while continuing in the original project.

Use a folder to access individual model and result files, or a zip archive to move the complete project. Reports are saved in the project's `reports/` folder, inside the archive when the project is a zip. When the project cannot be written back, such as an example or a read-only archive, the app first asks where to save it.

The [application layout](workspace.md) and [example refinement](first-refinement.md) apply to both desktop and web versions.
