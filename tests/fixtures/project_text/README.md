# Dictionary and project-text references

`dictionary_reference.json` captures `data/dictionary/parameters.yaml` from the
revision and SHA-256 recorded in its `source` member. It supplies labels, units,
options, category order and input/output marks without calling either product's
display bridge. A packaged binary SDK need not include the original YAML.

Regenerate explicitly from the reviewed dictionary source:

```sh
python tests/fixtures/project_text/dictionary_reference.py \
  --generate /path/to/crysta/data/dictionary/parameters.yaml \
  --revision <full-source-commit>
```

With no generation flags the script reads the committed reference. Its optional
positional SDK path remains accepted for already-built Qt observers; it is not
used to discover a sibling checkout or replace the pinned reference at runtime.
