---
template: interface.html
---

# Desktop application

Use native file dialogs and work directly with projects on your computer.

## Download

<!-- distribution:desktop -->
<div class="ed-downloads"><button class="md-button" type="button" disabled aria-label="macOS download not available yet">macOS</button>
<button class="md-button" type="button" disabled aria-label="Windows download not available yet">Windows</button>
<button class="md-button" type="button" disabled aria-label="Linux download not available yet">Linux</button></div>
<!-- /distribution -->

Installer links will be added here when the new releases are available. You can use the [web app](browser.md) now.

## Open local projects

Choose **Open project…** and select a folder or zip archive. You can also drop a project folder, its `project.edi` file or a zip archive onto the application window.

An archive opens as a temporary working copy. **Save** updates the archive when it is writable; otherwise the app asks where to save it.

## Save and share

**Save project as…** writes a folder or zip archive. Select **Save a copy** to write to another location while continuing in the original project.

Use a folder to access individual model and result files, or a zip archive to move the complete project. Reports are saved in the project's `reports/` folder, inside the archive when the project is a zip. When the project cannot be written back, such as an example or a read-only archive, the app first asks where to save it.

The [application layout](workspace.md) and [example refinement](first-refinement.md) apply to both desktop and web versions.
