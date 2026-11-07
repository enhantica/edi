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
<a class="gui-image-link" href="../assets/gui/y2o3/01-home.png?v=245f39cc72ad" data-gui-dark="9c512eb0c6c4" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Start"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Start"><title>Start</title><defs><clipPath id="gui-clip-01-home-overview-home-start"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/01-home.png?v=245f39cc72ad" data-gui-dark="9c512eb0c6c4" width="1480" height="800" clip-path="url(#gui-clip-01-home-overview-home-start)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="01-home-overview-home-start-1" data-gui-area="main" data-gui-parts="[[573,404,334,39]]" d="M574.000 409.000 Q574.000 405.000 578.000 405.000 L902.000 405.000 Q906.000 405.000 906.000 409.000 L906.000 438.000 Q906.000 442.000 902.000 442.000 L578.000 442.000 Q574.000 442.000 574.000 438.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[542,0,53.46875,77]]" d="M543.000 5.000 Q543.000 1.000 547.000 1.000 L590.469 1.000 Q594.469 1.000 594.469 5.000 L594.469 72.000 Q594.469 76.000 590.469 76.000 L547.000 76.000 Q543.000 76.000 543.000 72.000 Z" /></svg></a>

</figure>

</div>

## Create a project

Choose **Create a new project**.

<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61525;</span>Create a new project"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Open the project-details form.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/02-project-start.png?v=09c8828c2662" data-gui-dark="09769fd0b124" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create a new project"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create a new project"><title>Create a new project</title><defs><clipPath id="gui-clip-02-project-start-overview-project-create"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/02-project-start.png?v=09c8828c2662" data-gui-dark="09769fd0b124" width="1480" height="800" clip-path="url(#gui-clip-02-project-start-overview-project-create)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="02-project-start-overview-project-create-1" data-gui-area="sidebar" data-gui-parts="[[784,168,334,39]]" d="M785.000 173.000 Q785.000 169.000 789.000 169.000 L1113.000 169.000 Q1117.000 169.000 1117.000 173.000 L1117.000 202.000 Q1117.000 206.000 1113.000 206.000 L789.000 206.000 Q785.000 206.000 785.000 202.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "<span class='gui-fa' aria-hidden='true'>&#61749;</span>Get started"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Create a project or open an existing one.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/02-project-start.png?v=09c8828c2662" data-gui-dark="09769fd0b124" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Get started"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Get started"><title>Get started</title><defs><clipPath id="gui-clip-02-project-start-overview-group-getStarted"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/02-project-start.png?v=09c8828c2662" data-gui-dark="09769fd0b124" width="1480" height="800" clip-path="url(#gui-clip-02-project-start-overview-group-getStarted)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="02-project-start-overview-group-getStarted-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,155]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 269.000 Q1479.000 273.000 1475.000 273.000 L775.000 273.000 Q771.000 273.000 771.000 269.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

</div>

## Enter project details

Give the analysis a name, title and description, choose where to keep it, then confirm.

<div class="gui-viewer" markdown="1">


=== "Name"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use a short project identifier.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/03-project-details.png?v=0c7f705c9c4b" data-gui-dark="8eb31bafd097" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Name"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Name"><title>Name</title><defs><clipPath id="gui-clip-03-project-details-overview-createProject-name"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/03-project-details.png?v=0c7f705c9c4b" data-gui-dark="8eb31bafd097" width="1480" height="800" clip-path="url(#gui-clip-03-project-details-overview-createProject-name)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="03-project-details-overview-createProject-name-1" data-gui-area="main" data-gui-parts="[[495,238,490,35]]" d="M496.000 243.000 Q496.000 239.000 500.000 239.000 L980.000 239.000 Q984.000 239.000 984.000 243.000 L984.000 268.000 Q984.000 272.000 980.000 272.000 L500.000 272.000 Q496.000 272.000 496.000 268.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "Title"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Give the analysis a descriptive title.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/03-project-details.png?v=0c7f705c9c4b" data-gui-dark="8eb31bafd097" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Title"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Title"><title>Title</title><defs><clipPath id="gui-clip-03-project-details-overview-createProject-title"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/03-project-details.png?v=0c7f705c9c4b" data-gui-dark="8eb31bafd097" width="1480" height="800" clip-path="url(#gui-clip-03-project-details-overview-createProject-title)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="03-project-details-overview-createProject-title-1" data-gui-area="main" data-gui-parts="[[495,306,490,35]]" d="M496.000 311.000 Q496.000 307.000 500.000 307.000 L980.000 307.000 Q984.000 307.000 984.000 311.000 L984.000 336.000 Q984.000 340.000 980.000 340.000 L500.000 340.000 Q496.000 340.000 496.000 336.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "Description"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Record the sample, measurement and purpose.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/03-project-details.png?v=0c7f705c9c4b" data-gui-dark="8eb31bafd097" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Description"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Description"><title>Description</title><defs><clipPath id="gui-clip-03-project-details-overview-createProject-description"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/03-project-details.png?v=0c7f705c9c4b" data-gui-dark="8eb31bafd097" width="1480" height="800" clip-path="url(#gui-clip-03-project-details-overview-createProject-description)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="03-project-details-overview-createProject-description-1" data-gui-area="main" data-gui-parts="[[495,442,490,71]]" d="M496.000 447.000 Q496.000 443.000 500.000 443.000 L980.000 443.000 Q984.000 443.000 984.000 447.000 L984.000 508.000 Q984.000 512.000 980.000 512.000 L500.000 512.000 Q496.000 512.000 496.000 508.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "Location"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Choose where the project will be saved.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/03-project-details.png?v=0c7f705c9c4b" data-gui-dark="8eb31bafd097" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Location"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Location"><title>Location</title><defs><clipPath id="gui-clip-03-project-details-overview-createProject-location"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/03-project-details.png?v=0c7f705c9c4b" data-gui-dark="8eb31bafd097" width="1480" height="800" clip-path="url(#gui-clip-03-project-details-overview-createProject-location)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="03-project-details-overview-createProject-location-1" data-gui-area="main" data-gui-parts="[[495,546,490,35]]" d="M496.000 551.000 Q496.000 547.000 500.000 547.000 L980.000 547.000 Q984.000 547.000 984.000 551.000 L984.000 576.000 Q984.000 580.000 980.000 580.000 L500.000 580.000 Q496.000 580.000 496.000 576.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

</div>

## Inspect the project

Check the project details before adding a structure and measurement.

<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the project view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/04-project-created.png?v=0c03c435c4ef" data-gui-dark="50046285829c" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-04-project-created-overview-workflow-project-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/04-project-created.png?v=0c03c435c4ef" data-gui-dark="50046285829c" width="1480" height="800" clip-path="url(#gui-clip-04-project-created-overview-workflow-project-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="04-project-created-overview-workflow-project-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/04-project-created.png?v=0c03c435c4ef" data-gui-dark="50046285829c" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-04-project-created-overview-workflow-project-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/04-project-created.png?v=0c03c435c4ef" data-gui-dark="50046285829c" width="1480" height="800" clip-path="url(#gui-clip-04-project-created-overview-workflow-project-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="04-project-created-overview-workflow-project-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M771.000 124.000 Q771.000 120.000 771.000 116.000 L771.000 82.000 Q771.000 78.000 775.000 78.000 L808.516 78.000 Q812.516 78.000 812.516 82.000 L812.516 116.000 Q812.516 120.000 816.516 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 753.000 Q1479.000 757.000 1475.000 757.000 L775.000 757.000 Q771.000 757.000 771.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

    </figure>

</div>

The Project page now shows your project name and details.

## Load the structure

Open **Structure → Main**, expand **Structures**, choose **Load structure from file** and select **y2o3.cif**.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Import the structure file for this example.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/06-structure-import.png?v=c595280f443d" data-gui-dark="ac26e9abc62f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load structure"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load structure"><title>Load structure</title><defs><clipPath id="gui-clip-06-structure-import-overview-structures-load"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/06-structure-import.png?v=c595280f443d" data-gui-dark="ac26e9abc62f" width="1480" height="800" clip-path="url(#gui-clip-06-structure-import-overview-structures-load)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="06-structure-import-overview-structures-load-1" data-gui-area="sidebar" data-gui-parts="[[784,260,218,39]]" d="M785.000 265.000 Q785.000 261.000 789.000 261.000 L997.000 261.000 Q1001.000 261.000 1001.000 265.000 L1001.000 294.000 Q1001.000 298.000 997.000 298.000 L789.000 298.000 Q785.000 298.000 785.000 294.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

</figure>

</div>

## Inspect the crystal structure

Check the cell, space group and atom sites. The [structure model](../physics/crystallography.md) describes their meaning.

<div class="gui-viewer" markdown="1">


=== "Structures"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Select the structure whose cell and atom sites you want to inspect.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/07-structure-loaded.png?v=050641bffd59" data-gui-dark="020be33b72ad" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Structures"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Structures"><title>Structures</title><defs><clipPath id="gui-clip-07-structure-loaded-overview-structures-list"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/07-structure-loaded.png?v=050641bffd59" data-gui-dark="020be33b72ad" width="1480" height="800" clip-path="url(#gui-clip-07-structure-loaded-overview-structures-list)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="07-structure-loaded-overview-structures-list-1" data-gui-area="sidebar" data-gui-parts="[[784,168,682,78]]" d="M785.000 173.000 Q785.000 169.000 789.000 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 241.000 Q1465.000 245.000 1461.000 245.000 L789.000 245.000 Q785.000 245.000 785.000 241.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the structure view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/07-structure-loaded.png?v=050641bffd59" data-gui-dark="020be33b72ad" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-07-structure-loaded-overview-workflow-structure-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/07-structure-loaded.png?v=050641bffd59" data-gui-dark="020be33b72ad" width="1480" height="800" clip-path="url(#gui-clip-07-structure-loaded-overview-workflow-structure-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="07-structure-loaded-overview-workflow-structure-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[655.203125,0,72.25,77]]" d="M656.203 5.000 Q656.203 1.000 660.203 1.000 L722.453 1.000 Q726.453 1.000 726.453 5.000 L726.453 72.000 Q726.453 76.000 722.453 76.000 L660.203 76.000 Q656.203 76.000 656.203 72.000 Z" /></svg></a>

    </figure>

</div>

The structure appears in the main view and the Structures count is one.

## Create an experiment

Open **Experiment → Main**, expand **Experiments** and choose **Create experiment**.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Add an experiment and choose its measurement type.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/09-experiment-import.png?v=6a5194ba3e17" data-gui-dark="b8719b9a4f04" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Create experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Create experiment"><title>Create experiment</title><defs><clipPath id="gui-clip-09-experiment-import-overview-experiments-create"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-experiment-import.png?v=6a5194ba3e17" data-gui-dark="b8719b9a4f04" width="1480" height="800" clip-path="url(#gui-clip-09-experiment-import-overview-experiments-create)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-experiment-import-overview-experiments-create-1" data-gui-area="sidebar" data-gui-parts="[[1016,260,218,39]]" d="M1017.000 265.000 Q1017.000 261.000 1021.000 261.000 L1229.000 261.000 Q1233.000 261.000 1233.000 265.000 L1233.000 294.000 Q1233.000 298.000 1229.000 298.000 L1021.000 298.000 Q1017.000 298.000 1017.000 294.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

</figure>

</div>

## Choose the measurement type

Before loading data, choose **Powder**, **Constant wavelength**, **Neutron** for this measurement. [Experiment labels](../user-guide/glossary.md#experiment-types-and-labels) distinguish these attributes.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the sample form, beam mode and probe before loading data.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/09-experiment-type.png?v=2ab4be40cd60" data-gui-dark="4d29f85c32be" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: experimentType"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="experimentType"><title>experimentType</title><defs><clipPath id="gui-clip-09-experiment-type-overview-experimentType"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-experiment-type.png?v=2ab4be40cd60" data-gui-dark="4d29f85c32be" width="1480" height="800" clip-path="url(#gui-clip-09-experiment-type-overview-experimentType)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-experiment-type-overview-experimentType-1" data-gui-area="sidebar" data-gui-parts="[[784,260,682,126]]" d="M785.000 265.000 Q785.000 261.000 789.000 261.000 L1461.000 261.000 Q1465.000 261.000 1465.000 265.000 L1465.000 381.000 Q1465.000 385.000 1461.000 385.000 L789.000 385.000 Q785.000 385.000 785.000 381.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

</figure>

</div>

## Load measured data

Choose **Load data…** in the experiment row and select **spodi.xye**. Check the measured range and intensities.

<div class="gui-viewer" markdown="1">


=== "<span class='gui-fa' aria-hidden='true'>&#61587;</span>Load experiment"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Import the experiment file, including measured intensities and instrument settings.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-experiment-data.png?v=a2eea7199d0b" data-gui-dark="f7b51bc541d7" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Load experiment"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Load experiment"><title>Load experiment</title><defs><clipPath id="gui-clip-09-experiment-data-overview-experiments-load"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-experiment-data.png?v=a2eea7199d0b" data-gui-dark="f7b51bc541d7" width="1480" height="800" clip-path="url(#gui-clip-09-experiment-data-overview-experiments-load)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-experiment-data-overview-experiments-load-1" data-gui-area="sidebar" data-gui-parts="[[784,400,218,39]]" d="M785.000 405.000 Q785.000 401.000 789.000 401.000 L997.000 401.000 Q1001.000 401.000 1001.000 405.000 L1001.000 434.000 Q1001.000 438.000 997.000 438.000 L789.000 438.000 Q785.000 438.000 785.000 434.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the experiment view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-experiment-data.png?v=a2eea7199d0b" data-gui-dark="f7b51bc541d7" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-09-experiment-data-overview-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-experiment-data.png?v=a2eea7199d0b" data-gui-dark="f7b51bc541d7" width="1480" height="800" clip-path="url(#gui-clip-09-experiment-data-overview-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-experiment-data-overview-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

</div>

## Set the wavelength

Expand **Instrument** and enter **1.54822 Å** for this measurement. Use the wavelength from your own measurement when working with other data.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Enter the wavelength used for this measurement, in ångströms.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/09-wavelength.png?v=9e698b2f357d" data-gui-dark="6064dfd27edf" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Wavelength"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Wavelength"><title>Wavelength</title><defs><clipPath id="gui-clip-09-wavelength-overview-instrument-setup_wavelength"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-wavelength.png?v=9e698b2f357d" data-gui-dark="6064dfd27edf" width="1480" height="800" clip-path="url(#gui-clip-09-wavelength-overview-instrument-setup_wavelength)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-wavelength-overview-instrument-setup_wavelength-1" data-gui-area="sidebar" data-gui-parts="[[784,322.0000000000093,339.25,56]]" d="M785.000 327.000 Q785.000 323.000 789.000 323.000 L1118.250 323.000 Q1122.250 323.000 1122.250 327.000 L1122.250 373.000 Q1122.250 377.000 1118.250 377.000 L789.000 377.000 Q785.000 377.000 785.000 373.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

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
        <a class="gui-image-link" href="../assets/gui/y2o3/09-profile.png?v=7355f359cd0a" data-gui-dark="7e610bb4e7a9" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Profile"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Profile"><title>Profile</title><defs><clipPath id="gui-clip-09-profile-overview-walkthrough-09-profile-peak-type"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-profile.png?v=7355f359cd0a" data-gui-dark="7e610bb4e7a9" width="1480" height="800" clip-path="url(#gui-clip-09-profile-overview-walkthrough-09-profile-peak-type)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-profile-overview-walkthrough-09-profile-peak-type-1" data-gui-area="sidebar" data-gui-parts="[[784,294.0000000000047,682,56]]" d="M785.000 299.000 Q785.000 295.000 789.000 295.000 L1461.000 295.000 Q1465.000 295.000 1465.000 299.000 L1465.000 345.000 Q1465.000 349.000 1461.000 349.000 L789.000 349.000 Q785.000 349.000 785.000 345.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

        </figure>

    === "<span class='gui-fa' aria-hidden='true'>&#63007;</span>Peak profile"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Choose the peak shape and edit its profile parameters.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/09-profile.png?v=7355f359cd0a" data-gui-dark="7e610bb4e7a9" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Peak profile"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Peak profile"><title>Peak profile</title><defs><clipPath id="gui-clip-09-profile-overview-walkthrough-09-profile-group-peak"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-profile.png?v=7355f359cd0a" data-gui-dark="7e610bb4e7a9" width="1480" height="800" clip-path="url(#gui-clip-09-profile-overview-walkthrough-09-profile-group-peak)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-profile-overview-walkthrough-09-profile-group-peak-1" data-gui-area="sidebar" data-gui-parts="[[770,245.00000000000472,710,189]]" d="M771.000 250.000 Q771.000 246.000 775.000 246.000 L1475.000 246.000 Q1479.000 246.000 1479.000 250.000 L1479.000 429.000 Q1479.000 433.000 1475.000 433.000 L775.000 433.000 Q771.000 433.000 771.000 429.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

        </figure>

    </div>

=== "U"

    <div class="gui-viewer" markdown="1">

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Set the starting Gaussian width coefficient U.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-profile-broad-gauss-u.png?v=85d60f2046f5" data-gui-dark="64dddfc57ebc" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: U"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="U"><title>U</title><defs><clipPath id="gui-clip-09-profile-broad-gauss-u-overview-walkthrough-09-profile-broad-gauss-u-peak-broad_gauss_u"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-profile-broad-gauss-u.png?v=85d60f2046f5" data-gui-dark="64dddfc57ebc" width="1480" height="800" clip-path="url(#gui-clip-09-profile-broad-gauss-u-overview-walkthrough-09-profile-broad-gauss-u-peak-broad_gauss_u)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-profile-broad-gauss-u-overview-walkthrough-09-profile-broad-gauss-u-peak-broad_gauss_u-1" data-gui-area="sidebar" data-gui-parts="[[784,364.0000000000047,133.60000000000002,56]]" d="M785.000 369.000 Q785.000 365.000 789.000 365.000 L912.600 365.000 Q916.600 365.000 916.600 369.000 L916.600 415.000 Q916.600 419.000 912.600 419.000 L789.000 419.000 Q785.000 419.000 785.000 415.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

    </div>

=== "V"

    <div class="gui-viewer" markdown="1">

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Set the starting Gaussian width coefficient V.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-profile-broad-gauss-v.png?v=0e095a167d97" data-gui-dark="566ec091b91a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: V"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="V"><title>V</title><defs><clipPath id="gui-clip-09-profile-broad-gauss-v-overview-walkthrough-09-profile-broad-gauss-v-peak-broad_gauss_v"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-profile-broad-gauss-v.png?v=0e095a167d97" data-gui-dark="566ec091b91a" width="1480" height="800" clip-path="url(#gui-clip-09-profile-broad-gauss-v-overview-walkthrough-09-profile-broad-gauss-v-peak-broad_gauss_v)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-profile-broad-gauss-v-overview-walkthrough-09-profile-broad-gauss-v-peak-broad_gauss_v-1" data-gui-area="sidebar" data-gui-parts="[[921.1,364.0000000000047,133.60000000000002,56]]" d="M922.100 369.000 Q922.100 365.000 926.100 365.000 L1049.700 365.000 Q1053.700 365.000 1053.700 369.000 L1053.700 415.000 Q1053.700 419.000 1049.700 419.000 L926.100 419.000 Q922.100 419.000 922.100 415.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

    </div>

=== "W"

    <div class="gui-viewer" markdown="1">

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Set the starting Gaussian width coefficient W.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-profile-broad-gauss-w.png?v=0e095a167d97" data-gui-dark="566ec091b91a" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: W"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="W"><title>W</title><defs><clipPath id="gui-clip-09-profile-broad-gauss-w-overview-walkthrough-09-profile-broad-gauss-w-peak-broad_gauss_w"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-profile-broad-gauss-w.png?v=0e095a167d97" data-gui-dark="566ec091b91a" width="1480" height="800" clip-path="url(#gui-clip-09-profile-broad-gauss-w-overview-walkthrough-09-profile-broad-gauss-w-peak-broad_gauss_w)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-profile-broad-gauss-w-overview-walkthrough-09-profile-broad-gauss-w-peak-broad_gauss_w-1" data-gui-area="sidebar" data-gui-parts="[[1058.2,364.0000000000047,133.5999999999999,56]]" d="M1059.200 369.000 Q1059.200 365.000 1063.200 365.000 L1186.800 365.000 Q1190.800 365.000 1190.800 369.000 L1190.800 415.000 Q1190.800 419.000 1186.800 419.000 L1063.200 419.000 Q1059.200 419.000 1059.200 415.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

    </div>

</div>

## Exclude unwanted regions

Expand **Excluded regions**, use **Append new region** and enter 0 to 12°, 137.5 to 180° for this example. Exclude a region for a stated reason, rather than to hide disagreement.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Set the boundaries of regions omitted from fitting.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/09-exclusion-1.png?v=d09098225c32" data-gui-dark="f1e027e5c403" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Excluded intervals"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Excluded intervals"><title>Excluded intervals</title><defs><clipPath id="gui-clip-09-exclusion-1-overview-excludedRegions-list"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-exclusion-1.png?v=d09098225c32" data-gui-dark="f1e027e5c403" width="1480" height="800" clip-path="url(#gui-clip-09-exclusion-1-overview-excludedRegions-list)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-exclusion-1-overview-excludedRegions-list-1" data-gui-area="sidebar" data-gui-parts="[[784,336,682,117]]" d="M785.000 341.000 Q785.000 337.000 789.000 337.000 L1461.000 337.000 Q1465.000 337.000 1465.000 341.000 L1465.000 448.000 Q1465.000 452.000 1461.000 452.000 L789.000 452.000 Q785.000 452.000 785.000 448.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

</figure>

</div>

## Estimate the background

On **Experiment → Extra**, expand **Background estimation** and set the number of points to **21**. Return to **Main**, expand **Background** and press **Estimate**. Inspect the baseline between peaks before refining. See [background models](../physics/background.md).

<div class="gui-viewer" markdown="1">


=== "Estimation settings"

    <div class="gui-viewer" markdown="1">

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Choose the number of background anchors before estimating the baseline.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/09-background-settings.png?v=0fa5f5a47bfb" data-gui-dark="e5ae18f11f11" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Number of points"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Number of points"><title>Number of points</title><defs><clipPath id="gui-clip-09-background-settings-overview-walkthrough-09-background-settings-background_estimate-n_points"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-background-settings.png?v=0fa5f5a47bfb" data-gui-dark="e5ae18f11f11" width="1480" height="800" clip-path="url(#gui-clip-09-background-settings-overview-walkthrough-09-background-settings-background_estimate-n_points)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-background-settings-overview-walkthrough-09-background-settings-background_estimate-n_points-1" data-gui-area="sidebar" data-gui-parts="[[1126.75,168,339.25,56]]" d="M1127.750 173.000 Q1127.750 169.000 1131.750 169.000 L1461.000 169.000 Q1465.000 169.000 1465.000 173.000 L1465.000 219.000 Q1465.000 223.000 1461.000 223.000 L1131.750 223.000 Q1127.750 223.000 1127.750 219.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

    </div>

=== "Estimated background"

    <div class="gui-viewer" markdown="1">


    === "Background values"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Inspect or edit the values in the selected representation.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/09-background-estimate.png?v=651886ead43e" data-gui-dark="fe826aa55edc" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Background values"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Background values"><title>Background values</title><defs><clipPath id="gui-clip-09-background-estimate-overview-walkthrough-09-background-estimate-background-rows"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-background-estimate.png?v=651886ead43e" data-gui-dark="fe826aa55edc" width="1480" height="800" clip-path="url(#gui-clip-09-background-estimate-overview-walkthrough-09-background-estimate-background-rows)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-background-estimate-overview-walkthrough-09-background-estimate-background-rows-1" data-gui-area="sidebar" data-gui-parts="[[784,210.00000000000932,682,337.5]]" d="M785.000 215.000 Q785.000 211.000 789.000 211.000 L1461.000 211.000 Q1465.000 211.000 1465.000 215.000 L1465.000 542.500 Q1465.000 546.500 1461.000 546.500 L789.000 546.500 Q785.000 546.500 785.000 542.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

        </figure>

    === "<span class='gui-fa' aria-hidden='true'>&#61648;</span>Estimate"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Estimate a starting background from the measured pattern.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/09-background-estimate.png?v=651886ead43e" data-gui-dark="fe826aa55edc" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Estimate"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Estimate"><title>Estimate</title><defs><clipPath id="gui-clip-09-background-estimate-overview-walkthrough-09-background-estimate-background-estimate"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/09-background-estimate.png?v=651886ead43e" data-gui-dark="fe826aa55edc" width="1480" height="800" clip-path="url(#gui-clip-09-background-estimate-overview-walkthrough-09-background-estimate-background-estimate)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="09-background-estimate-overview-walkthrough-09-background-estimate-background-estimate-1" data-gui-area="sidebar" data-gui-parts="[[1248,508.5000000000093,218,39]]" d="M1249.000 513.500 Q1249.000 509.500 1253.000 509.500 L1461.000 509.500 Q1465.000 509.500 1465.000 513.500 L1465.000 542.500 Q1465.000 546.500 1461.000 546.500 L1253.000 546.500 Q1249.000 546.500 1249.000 542.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

        </figure>

    </div>

</div>

## Inspect the starting pattern

Compare peak positions, widths, intensities and the residual. Correct the experiment setup before freeing more parameters.

<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the experiment view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/10-experiment-loaded.png?v=651886ead43e" data-gui-dark="fe826aa55edc" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-10-experiment-loaded-overview-workflow-experiment-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/10-experiment-loaded.png?v=651886ead43e" data-gui-dark="fe826aa55edc" width="1480" height="800" clip-path="url(#gui-clip-10-experiment-loaded-overview-workflow-experiment-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="10-experiment-loaded-overview-workflow-experiment-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/10-experiment-loaded.png?v=651886ead43e" data-gui-dark="fe826aa55edc" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-10-experiment-loaded-overview-workflow-experiment-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/10-experiment-loaded.png?v=651886ead43e" data-gui-dark="fe826aa55edc" width="1480" height="800" clip-path="url(#gui-clip-10-experiment-loaded-overview-workflow-experiment-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="10-experiment-loaded-overview-workflow-experiment-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M771.000 124.000 Q771.000 120.000 771.000 116.000 L771.000 82.000 Q771.000 78.000 775.000 78.000 L808.516 78.000 Q812.516 78.000 812.516 82.000 L812.516 116.000 Q812.516 120.000 816.516 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 753.000 Q1479.000 757.000 1475.000 757.000 L775.000 757.000 Q771.000 757.000 771.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[727.453125,0,84.90625,77]]" d="M728.453 5.000 Q728.453 1.000 732.453 1.000 L807.359 1.000 Q811.359 1.000 811.359 5.000 L811.359 72.000 Q811.359 76.000 807.359 76.000 L732.453 76.000 Q728.453 76.000 728.453 72.000 Z" /></svg></a>

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
        <a class="gui-image-link" href="../assets/gui/y2o3/12-analysis-choose.png?v=7cc4b1e2098c" data-gui-dark="5ece88585d9f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Parameters"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Parameters"><title>Parameters</title><defs><clipPath id="gui-clip-12-analysis-choose-overview-walkthrough-12-analysis-choose-group-parameters"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-analysis-choose.png?v=7cc4b1e2098c" data-gui-dark="5ece88585d9f" width="1480" height="800" clip-path="url(#gui-clip-12-analysis-choose-overview-walkthrough-12-analysis-choose-group-parameters)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-analysis-choose-overview-walkthrough-12-analysis-choose-group-parameters-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

        </figure>

    === "Free parameters"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Open the free header menu to fix or free the parameters matching the current filters.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/12-analysis-choose.png?v=7cc4b1e2098c" data-gui-dark="5ece88585d9f" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Free parameters"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Free parameters"><title>Free parameters</title><defs><clipPath id="gui-clip-12-analysis-choose-overview-walkthrough-12-analysis-choose-parameters-freeHeader"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-analysis-choose.png?v=7cc4b1e2098c" data-gui-dark="5ece88585d9f" width="1480" height="800" clip-path="url(#gui-clip-12-analysis-choose-overview-walkthrough-12-analysis-choose-parameters-freeHeader)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-analysis-choose-overview-walkthrough-12-analysis-choose-parameters-freeHeader-1" data-gui-area="sidebar" data-gui-parts="[[1386,231,75,39]]" d="M1387.000 236.000 Q1387.000 232.000 1391.000 232.000 L1456.000 232.000 Q1460.000 232.000 1460.000 236.000 L1460.000 265.000 Q1460.000 269.000 1456.000 269.000 L1391.000 269.000 Q1387.000 269.000 1387.000 265.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

        </figure>

    </div>

=== "Result"

    <div class="gui-viewer" markdown="1">


    === "Main workspace"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/12-fit-scale-cell.png?v=abf47776a93b" data-gui-dark="5e3e3605b0c0" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-fit-scale-cell.png?v=abf47776a93b" data-gui-dark="5e3e3605b0c0" width="1480" height="800" clip-path="url(#gui-clip-12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

        </figure>

    === "Parameters"

        <figure class="gui-figure" data-gui-figure>
        <p class="gui-view-description">Inspect values, uncertainties, bounds and the free parameter set.</p>
        <a class="gui-image-link" href="../assets/gui/y2o3/12-fit-scale-cell.png?v=abf47776a93b" data-gui-dark="5e3e3605b0c0" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Parameters"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Parameters"><title>Parameters</title><defs><clipPath id="gui-clip-12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-group-parameters"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-fit-scale-cell.png?v=abf47776a93b" data-gui-dark="5e3e3605b0c0" width="1480" height="800" clip-path="url(#gui-clip-12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-group-parameters)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-fit-scale-cell-overview-walkthrough-12-fit-scale-cell-group-parameters-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

        </figure>

    </div>

</div>

## Refine widths and calibration

Keep the scale and cell free. Repeat the filter-and-free action for `broad_gauss_` and `calib_twotheta_offset` to add the Gaussian widths and 2θ offset. Clear the filters and press **Fit** again. Inspect the peak shapes and residual before continuing.

<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/12-fit-profile.png?v=3adb58ea1e56" data-gui-dark="a6b151e00910" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-12-fit-profile-overview-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-fit-profile.png?v=3adb58ea1e56" data-gui-dark="a6b151e00910" width="1480" height="800" clip-path="url(#gui-clip-12-fit-profile-overview-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-fit-profile-overview-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Parameters"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect values, uncertainties, bounds and the free parameter set.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/12-fit-profile.png?v=3adb58ea1e56" data-gui-dark="a6b151e00910" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Parameters"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Parameters"><title>Parameters</title><defs><clipPath id="gui-clip-12-fit-profile-overview-group-parameters"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-fit-profile.png?v=3adb58ea1e56" data-gui-dark="a6b151e00910" width="1480" height="800" clip-path="url(#gui-clip-12-fit-profile-overview-group-parameters)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-fit-profile-overview-group-parameters-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,609.5]]" d="M771.000 124.000 Q771.000 120.000 775.000 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 723.500 Q1479.000 727.500 1475.000 727.500 L775.000 727.500 Q771.000 727.500 771.000 723.500 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

</div>

## Refine the structural model

Repeat the filter-and-free action for `background` and `fract_` to add background values and independent atom coordinates. Clear the filters. Keep displacement parameters fixed in this first fit; their [advanced refinement](structure/atomic-displacement.md) requires additional physical checks. Press **Fit**, inspect the outcome and close the result popup. Symmetry-related quantities remain linked. See [refinement](../physics/rietveld.md) and [fit assessment](../user-guide/analysis-workflow/analysis.md#fit-quality).

<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the analysis view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-workflow-analysis-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-workflow-analysis-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-workflow-analysis-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M771.000 124.000 Q771.000 120.000 771.000 116.000 L771.000 82.000 Q771.000 78.000 775.000 78.000 L808.516 78.000 Q812.516 78.000 812.516 82.000 L812.516 116.000 Q812.516 120.000 816.516 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 753.000 Q1479.000 757.000 1475.000 757.000 L775.000 757.000 Q771.000 757.000 771.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-13-analysis-basic-overview-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/13-analysis-basic.png?v=d21425890a21" data-gui-dark="70046ce6fa52" width="1480" height="800" clip-path="url(#gui-clip-13-analysis-basic-overview-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="13-analysis-basic-overview-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M1.000 763.000 Q1.000 759.000 5.000 759.000 L1475.000 759.000 Q1479.000 759.000 1479.000 763.000 L1479.000 795.000 Q1479.000 799.000 1475.000 799.000 L5.000 799.000 Q1.000 799.000 1.000 795.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

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
<a class="gui-image-link" href="../assets/gui/y2o3/12-correlations.png?v=72db3ad97bbb" data-gui-dark="5520f559a279" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-12-correlations-overview-workflow-analysis-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/12-correlations.png?v=72db3ad97bbb" data-gui-dark="5520f559a279" width="1480" height="800" clip-path="url(#gui-clip-12-correlations-overview-workflow-analysis-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="12-correlations-overview-workflow-analysis-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[812.359375,0,67.84375,77]]" d="M813.359 5.000 Q813.359 1.000 817.359 1.000 L875.203 1.000 Q879.203 1.000 879.203 5.000 L879.203 72.000 Q879.203 76.000 875.203 76.000 L817.359 76.000 Q813.359 76.000 813.359 72.000 Z" /></svg></a>

</figure>

</div>

## Review the report

Open **Report**. Check the fitted structure, measurement and results, then choose the report contents and export format.

<div class="gui-viewer" markdown="1">


=== "Main workspace"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Inspect the report view here. Its content changes with the active page and selection.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/14-report-basic.png?v=6f642d1c2fdb" data-gui-dark="59154d2fa211" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Main workspace"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Main workspace"><title>Main workspace</title><defs><clipPath id="gui-clip-14-report-basic-overview-workflow-report-mainContent"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/14-report-basic.png?v=6f642d1c2fdb" data-gui-dark="59154d2fa211" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-workflow-report-mainContent)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-workflow-report-mainContent-1" data-gui-area="main" data-gui-parts="[[0,77,770,681]]" d="M1.000 82.000 Q1.000 78.000 5.000 78.000 L765.000 78.000 Q769.000 78.000 769.000 82.000 L769.000 753.000 Q769.000 757.000 765.000 757.000 L5.000 757.000 Q1.000 757.000 1.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

=== "Sidebar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Use the enabled Main, Extra, Text and Settings tabs to inspect and edit this page.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/14-report-basic.png?v=6f642d1c2fdb" data-gui-dark="59154d2fa211" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Sidebar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Sidebar"><title>Sidebar</title><defs><clipPath id="gui-clip-14-report-basic-overview-workflow-report-manualSidebar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/14-report-basic.png?v=6f642d1c2fdb" data-gui-dark="59154d2fa211" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-workflow-report-manualSidebar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-workflow-report-manualSidebar-1" data-gui-area="sidebar" data-gui-parts="[[770,119,710,639],[770,77,43.515625,42]]" d="M771.000 124.000 Q771.000 120.000 771.000 116.000 L771.000 82.000 Q771.000 78.000 775.000 78.000 L808.516 78.000 Q812.516 78.000 812.516 82.000 L812.516 116.000 Q812.516 120.000 816.516 120.000 L1475.000 120.000 Q1479.000 120.000 1479.000 124.000 L1479.000 753.000 Q1479.000 757.000 1475.000 757.000 L775.000 757.000 Q771.000 757.000 771.000 753.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

=== "Status bar"

    <figure class="gui-figure" data-gui-figure>
    <p class="gui-view-description">Read project counts, messages, calculation and fitting state here.</p>
    <a class="gui-image-link" href="../assets/gui/y2o3/14-report-basic.png?v=6f642d1c2fdb" data-gui-dark="59154d2fa211" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Status bar"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Status bar"><title>Status bar</title><defs><clipPath id="gui-clip-14-report-basic-overview-statusBar"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/14-report-basic.png?v=6f642d1c2fdb" data-gui-dark="59154d2fa211" width="1480" height="800" clip-path="url(#gui-clip-14-report-basic-overview-statusBar)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="14-report-basic-overview-statusBar-1" data-gui-area="status" data-gui-parts="[[0,758,1480,42]]" d="M1.000 763.000 Q1.000 759.000 5.000 759.000 L1475.000 759.000 Q1479.000 759.000 1479.000 763.000 L1479.000 795.000 Q1479.000 799.000 1475.000 799.000 L5.000 799.000 Q1.000 799.000 1.000 795.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[880.203125,0,58.25,77]]" d="M881.203 5.000 Q881.203 1.000 885.203 1.000 L933.453 1.000 Q937.453 1.000 937.453 5.000 L937.453 72.000 Q937.453 76.000 933.453 76.000 L885.203 76.000 Q881.203 76.000 881.203 72.000 Z" /></svg></a>

    </figure>

</div>

## Save the project

Return to **Project** and choose **Save project as…**. Keep the complete project as a folder or zip archive; the report is a separate export.

<div class="gui-viewer" markdown="1">

<figure class="gui-figure" data-gui-figure>
<p class="gui-view-description">Choose the output format and whether to save a copy.</p>
<a class="gui-image-link" href="../assets/gui/y2o3/guide-project-save.png?v=27ae3b274a90" data-gui-dark="e2320beb11b7" data-gui-open aria-haspopup="dialog" aria-label="Enlarge screenshot: Save options"><svg class="gui-capture" data-gui-view="overview" viewBox="0 0 1480 800" width="1480" height="800" role="img" aria-label="Save options"><title>Save options</title><defs><clipPath id="gui-clip-guide-project-save-overview-walkthrough-save-project-saveChoice"><rect width="1480" height="800" rx="17.76" /></clipPath></defs><image href="../assets/gui/y2o3/guide-project-save.png?v=27ae3b274a90" data-gui-dark="e2320beb11b7" width="1480" height="800" clip-path="url(#gui-clip-guide-project-save-overview-walkthrough-save-project-saveChoice)" /><rect class="gui-image-frame" width="1480" height="800" rx="17.76" /><path class="is-active" data-gui-region="guide-project-save-overview-walkthrough-save-project-saveChoice-1" data-gui-area="main" data-gui-parts="[[607,354,111.84375,93]]" d="M608.000 359.000 Q608.000 355.000 612.000 355.000 L713.844 355.000 Q717.844 355.000 717.844 359.000 L717.844 442.000 Q717.844 446.000 713.844 446.000 L612.000 446.000 Q608.000 446.000 608.000 442.000 Z" /><path data-gui-navigation data-gui-area="navigation" data-gui-parts="[[595.46875,0,59.734375,77]]" d="M596.469 5.000 Q596.469 1.000 600.469 1.000 L650.203 1.000 Q654.203 1.000 654.203 5.000 L654.203 72.000 Q654.203 76.000 650.203 76.000 L600.469 76.000 Q596.469 76.000 596.469 72.000 Z" /></svg></a>

</figure>

</div>

!!! note "Keep the project as well as the report"

    A report is an export of the result. Keep the saved project to reopen the model, change parameters or repeat the fit. In the browser, [check the save location](browser.md#open-and-save-files).

## Try it

Change the cell length **a** slightly on **Structure** and watch the peak positions move. Use **Undo** to restore the fitted model.

??? tip "Where to look"

    Expand **Cell** on **Structure → Main**. A cell change affects peak positions; compare several peaks across the pattern.

## Continue with the same project

Open the saved project in [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../python/examples/index.md){ .ed-icon-label .ed-interface-link } or run it from the [<span class="ed-interface-icons" aria-hidden="true">:fa5-terminal:</span> <span class="ed-icon-text">Command Line</span>](../cli/examples/index.md){ .ed-icon-label .ed-interface-link }. Try [joint refinement](analysis/joint-fit-weights.md) or a [scan](scans.md) when you are ready for several measurements.
