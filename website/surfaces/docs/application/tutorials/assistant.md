---
template: gui.html
---

# Fit with the AI assistant

The app has an AI assistant built in. Give it a structure and a measured pattern and ask it to fit the structure: it asks for what the files do not say, then sets up the project and fits it in stages, as the tutorials do by hand. This page follows one run on La₀.₅Ba₀.₅CoO₃ measured on HRPT, the case of the [La₀.₅Ba₀.₅CoO₃ on HRPT](cases/pd-neut-cwl_lbco-hrpt.md) tutorial.

## Get the two files

Download them from EasyDiffraction's collection:

- [tutorial-lbco.cif](https://raw.githubusercontent.com/enhantica/edi-data/main/structures/tutorial-lbco.cif): the structure.
- [tutorial-hrpt.xye](https://raw.githubusercontent.com/enhantica/edi-data/main/data/tutorial-hrpt.xye): the measured pattern.

## Open and connect

The assistant needs the desktop app and a ChatGPT account (see [AI assistant](../../user-guide/ai-assistant/index.md)). Open it with the robot button in the toolbar and connect.

<div class="gui-viewer" markdown="1">


=== "Panel"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../assets/gui/assistant/assistant-panel.webp?v=ab9eb29c29d9" data-gui-dark="f88a3147f077" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Open the assistant from the toolbar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Open the assistant from the toolbar"><title>Open the assistant from the toolbar</title><defs><clipPath id="gui-clip-assistant-panel-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/assistant/assistant-panel.webp?v=ab9eb29c29d9" data-gui-dark="f88a3147f077" width="1480" height="800" clip-path="url(#gui-clip-assistant-panel-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="assistant-panel-overview-1" data-gui-area="sidebar" data-gui-parts="[[1327,80,145.5999999999999,35]]" d="M1328.000 85.000 Q1328.000 81.000 1332.000 81.000 L1467.600 81.000 Q1471.600 81.000 1471.600 85.000 L1471.600 110.000 Q1471.600 114.000 1467.600 114.000 L1332.000 114.000 Q1328.000 114.000 1328.000 110.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "Connect"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../assets/gui/assistant/assistant-connect.webp?v=b93b167ca15f" data-gui-dark="c10dbc5d4d78" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Connect ChatGPT"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Connect ChatGPT"><title>Connect ChatGPT</title><defs><clipPath id="gui-clip-assistant-connect-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/assistant/assistant-connect.webp?v=b93b167ca15f" data-gui-dark="c10dbc5d4d78" width="1480" height="800" clip-path="url(#gui-clip-assistant-connect-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

</div>

## Show actions

With **Show actions** on, the app shows each action the assistant takes as it works, on the control it uses. This run leaves it off, so the assistant works in the background and reports in the chat.

<figure class="gui-figure" data-gui-figure>
<a class="gui-image-link" href="../../assets/gui/assistant/assistant-ready.webp?v=d9de5762f66f" data-gui-dark="855f0f623d5b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: The assistant is connected; Show actions is off"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="The assistant is connected; Show actions is off"><title>The assistant is connected; Show actions is off</title><defs><clipPath id="gui-clip-assistant-ready-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/assistant/assistant-ready.webp?v=d9de5762f66f" data-gui-dark="855f0f623d5b" width="1480" height="800" clip-path="url(#gui-clip-assistant-ready-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="assistant-ready-overview-1" data-gui-area="sidebar" data-gui-parts="[[828.5,706.2,121,26.25]]" d="M829.500 711.200 Q829.500 707.200 833.500 707.200 L944.500 707.200 Q948.500 707.200 948.500 711.200 L948.500 727.450 Q948.500 731.450 944.500 731.450 L833.500 731.450 Q829.500 731.450 829.500 727.450 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

</figure>

## Ask for the fit

Attach both files with the **+** button, ask it to fit the crystal structure, and send. The app asks before it shares the project and the files.

<div class="gui-viewer" markdown="1">


=== "Message"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../assets/gui/assistant/assistant-ask.webp?v=a8196c05c214" data-gui-dark="de6fe4084833" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Attach the two files and ask for the fit"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Attach the two files and ask for the fit"><title>Attach the two files and ask for the fit</title><defs><clipPath id="gui-clip-assistant-ask-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/assistant/assistant-ask.webp?v=a8196c05c214" data-gui-dark="de6fe4084833" width="1480" height="800" clip-path="url(#gui-clip-assistant-ask-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="assistant-ask-overview-1" data-gui-area="sidebar" data-gui-parts="[[794.5,600.5,661,46.200000000000045]]" d="M795.500 605.500 Q795.500 601.500 799.500 601.500 L1450.500 601.500 Q1454.500 601.500 1454.500 605.500 L1454.500 641.700 Q1454.500 645.700 1450.500 645.700 L799.500 645.700 Q795.500 645.700 795.500 641.700 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "Approve"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../assets/gui/assistant/assistant-approve.webp?v=14b124524343" data-gui-dark="f80257be8aa9" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Approve sharing the project information and the files"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Approve sharing the project information and the files"><title>Approve sharing the project information and the files</title><defs><clipPath id="gui-clip-assistant-approve-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/assistant/assistant-approve.webp?v=14b124524343" data-gui-dark="f80257be8aa9" width="1480" height="800" clip-path="url(#gui-clip-assistant-approve-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

</div>

## Answer its question

The pattern does not say which radiation or wavelength was used, so the assistant asks. Answer, and it fits the structure.

<div class="gui-viewer" markdown="1">


=== "Question"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../assets/gui/assistant/assistant-question.webp?v=aa3bbcdfd8ff" data-gui-dark="76ae0e2962aa" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: The assistant asks what the files do not say"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="The assistant asks what the files do not say"><title>The assistant asks what the files do not say</title><defs><clipPath id="gui-clip-assistant-question-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/assistant/assistant-question.webp?v=aa3bbcdfd8ff" data-gui-dark="76ae0e2962aa" width="1480" height="800" clip-path="url(#gui-clip-assistant-question-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="assistant-question-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,133,682,481]]" d="M785.000 138.000 Q785.000 134.000 789.000 134.000 L1461.000 134.000 Q1465.000 134.000 1465.000 138.000 L1465.000 609.000 Q1465.000 613.000 1461.000 613.000 L789.000 613.000 Q785.000 613.000 785.000 609.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "Fitted"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../assets/gui/assistant/assistant-fitted.webp?v=4ee14f474b42" data-gui-dark="125ecf5bcec3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Answer, and the assistant fits the structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Answer, and the assistant fits the structure"><title>Answer, and the assistant fits the structure</title><defs><clipPath id="gui-clip-assistant-fitted-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/assistant/assistant-fitted.webp?v=4ee14f474b42" data-gui-dark="125ecf5bcec3" width="1480" height="800" clip-path="url(#gui-clip-assistant-fitted-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="assistant-fitted-overview-1" data-gui-area="sidebar" data-gui-parts="[[784,133,682,481]]" d="M785.000 138.000 Q785.000 134.000 789.000 134.000 L1461.000 134.000 Q1465.000 134.000 1465.000 138.000 L1465.000 609.000 Q1465.000 613.000 1461.000 613.000 L789.000 613.000 Q785.000 613.000 785.000 609.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Pattern"

    <figure class="gui-figure" data-gui-figure>
    <a class="gui-image-link" href="../../assets/gui/assistant/assistant-result.webp?v=4ee14f474b42" data-gui-dark="125ecf5bcec3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: The fitted pattern on Analysis"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="The fitted pattern on Analysis"><title>The fitted pattern on Analysis</title><defs><clipPath id="gui-clip-assistant-result-overview"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../../assets/gui/assistant/assistant-result.webp?v=4ee14f474b42" data-gui-dark="125ecf5bcec3" width="1480" height="800" clip-path="url(#gui-clip-assistant-result-overview)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="assistant-result-overview-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>

## What it did

It asked whether the data were neutron or X-ray and for the wavelength, built the project from the two files, fitted in stages and shared one displacement between La and Ba. It ended at a = 3.890787(37) Å, within the tutorial's result, with La/Ba B iso 0.410(34) Å² against the tutorial's 0.55(6) Å², Rwp 6.91 % and reduced χ² 1.19, freeing 32 parameters where the tutorial frees 15. Its last step, saving the project, returned no confirmation. Tried with gpt-6.1-sol on 2026-11-09; another run can take other steps, so check the result against the [La₀.₅Ba₀.₅CoO₃ on HRPT](cases/pd-neut-cwl_lbco-hrpt.md) tutorial.
