# Removed absorption field census

The hidden census checks the live Python declarations, public model declarations
and each declared public surface. Historical removal metadata in the Python
manifest is retained; it is not a live member. JSON and notebook strings are
decoded before checking names. Missing or empty surfaces fail the census.

Only FullProf control inputs with a `.pcr`, `.inp` or `.new` extension and the
`COMM` plus `!Job Npr` header are exempt. Renaming an Edi project to one of those
extensions does not exempt it. Profiles, summaries and other output formats are
checked normally.

The surfaces include the parameter declarations and selectors, Python binding
sources and manifest, category census, QML and native app source, user docs and
rendered reference assets, the features list, examples, built-in tutorials, and
the project, tutorial, collection and parameter-reference generators. The
collection builder takes its projects from the checked CLI examples. This
source census does not fetch or attest an independently published collection.
