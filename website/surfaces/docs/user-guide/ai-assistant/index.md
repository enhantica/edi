---
template: gui.html
---

# AI assistant

EasyDiffraction is ready for AI assistants. The desktop app has an assistant built in, which works in your open project. ChatGPT or Claude, in their desktop apps or command-line tools, can write a notebook or a project for you from your own files: a structure and a measured pattern become a fit set up in stages, which you then run, check and change.

| Where | Built-in assistant | Your own assistant | Notes |
| --- | :---: | :---: | --- |
| Desktop app | <span role="img" aria-label="Available: built into the desktop app" title="Available: built into the desktop app">:status-available:</span> | <span role="img" aria-label="Available: open the project it writes" title="Available: open the project it writes">:status-available:</span> | The built-in assistant is an optional part of the desktop app and needs a ChatGPT account. |
| Web app | <span role="img" aria-label="Not available: the browser has no built-in assistant" title="Not available: the browser has no built-in assistant">:fa5-times-circle:</span> | <span role="img" aria-label="Available: open the project it writes" title="Available: open the project it writes">:status-available:</span> | The browser has no built-in assistant; open the project your own assistant writes. |
| Python | <span role="img" aria-label="Not available: no built-in assistant in Python" title="Not available: no built-in assistant in Python">:fa5-times-circle:</span> | <span role="img" aria-label="Available: it writes a notebook" title="Available: it writes a notebook">:status-available:</span> | Your own assistant writes a Jupyter notebook ready to run. |
| Command line | <span role="img" aria-label="Not available: no built-in assistant on the command line" title="Not available: no built-in assistant on the command line">:fa5-times-circle:</span> | <span role="img" aria-label="Available: it writes a project" title="Available: it writes a project">:status-available:</span> | Your own assistant writes a project ready for `edi fit`. |

## Built-in assistant (desktop app)

The desktop app's assistant can explain a fit, suggest which parameters to fit next, and carry out supported actions in your open project. The [Fit with the AI assistant](../../application/tutorials/assistant.md) tutorial follows one run.

<!-- assistant-result -->
<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../assets/gui/assistant/assistant-fitted.webp?v=4ee14f474b42" data-gui-dark="125ecf5bcec3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Answer, and the assistant fits the structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Answer, and the assistant fits the structure"><title>Answer, and the assistant fits the structure</title><defs><clipPath id="gui-clip-assistant-fitted-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/assistant/assistant-fitted.webp?v=4ee14f474b42" data-gui-dark="125ecf5bcec3" width="1480" height="800" clip-path="url(#gui-clip-assistant-fitted-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="assistant-fitted-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,133,682,481]]" d="M785.000 138.000 Q785.000 134.000 789.000 134.000 L1461.000 134.000 Q1465.000 134.000 1465.000 138.000 L1465.000 609.000 Q1465.000 613.000 1461.000 613.000 L789.000 613.000 Q785.000 613.000 785.000 609.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

The assistant after it fitted La₀.₅Ba₀.₅CoO₃ on HRPT ([the tutorial](../../application/tutorials/assistant.md)).
<!-- /assistant-result -->

### Install and connect

1. Select **AI assistant** in the [desktop installer](../../application/desktop.md#download). To add it to an existing
   installation, open **Preferences → Updates → Open Maintenance Tool** and add **AI assistant**, then restart the application.
2. Open a project workflow page and select the robot button in the toolbar.
3. Select **Connect ChatGPT** and complete the OpenAI sign-in if prompted. The assistant needs
   an internet connection and a ChatGPT account with access to a compatible Codex model.

The assistant uses your ChatGPT plan’s Codex allowance. Model access and usage limits depend on the
plan and workspace settings. OpenAI offers limited Codex access on some free accounts. Your account’s
model access determines whether you need a paid subscription. [OpenAI plans and usage limits](https://learn.chatgpt.com/docs/pricing)

In the web app the robot button opens a note about the desktop app instead: the browser has no built-in assistant.

### Work with your project

Ask a question about the open project or describe the result you want. For example, ask which
parameters to fit first and why, or ask the assistant to fit the background and inspect the
residual before fitting the peak profile.

When EasyDiffraction asks for approval to share project information or attached files, review the
selection before continuing. Use **Stop** to interrupt ongoing work.

Inspect the resulting pattern and fitted parameters before relying on the result. The
[fit quality guide](../analysis-workflow/analysis.md#fit-quality) explains how to assess a fit.

### Show actions

**Show actions**, in the chat's composer, shows each action the assistant takes in the app as it works, on the control it uses. Off, the assistant works in the background and reports in the chat.

## Your own assistant

ChatGPT or Claude, in their desktop apps or command-line tools, can write what each interface uses, given the documentation, the tutorials and your files:

- a Jupyter notebook ready to run: the [Python AI assistant tutorial](../../python/tutorials/assistant.md);
- a project to fit with `edi fit`: the [Command line AI assistant tutorial](../../cli/tutorials/assistant.md);
- a project to open in the desktop or web app, as an alternative to the built-in assistant or in its place: the same Command line prompt.

Open a project it returns in the app:

=== ":fa5-desktop: Desktop app"

    On **Project**, choose **Open project…**, then **Folder** and select the project folder. You can also drop the folder or its `project.edi` file onto the window.

=== ":fa5-globe: Web app"

    On **Project**, choose **Open project…**, then **Folder**, or zip the project folder first and choose **Zip archive**. Where the project is kept afterwards depends on the browser; see [Open and save files](../../application/browser.md#open-and-save-files).
