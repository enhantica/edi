# Projects and files

<p class="ed-doc-lead">One readable project record across the application, Python and the command line.</p>

## The project model

A project contains structures, experiments and analysis settings. Experiments link the structures that contribute to their calculated pattern, with their own instrument, background and profile settings.

## Structures and experiments

A structure lives in `structures/<name>.edi`. Experimental blocks carry observations or a calculation range, together with their linked structures. The project loader validates that the pieces form a complete model.

## Analysis settings

The declared fitting mode and minimizer settings stay in the project. This makes the chosen analysis reproducible when you move between interfaces.

## Folders and archives

The desktop application works with local project locations. The browser exports a project archive through its download mechanism. Keep that editable project together with any report you share.
