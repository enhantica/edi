# :fa5-download: Get data and tutorials

EasyDiffraction keeps its example structures, measured data and projects in one collection, the
same one the application's **Load ▾ From web…** reads. Python lists it and downloads what you name.

## List and download data

```python
import edi

edi.list_data()                       # every entry, numbered
edi.list_data('project')              # one kind: structure, experiment, data or project
path = edi.download_data('pd-neut-cwl_lbco-hrpt', destination='data')
```

`download_data` takes an entry's id, or its number in the last listing. Use the id in saved code,
since numbers follow the listing. It returns the downloaded file. A project archive is unpacked into
a folder named after the entry and its digest, and that folder is returned, ready for
`edi.Project.load`. Every file's size and SHA-256 are checked against the collection's index, and a
mismatch is refused. A file already downloaded and still matching is kept unless you pass
`overwrite=True`.

The collection is read from GitHub, with `data.easydiffraction.org` as the mirror when GitHub cannot
be reached. Set `EDI_COLLECTION` to a folder or URL, or pass `source=`, to read another collection.

## List and download tutorials

```python
edi.list_tutorials()
edi.download_tutorial('pd-neut-cwl_lbco-hrpt', destination='tutorials')
edi.download_tutorial(1, file_format='py')
edi.download_all_tutorials(destination='tutorials')
```

Tutorials come as Jupyter notebooks (`ipynb`, the default) or Python scripts (`py`), listed in their
learning order. Each one's first cell installs edi and gets its data.
