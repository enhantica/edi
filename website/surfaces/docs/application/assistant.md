# AI assistant

The AI assistant in EasyDiffraction can explain a refinement, suggest which parameters to fit next,
and carry out supported actions in your open project.

| Interface | Availability |
| --- | --- |
| :lucide-monitor: Desktop app | Select the optional **AI assistant** component during installation. |
| :lucide-globe: Web app | The assistant is unavailable in the browser. The toolbar button opens information about the desktop app. |

## Install and connect

1. Select **AI assistant** in the [desktop installer](desktop.md#download). To add it to an existing
   installation, use **EasyDiffraction Maintenance Tool**, then restart the application.
2. Open a project workflow page and select the robot button in the toolbar.
3. Select **Connect ChatGPT** and complete the OpenAI sign-in if prompted. The assistant needs
   an internet connection and a ChatGPT account with access to a compatible Codex model.

The assistant uses your ChatGPT plan’s Codex allowance. Model access and usage limits depend on the
plan and workspace settings. OpenAI offers limited Codex access on some free accounts. Your account’s
model access determines whether you need a paid subscription. [OpenAI plans and usage limits](https://learn.chatgpt.com/docs/pricing)

## Work with your project

Ask a question about the open project or describe the result you want. For example, ask which
parameters to refine first and why, or ask the assistant to fit the background and inspect the
residual before refining the peak profile.

When EasyDiffraction asks for approval to share project information or attached files, review the
selection before continuing. **Show actions** lets you follow what the assistant does in the app.
Use **Stop** to interrupt ongoing work.

Inspect the resulting pattern and fitted parameters before relying on the result. The
[fit quality guide](../user-guide/fit-quality.md) explains how to assess a refinement.
