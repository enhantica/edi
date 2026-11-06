---
template: gui.html
---

# Example refinement

Create a refinement from a crystal-structure CIF and a measured diffraction pattern. This example uses Y₂O₃ [Ia-3] measured on SPODI @ FRM II.

The [application layout](workspace.md) introduces the controls. Follow the steps below in the web or desktop app.

## Download the inputs

- [Crystal structure: y2o3.cif](../assets/gui/y2o3/inputs/structures/y2o3.cif)
- [Measured data: spodi.xye](../assets/gui/y2o3/inputs/spodi.xye) — scattering angle, intensity and standard uncertainty.

Start with an empty project. Set up the experiment in the app; the measured-data file does not supply the wavelength, profile or background.

## Home

Press **Start** to begin.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Begin a new analysis on the Project page.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/01-home.png?v=88492aa4f719" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Start"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Start"><title>Start</title><defs><clipPath id="gui-clip-01-home-overview-home-start"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/01-home.png?v=88492aa4f719" width="1480" height="800" clip-path="url(#gui-clip-01-home-overview-home-start)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="01-home-overview-home-start-1" data-gui-area="main" data-gui-parts="[[573,404,334,39]]" d="M571.000 402.000 L909.000 402.000 L909.000 445.000 L571.000 445.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[542,0,53.46875,77]]" d="M540.000 -2.000 L597.469 -2.000 L597.469 79.000 L540.000 79.000 Z" /></svg></a>

</figure>

</div>

## Create a project

Choose **Create a new project**.

<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61525;</span>Create a new project"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Open the project-details form.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/02-project-start.png?v=8668e1c863fd" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create a new project"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create a new project"><title>Create a new project</title><defs><clipPath id="gui-clip-02-project-start-overview-project-create"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/02-project-start.png?v=8668e1c863fd" width="1480" height="800" clip-path="url(#gui-clip-02-project-start-overview-project-create)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="02-project-start-overview-project-create-1" data-gui-area="sidebar" data-gui-parts="[[784,168,334,39]]" d="M782.000 166.000 L1120.000 166.000 L1120.000 209.000 L782.000 209.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61749;</span>Get started"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Create a project or open an existing one.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/02-project-start.png?v=8668e1c863fd" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Get started"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Get started"><title>Get started</title><defs><clipPath id="gui-clip-02-project-start-overview-group-getStarted"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/02-project-start.png?v=8668e1c863fd" width="1480" height="800" clip-path="url(#gui-clip-02-project-start-overview-group-getStarted)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="02-project-start-overview-group-getStarted-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,155]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 276.000 L768.000 276.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

</div>

## Enter project details

Give the analysis a name, title and description, choose where to keep it, then confirm.

<div class="gui-viewer" markdown="1">


=== "Name"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use a short project identifier.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/03-project-details.png?v=3d2b30b6f5f2" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Name"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Name"><title>Name</title><defs><clipPath id="gui-clip-03-project-details-overview-createProject-name"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/03-project-details.png?v=3d2b30b6f5f2" width="1480" height="800" clip-path="url(#gui-clip-03-project-details-overview-createProject-name)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="03-project-details-overview-createProject-name-1" data-gui-area="main" data-gui-parts="[[495,237,490,35]]" d="M493.000 235.000 L987.000 235.000 L987.000 274.000 L493.000 274.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

=== "Title"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Give the analysis a descriptive title.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/03-project-details.png?v=3d2b30b6f5f2" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Title"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Title"><title>Title</title><defs><clipPath id="gui-clip-03-project-details-overview-createProject-title"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/03-project-details.png?v=3d2b30b6f5f2" width="1480" height="800" clip-path="url(#gui-clip-03-project-details-overview-createProject-title)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="03-project-details-overview-createProject-title-1" data-gui-area="main" data-gui-parts="[[495,305,490,35]]" d="M493.000 303.000 L987.000 303.000 L987.000 342.000 L493.000 342.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

=== "Description"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Record the sample, measurement and purpose.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/03-project-details.png?v=3d2b30b6f5f2" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Description"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Description"><title>Description</title><defs><clipPath id="gui-clip-03-project-details-overview-createProject-description"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/03-project-details.png?v=3d2b30b6f5f2" width="1480" height="800" clip-path="url(#gui-clip-03-project-details-overview-createProject-description)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="03-project-details-overview-createProject-description-1" data-gui-area="main" data-gui-parts="[[495,441,490,73]]" d="M493.000 439.000 L987.000 439.000 L987.000 516.000 L493.000 516.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

=== "Location"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Choose where the project will be saved.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/03-project-details.png?v=3d2b30b6f5f2" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Location"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Location"><title>Location</title><defs><clipPath id="gui-clip-03-project-details-overview-createProject-location"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/03-project-details.png?v=3d2b30b6f5f2" width="1480" height="800" clip-path="url(#gui-clip-03-project-details-overview-createProject-location)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="03-project-details-overview-createProject-location-1" data-gui-area="main" data-gui-parts="[[495,547,490,35]]" d="M493.000 545.000 L987.000 545.000 L987.000 584.000 L493.000 584.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

</div>

## Inspect the project

Check the project details before adding a structure and measurement.

<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the project view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/04-project-created.png?v=142ee9189ead" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-04-project-created-overview-workflow-project-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/04-project-created.png?v=142ee9189ead" width="1480" height="800" clip-path="url(#gui-clip-04-project-created-overview-workflow-project-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="04-project-created-overview-workflow-project-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/04-project-created.png?v=142ee9189ead" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-04-project-created-overview-workflow-project-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/04-project-created.png?v=142ee9189ead" width="1480" height="800" clip-path="url(#gui-clip-04-project-created-overview-workflow-project-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="04-project-created-overview-workflow-project-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

    </figure>

</div>

The Project page now shows your project name and details.

## Load the structure

Open **Structure → Main**, expand **Structures**, choose **Load ▾ → From file…** and select **y2o3.cif**.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Import the structure file for this example.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/06-structure-import.png?v=b9a32d40c465" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load structure"><title>Load structure</title><defs><clipPath id="gui-clip-06-structure-import-overview-structures-load"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/06-structure-import.png?v=b9a32d40c465" width="1480" height="800" clip-path="url(#gui-clip-06-structure-import-overview-structures-load)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="06-structure-import-overview-structures-load-1" data-gui-area="sidebar" data-gui-parts="[[784,260,334,39]]" d="M782.000 258.000 L1120.000 258.000 L1120.000 301.000 L782.000 301.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

</figure>

</div>

## Inspect the crystal structure

Check the cell, space group and atom sites. The [structure model](../physics/crystallography.md) describes their meaning.

<div class="gui-viewer" markdown="1">


=== "Structures"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select the structure whose cell and atom sites you want to inspect.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/07-structure-loaded.png?v=e86feaa85788" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Structures"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Structures"><title>Structures</title><defs><clipPath id="gui-clip-07-structure-loaded-overview-structures-list"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/07-structure-loaded.png?v=e86feaa85788" width="1480" height="800" clip-path="url(#gui-clip-07-structure-loaded-overview-structures-list)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="07-structure-loaded-overview-structures-list-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M782.000 166.000 L1468.000 166.000 L1468.000 248.000 L782.000 248.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the structure view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/07-structure-loaded.png?v=e86feaa85788" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-07-structure-loaded-overview-workflow-structure-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/07-structure-loaded.png?v=e86feaa85788" width="1480" height="800" clip-path="url(#gui-clip-07-structure-loaded-overview-workflow-structure-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="07-structure-loaded-overview-workflow-structure-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M653.203 -2.000 L729.453 -2.000 L729.453 79.000 L653.203 79.000 Z" /></svg></a>

    </figure>

</div>

The structure appears in the main view and the Structures count is one.

## Create an experiment

Open **Experiment → Main**, expand **Experiments** and choose **Create experiment**.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Add an experiment and choose its measurement type.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/09-experiment-import.png?v=ac436627cb35" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create experiment"><title>Create experiment</title><defs><clipPath id="gui-clip-09-experiment-import-overview-experiments-create"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-experiment-import.png?v=ac436627cb35" width="1480" height="800" clip-path="url(#gui-clip-09-experiment-import-overview-experiments-create)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-experiment-import-overview-experiments-create-1" data-gui-area="sidebar" data-gui-parts="[[1016,260,218,39]]" d="M1014.000 258.000 L1236.000 258.000 L1236.000 301.000 L1014.000 301.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

</figure>

</div>

## Choose the measurement type

Before loading data, choose **Powder**, **Constant wavelength**, **Neutron** for this measurement. [Experiment labels](../user-guide/glossary.md#experiment-types-and-labels) distinguish these attributes.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the sample form, beam mode and probe before loading data.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/09-experiment-type.png?v=17aa5f3f168e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: experimentType"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="experimentType"><title>experimentType</title><defs><clipPath id="gui-clip-09-experiment-type-overview-experimentType"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-experiment-type.png?v=17aa5f3f168e" width="1480" height="800" clip-path="url(#gui-clip-09-experiment-type-overview-experimentType)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-experiment-type-overview-experimentType-1" data-gui-area="sidebar" data-gui-parts="[[784,260,682,126]]" d="M782.000 258.000 L1468.000 258.000 L1468.000 388.000 L782.000 388.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

</figure>

</div>

## Load measured data

Select the experiment, open **Load ▾**, choose **From file…** under **Measured data**, and select **spodi.xye**. Check the measured range and intensities.

<div class="gui-viewer" markdown="1">


=== "Measured-data file"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Load the observed intensities for this experiment.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-experiment-data.png?v=44087322755a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Measured-data file"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Measured-data file"><title>Measured-data file</title><defs><clipPath id="gui-clip-09-experiment-data-overview-experiments-loadData-0"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-experiment-data.png?v=44087322755a" width="1480" height="800" clip-path="url(#gui-clip-09-experiment-data-overview-experiments-loadData-0)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-experiment-data-overview-experiments-loadData-0-1" data-gui-area="sidebar" data-gui-parts="[[974,207,56.078125,39]]" d="M972.000 205.000 L1032.078 205.000 L1032.078 248.000 L972.000 248.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the experiment view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-experiment-data.png?v=44087322755a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-09-experiment-data-overview-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-experiment-data.png?v=44087322755a" width="1480" height="800" clip-path="url(#gui-clip-09-experiment-data-overview-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-experiment-data-overview-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

</div>

## Set the wavelength

Expand **Instrument** and enter **1.54822 Å** for this measurement. Use the wavelength from your own measurement when working with other data.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Enter the wavelength used for this measurement, in ångströms.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/09-wavelength.png?v=41d495cc956e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Wavelength"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Wavelength"><title>Wavelength</title><defs><clipPath id="gui-clip-09-wavelength-overview-instrument-setup_wavelength"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-wavelength.png?v=41d495cc956e" width="1480" height="800" clip-path="url(#gui-clip-09-wavelength-overview-instrument-setup_wavelength)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-wavelength-overview-instrument-setup_wavelength-1" data-gui-area="sidebar" data-gui-parts="[[784,322,339.25,56]]" d="M782.000 320.000 L1125.250 320.000 L1125.250 380.000 L782.000 380.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

</figure>

</div>

## Choose the peak profile

Expand **Peak profile**, choose the profile shown below and set its starting coefficients. These values are starting estimates; refine the widths later. See [constant-wavelength profiles](../physics/profiles/cw.md).

<div class="gui-viewer" markdown="1">


=== "Profile"

    <div class="gui-viewer" markdown="1">


    === "Profile"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Choose the peak-shape model for this measurement.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/09-profile.png?v=ffebe50fb1aa" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Profile"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Profile"><title>Profile</title><defs><clipPath id="gui-clip-09-profile-overview-walkthrough-09-profile-peak-type"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-profile.png?v=ffebe50fb1aa" width="1480" height="800" clip-path="url(#gui-clip-09-profile-overview-walkthrough-09-profile-peak-type)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-profile-overview-walkthrough-09-profile-peak-type-1" data-gui-area="sidebar" data-gui-parts="[[784,294,682,56]]" d="M782.000 292.000 L1468.000 292.000 L1468.000 352.000 L782.000 352.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

        </figure>

    === "<span class='gui-fa' aria-hidden='true'>&#63007;</span>Peak profile"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Choose the peak shape and edit its profile parameters.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/09-profile.png?v=ffebe50fb1aa" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Peak profile"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Peak profile"><title>Peak profile</title><defs><clipPath id="gui-clip-09-profile-overview-walkthrough-09-profile-group-peak"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-profile.png?v=ffebe50fb1aa" width="1480" height="800" clip-path="url(#gui-clip-09-profile-overview-walkthrough-09-profile-group-peak)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-profile-overview-walkthrough-09-profile-group-peak-1" data-gui-area="sidebar" data-gui-parts="[[770,245,710,189]]" d="M768.000 243.000 L1482.000 243.000 L1482.000 436.000 L768.000 436.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

        </figure>

    </div>

=== "U"

    <div class="gui-viewer" markdown="1">

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Set the starting Gaussian width coefficient U.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-profile-broad-gauss-u.png?v=ae67a309247e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: U"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="U"><title>U</title><defs><clipPath id="gui-clip-09-profile-broad-gauss-u-overview-walkthrough-09-profile-broad-gauss-u-peak-broad_gauss_u"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-profile-broad-gauss-u.png?v=ae67a309247e" width="1480" height="800" clip-path="url(#gui-clip-09-profile-broad-gauss-u-overview-walkthrough-09-profile-broad-gauss-u-peak-broad_gauss_u)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-profile-broad-gauss-u-overview-walkthrough-09-profile-broad-gauss-u-peak-broad_gauss_u-1" data-gui-area="sidebar" data-gui-parts="[[784,364,133.60000000000002,56]]" d="M782.000 362.000 L919.600 362.000 L919.600 422.000 L782.000 422.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

    </div>

=== "V"

    <div class="gui-viewer" markdown="1">

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Set the starting Gaussian width coefficient V.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-profile-broad-gauss-v.png?v=372ed28354f0" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: V"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="V"><title>V</title><defs><clipPath id="gui-clip-09-profile-broad-gauss-v-overview-walkthrough-09-profile-broad-gauss-v-peak-broad_gauss_v"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-profile-broad-gauss-v.png?v=372ed28354f0" width="1480" height="800" clip-path="url(#gui-clip-09-profile-broad-gauss-v-overview-walkthrough-09-profile-broad-gauss-v-peak-broad_gauss_v)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-profile-broad-gauss-v-overview-walkthrough-09-profile-broad-gauss-v-peak-broad_gauss_v-1" data-gui-area="sidebar" data-gui-parts="[[921.1,364,133.60000000000002,56]]" d="M919.100 362.000 L1056.700 362.000 L1056.700 422.000 L919.100 422.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

    </div>

=== "W"

    <div class="gui-viewer" markdown="1">

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Set the starting Gaussian width coefficient W.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-profile-broad-gauss-w.png?v=372ed28354f0" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: W"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="W"><title>W</title><defs><clipPath id="gui-clip-09-profile-broad-gauss-w-overview-walkthrough-09-profile-broad-gauss-w-peak-broad_gauss_w"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-profile-broad-gauss-w.png?v=372ed28354f0" width="1480" height="800" clip-path="url(#gui-clip-09-profile-broad-gauss-w-overview-walkthrough-09-profile-broad-gauss-w-peak-broad_gauss_w)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-profile-broad-gauss-w-overview-walkthrough-09-profile-broad-gauss-w-peak-broad_gauss_w-1" data-gui-area="sidebar" data-gui-parts="[[1058.2,364,133.5999999999999,56]]" d="M1056.200 362.000 L1193.800 362.000 L1193.800 422.000 L1056.200 422.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

    </div>

</div>

## Exclude unwanted regions

Expand **Excluded regions**, use **Append new region** and enter 0 to 12°, 137.5 to 180° for this example. Exclude a region for a stated reason, rather than to hide disagreement.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Set the boundaries of regions omitted from fitting.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/09-exclusion-1.png?v=7bea815a44cc" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Excluded intervals"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Excluded intervals"><title>Excluded intervals</title><defs><clipPath id="gui-clip-09-exclusion-1-overview-excludedRegions-list"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-exclusion-1.png?v=7bea815a44cc" width="1480" height="800" clip-path="url(#gui-clip-09-exclusion-1-overview-excludedRegions-list)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-exclusion-1-overview-excludedRegions-list-1" data-gui-area="sidebar" data-gui-parts="[[784,336,682,117]]" d="M782.000 334.000 L1468.000 334.000 L1468.000 455.000 L782.000 455.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

</figure>

</div>

## Estimate the background

On **Experiment → Extra**, expand **Background estimation** and set the number of points to **21**. Return to **Main**, expand **Background** and press **Estimate**. Inspect the baseline between peaks before refining. See [background models](../physics/background.md).

<div class="gui-viewer" markdown="1">


=== "Estimation settings"

    <div class="gui-viewer" markdown="1">

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Choose the number of background anchors before estimating the baseline.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-background-settings.png?v=7f72c2e3105b" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Number of points"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Number of points"><title>Number of points</title><defs><clipPath id="gui-clip-09-background-settings-overview-walkthrough-09-background-settings-background_estimate-n_points"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-background-settings.png?v=7f72c2e3105b" width="1480" height="800" clip-path="url(#gui-clip-09-background-settings-overview-walkthrough-09-background-settings-background_estimate-n_points)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-background-settings-overview-walkthrough-09-background-settings-background_estimate-n_points-1" data-gui-area="sidebar" data-gui-parts="[[1126.75,168,339.25,56]]" d="M1124.750 166.000 L1468.000 166.000 L1468.000 226.000 L1124.750 226.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

    </div>

=== "Estimated background"

    <div class="gui-viewer" markdown="1">


    === "Background values"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Inspect or edit the values in the selected representation.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/09-background-estimate.png?v=181ef1b9d27e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background values"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background values"><title>Background values</title><defs><clipPath id="gui-clip-09-background-estimate-overview-walkthrough-09-background-estimate-background-rows"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-background-estimate.png?v=181ef1b9d27e" width="1480" height="800" clip-path="url(#gui-clip-09-background-estimate-overview-walkthrough-09-background-estimate-background-rows)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-background-estimate-overview-walkthrough-09-background-estimate-background-rows-1" data-gui-area="sidebar" data-gui-parts="[[784,210,682,337.5]]" d="M782.000 208.000 L1468.000 208.000 L1468.000 549.500 L782.000 549.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

        </figure>

    === "<span class='gui-fa' aria-hidden='true'>&#61648;</span>Estimate"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Estimate a starting background from the measured pattern.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/09-background-estimate.png?v=181ef1b9d27e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Estimate"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Estimate"><title>Estimate</title><defs><clipPath id="gui-clip-09-background-estimate-overview-walkthrough-09-background-estimate-background-estimate"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-background-estimate.png?v=181ef1b9d27e" width="1480" height="800" clip-path="url(#gui-clip-09-background-estimate-overview-walkthrough-09-background-estimate-background-estimate)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-background-estimate-overview-walkthrough-09-background-estimate-background-estimate-1" data-gui-area="sidebar" data-gui-parts="[[1248,508.5,218,39]]" d="M1246.000 506.500 L1468.000 506.500 L1468.000 549.500 L1246.000 549.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

        </figure>

    </div>

</div>

## Inspect the starting pattern

Compare peak positions, widths, intensities and the residual. Correct the experiment setup before freeing more parameters.

<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the experiment view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-10-experiment-loaded-overview-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" width="1480" height="800" clip-path="url(#gui-clip-10-experiment-loaded-overview-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="10-experiment-loaded-overview-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-10-experiment-loaded-overview-workflow-experiment-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/10-experiment-loaded.png?v=181ef1b9d27e" width="1480" height="800" clip-path="url(#gui-clip-10-experiment-loaded-overview-workflow-experiment-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="10-experiment-loaded-overview-workflow-experiment-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M725.453 -2.000 L814.359 -2.000 L814.359 79.000 L725.453 79.000 Z" /></svg></a>

    </figure>

</div>

The measured pattern, calculated curve, reflection marks and residual are visible.

## Fit the scale and cell

Open **Analysis → Main**. Use the **free** header to fix all parameters. Filter by `scale`, choose **free → Free · all …**, then repeat for `length_a`. Clear the filters, press **Fit**, inspect the result and close the popup.

<div class="gui-viewer" markdown="1">


=== "Free parameters"

    <div class="gui-viewer" markdown="1">


    === "Parameters"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Inspect values, uncertainties, bounds and the free parameter set.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/12-analysis-choose.png?v=3b3bf7972e3f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Parameters"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Parameters"><title>Parameters</title><defs><clipPath id="gui-clip-12-analysis-choose-overview-walkthrough-12-analysis-choose-group-parameters"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-analysis-choose.png?v=3b3bf7972e3f" width="1480" height="800" clip-path="url(#gui-clip-12-analysis-choose-overview-walkthrough-12-analysis-choose-group-parameters)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-analysis-choose-overview-walkthrough-12-analysis-choose-group-parameters-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 730.500 L768.000 730.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

        </figure>

    === "Free parameters"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Open the free header menu to fix or free the parameters matching the current filters.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/12-analysis-choose.png?v=3b3bf7972e3f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Free parameters"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Free parameters"><title>Free parameters</title><defs><clipPath id="gui-clip-12-analysis-choose-overview-walkthrough-12-analysis-choose-parameters-freeHeader"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-analysis-choose.png?v=3b3bf7972e3f" width="1480" height="800" clip-path="url(#gui-clip-12-analysis-choose-overview-walkthrough-12-analysis-choose-parameters-freeHeader)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-analysis-choose-overview-walkthrough-12-analysis-choose-parameters-freeHeader-1" data-gui-area="sidebar" data-gui-parts="[[1411,231,50,39]]" d="M1409.000 229.000 L1463.000 229.000 L1463.000 272.000 L1409.000 272.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

        </figure>

    </div>

=== "Result"

    <div class="gui-viewer" markdown="1">


    === "Main workspace"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/12-fit-scale-cell.png?v=b28c30f79661" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-fit-scale-cell.png?v=b28c30f79661" width="1480" height="800" clip-path="url(#gui-clip-12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

        </figure>

    === "Parameters"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Inspect values, uncertainties, bounds and the free parameter set.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/12-fit-scale-cell.png?v=b28c30f79661" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Parameters"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Parameters"><title>Parameters</title><defs><clipPath id="gui-clip-12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-group-parameters"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-fit-scale-cell.png?v=b28c30f79661" width="1480" height="800" clip-path="url(#gui-clip-12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-group-parameters)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-group-parameters-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 730.500 L768.000 730.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

        </figure>

    </div>

</div>

## Refine widths and calibration

Keep the scale and cell free. Repeat the filter-and-free action for `broad_gauss_` and `calib_twotheta_offset` to add the Gaussian widths and 2θ offset. Clear the filters and press **Fit** again. Inspect the peak shapes and residual before continuing.

<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/12-fit-profile.png?v=407b17609d9c" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-12-fit-profile-overview-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-fit-profile.png?v=407b17609d9c" width="1480" height="800" clip-path="url(#gui-clip-12-fit-profile-overview-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-fit-profile-overview-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Parameters"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect values, uncertainties, bounds and the free parameter set.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/12-fit-profile.png?v=407b17609d9c" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Parameters"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Parameters"><title>Parameters</title><defs><clipPath id="gui-clip-12-fit-profile-overview-group-parameters"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-fit-profile.png?v=407b17609d9c" width="1480" height="800" clip-path="url(#gui-clip-12-fit-profile-overview-group-parameters)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-fit-profile-overview-group-parameters-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M768.000 117.000 L1482.000 117.000 L1482.000 730.500 L768.000 730.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

</div>

## Refine the structural model

Repeat the filter-and-free action for `background` and `fract_` to add background values and independent atom coordinates. Clear the filters. Keep displacement parameters fixed in this first fit; their [advanced refinement](displacement.md) requires additional physical checks. Press **Fit**, inspect the outcome and close the result popup. Symmetry-related quantities remain linked. See [refinement](../physics/rietveld.md) and [fit assessment](../user-guide/analysis-workflow/analysis.md#fit-quality).

<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-workflow-analysis-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-workflow-analysis-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-workflow-analysis-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/13-analysis-basic.png?v=8f3e20271fa5" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M-2.000 756.000 L1482.000 756.000 L1482.000 802.000 L-2.000 802.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

    </figure>

</div>

<!-- learning-comparison -->
<div class="gui-viewer" markdown="1">

=== "Starting model"

    <p class="gui-view-description">Compare the starting calculation with the measured pattern. The residual shows their difference.</p>

    <figure class="ed-interface-preview" data-interface-hero>
    <a class="gui-image-link" href="../assets/learning/gui/initial.svg?v=4afbcb4e121a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Starting model"><svg class="gui-capture" viewBox="0 0 1000 540" width="1000" height="540" role="img" aria-label="Starting model"><title>Starting model</title><defs><clipPath id="interface-initial"><rect y="0" width="1000" height="540" rx="12" /></clipPath></defs><image href="../assets/learning/gui/initial.svg?v=4afbcb4e121a" width="1000" height="540" clip-path="url(#interface-initial)" /><rect class="gui-image-frame" y="0" width="1000" height="540" rx="12" /></svg></a>
    </figure>

=== "Refined model"

    <p class="gui-view-description">After refinement, compare the same peaks and residual on exactly the same axes and scale.</p>

    <figure class="ed-interface-preview" data-interface-hero>
    <a class="gui-image-link" href="../assets/learning/gui/refined.svg?v=5f3eef38dea3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Refined model"><svg class="gui-capture" viewBox="0 0 1000 540" width="1000" height="540" role="img" aria-label="Refined model"><title>Refined model</title><defs><clipPath id="interface-refined"><rect y="0" width="1000" height="540" rx="12" /></clipPath></defs><image href="../assets/learning/gui/refined.svg?v=5f3eef38dea3" width="1000" height="540" clip-path="url(#interface-refined)" /><rect class="gui-image-frame" y="0" width="1000" height="540" rx="12" /></svg></a>
    </figure>

</div>

<!-- /learning-comparison -->

Check the fit status, agreement factors and parameter uncertainties before continuing.

## Inspect correlations

Choose **Correlations** in the main view. Strong correlations show parameters that are difficult to distinguish using these observations; review the free set and physical model.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/12-correlations.png?v=1227e60c9095" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-12-correlations-overview-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-correlations.png?v=1227e60c9095" width="1480" height="800" clip-path="url(#gui-clip-12-correlations-overview-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-correlations-overview-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M810.359 -2.000 L882.203 -2.000 L882.203 79.000 L810.359 79.000 Z" /></svg></a>

</figure>

</div>

## Review the report

Open **Report**. Check the fitted structure, measurement and results, then choose the report contents and export format.

<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the report view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-14-report-basic-overview-workflow-report-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-workflow-report-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-workflow-report-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M-2.000 75.000 L772.000 75.000 L772.000 760.000 L-2.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-14-report-basic-overview-workflow-report-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-workflow-report-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-workflow-report-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M768.000 117.000 L768.000 117.000 L768.000 75.000 L815.516 75.000 L815.516 117.000 L1482.000 117.000 L1482.000 760.000 L768.000 760.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-14-report-basic-overview-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/14-report-basic.png?v=d30351136ef3" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M-2.000 756.000 L1482.000 756.000 L1482.000 802.000 L-2.000 802.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M878.203 -2.000 L940.453 -2.000 L940.453 79.000 L878.203 79.000 Z" /></svg></a>

    </figure>

</div>

## Save the project

Return to **Project** and choose **Save project as…**. Keep the complete project as a folder or zip archive; the report is a separate export.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the output format and whether to save a copy.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-project-save.png?v=6668eba38bd5" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save options"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save options"><title>Save options</title><defs><clipPath id="gui-clip-guide-project-save-overview-walkthrough-save-project-saveChoice"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-project-save.png?v=6668eba38bd5" width="1480" height="800" clip-path="url(#gui-clip-guide-project-save-overview-walkthrough-save-project-saveChoice)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-save-overview-walkthrough-save-project-saveChoice-1" data-gui-area="main" data-gui-parts="[[607,354,111.84375,93]]" d="M605.000 352.000 L720.844 352.000 L720.844 449.000 L605.000 449.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M593.469 -2.000 L657.203 -2.000 L657.203 79.000 L593.469 79.000 Z" /></svg></a>

</figure>

</div>

!!! note "Keep the project as well as the report"

    A report is an export of the result. Keep the saved project to reopen the model, change parameters or repeat the fit. In the browser, [check the save location](browser.md#open-and-save-files).

## Try it

Change the cell length **a** slightly on **Structure** and watch the peak positions move. Use **Undo** to restore the fitted model.

??? tip "Where to look"

    Expand **Cell** on **Structure → Main**. A cell change affects peak positions; compare several peaks across the pattern.

## Continue with the same project

Open the saved project in [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../python/examples/index.md){ .ed-interface-link .ed-icon-label } or run it from the [<span class="ed-interface-icons" aria-hidden="true">:lucide-square-terminal:</span> <span class="ed-icon-text">Command Line</span>](../cli/examples/index.md){ .ed-interface-link .ed-icon-label }. Try [joint refinement](refine.md) or a [scan](scans.md) when you are ready for several measurements.
