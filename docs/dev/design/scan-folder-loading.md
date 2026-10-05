# Loading a scan folder (design note, not built)

Today a scan's files are in the project's directory, declared by `_sequential_fit.data_dir`. Two
ways of pointing the app at a folder of scan data are planned; neither is built.

## A local folder

The user chooses a folder, and the project records it as its scan directory. The folder is listed,
not read: each file is read when it is shown or fitted, as for a scan inside the project
([ADR-0026](../adrs/0026-scan-datasets-and-scale.md)). Save As copies the files the project needs
into the saved project, so the saved project does not depend on the folder.

## A web link

The user gives a link to a folder listing. Two forms are possible:

- **Files on demand.** The app fetches the listing, then fetches each file when the fit reaches it
  or the user selects it, with the same read-ahead of up to four files. Nothing is downloaded up
  front, so a long scan starts at once.
- **Links only.** The project records the links and no data. A run fetches each file in turn.
  This keeps a saved project small, at the price of needing the link when the project is opened.

In the browser both go through the page, as other files do ([ADR-0023](../adrs/0023-web-build.md)).
What happens when a file cannot be fetched (retry, skip and mark the dataset failed) is to be
decided with the feature.
