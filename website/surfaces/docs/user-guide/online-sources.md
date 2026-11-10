---
icon: fa5/globe
---

# Online sources

EasyDiffraction can load structures, experiments, measured data and whole projects from the web. Each place it reads
from is an **online source**. Two are built in: the Crystallography Open Database (COD), for structures, and
EasyDiffraction's own collection, which holds the examples and the tutorial data. You can add your own collection, for
example your group's shared data.

## Use an online source

- **Application:** on the Structure or Experiment page, open **Load** and choose **From web…**. Pick a source, search,
  and press **Load** on a row.
- **Python:** `edi.load_collection("https://example.org/my-data")` reads a collection; `edi.list_data()` and
  `edi.download_data("pd-neut-cwl_lbco-hrpt")` list and download entries of EasyDiffraction's collection.
- **Command line:** `edi collection list`, `edi collection find ID` and `edi collection fetch ID`, each with
  `--source URL_OR_FOLDER` for another collection.

## Add your own source

1. Open **Preferences** and the **Projects** tab.
2. Under **Online sources**, press **Add online source**. A new row appears.
3. Type a name and the collection's base URL: the address that holds its `index.json`.

The switch at the end of a row hides a source from **From web…** without removing it; the minus button removes a
source you added. The two built-in sources can be switched off but not removed.

## How a collection is laid out

A collection is plain files behind one base URL, for example a GitHub repository or any static web server, with one
`index.json` at the top:

```text
index.json
structures/   structure files (CIF or .edi)
experiments/  experiment files (.edi)
data/         measured data (.xye, .dat, …)
projects/     whole projects, zipped
```

Only `index.json` is required to have that name and place; the folders are a convention. Every file the index lists
is read from its path relative to the base URL.

## The index format

`index.json` is an object with two keys: `"schema": "edi-data-index/1"` and `"entries"`, a list. Each entry
describes one thing to load:

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | A name unique in the collection, used to find and download the entry |
| `kind` | yes | `structure`, `experiment`, `data` or `project` |
| `files` | yes | One or more files, each with `path` (relative to the base URL) and `format`; `sha256` and `bytes` are checked when given |
| `name`, `description` | no | What the search results show |
| `formula`, `elements` | no | The chemical formula in Hill notation and its element symbols, for searching |
| `space_group`, `cell` | no | The space group and the six cell parameters of a structure |
| `radiation`, `technique`, `instrument`, `facility` | no | How an experiment or its data was measured |
| `source` | no | Who provides the entry |

A file path is made of folder and file names (letters, digits, `.`, `_`, `~` and `-`) joined by `/`, never starting
with `/` or containing `..`. A download whose size or digest differs from the index is refused.

## Example

This collection holds one structure, one experiment, its measured data and a whole project. Its files are in the
EasyDiffraction repository under
[`docs/user/collection-example`](https://github.com/enhantica/edi/tree/main/docs/user/collection-example).

```json
{
 "schema": "edi-data-index/1",
 "entries": [
  {
   "id": "lbco",
   "kind": "structure",
   "name": "La₀.₅Ba₀.₅CoO₃",
   "description": "Cubic perovskite, La and Ba sharing one site",
   "formula": "Ba Co La O",
   "elements": [
    "Ba",
    "Co",
    "La",
    "O"
   ],
   "space_group": "P m -3 m",
   "cell": [
    3.88,
    3.88,
    3.88,
    90.0,
    90.0,
    90.0
   ],
   "source": "EasyDiffraction",
   "files": [
    {
     "path": "structures/lbco.edi",
     "format": "edi",
     "sha256": "d1c245e00052e5ba22a07a5f26d645d97bc4576e369599467bfc85af224bfb04",
     "bytes": 530
    }
   ]
  },
  {
   "id": "lbco-hrpt",
   "kind": "experiment",
   "name": "La₀.₅Ba₀.₅CoO₃ at HRPT",
   "description": "Neutron powder pattern with its instrument and peak profile",
   "formula": "Ba Co La O",
   "elements": [
    "Ba",
    "Co",
    "La",
    "O"
   ],
   "radiation": "neutron",
   "technique": "powder constant wavelength",
   "instrument": "HRPT",
   "facility": "PSI",
   "source": "EasyDiffraction",
   "structures": [
    "lbco"
   ],
   "files": [
    {
     "path": "experiments/lbco-hrpt.edi",
     "format": "edi",
     "sha256": "f0c0e3839ffa3b6043992fb768eef3794ced6c869ceb7da52a57b8a387cac3f2",
     "bytes": 46359
    }
   ]
  },
  {
   "id": "lbco-hrpt-data",
   "kind": "data",
   "name": "La₀.₅Ba₀.₅CoO₃ at HRPT, measured data",
   "description": "The measured pattern alone, as x, y and its uncertainty",
   "formula": "Ba Co La O",
   "elements": [
    "Ba",
    "Co",
    "La",
    "O"
   ],
   "radiation": "neutron",
   "technique": "powder constant wavelength",
   "instrument": "HRPT",
   "facility": "PSI",
   "source": "EasyDiffraction",
   "files": [
    {
     "path": "data/lbco-hrpt.xye",
     "format": "xye",
     "sha256": "83c7f3d27d2e254367dd7dc3730261b9a5ebb811baaeed01fde050a7ba99be24",
     "bytes": 45384
    }
   ]
  },
  {
   "id": "lbco-hrpt-project",
   "kind": "project",
   "name": "La₀.₅Ba₀.₅CoO₃ project",
   "description": "A whole project: structure, experiment and analysis settings",
   "formula": "Ba Co La O",
   "elements": [
    "Ba",
    "Co",
    "La",
    "O"
   ],
   "radiation": "neutron",
   "technique": "powder constant wavelength",
   "instrument": "HRPT",
   "facility": "PSI",
   "source": "EasyDiffraction",
   "files": [
    {
     "path": "projects/lbco-hrpt.zip",
     "format": "zip",
     "sha256": "1e8ef36fff552e511ef10f66690b5eb4a50b02559a6a188421514cb48ec682fe",
     "bytes": 15884
    }
   ]
  }
 ]
}
```

You do not have to write the digests and sizes by hand. In a copy of the EasyDiffraction repository,
`python tools/data/build_collection.py index FOLDER` writes `index.json` for a folder laid out as above, reading
each file's facts and an optional `<file>.meta.json` beside it for the name and description, and
`python tools/data/build_collection.py check FOLDER` checks that the index and the files agree.
