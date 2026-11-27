# Probes

Scripts that measure something once and print or record the result. They are not tests: nothing
under `tests/` runs them, pytest does not collect them, and CI does not call them. Each script
explains its own use in its module docstring.

## COD CIF import audit

Three files check how edi imports the structure CIFs of the
[Crystallography Open Database](https://www.crystallography.net/cod/) (COD):

| File                 | What it is                                                                  |
| -------------------- | --------------------------------------------------------------------------- |
| `cod_cif_audit.py`   | Imports a local folder of COD CIFs with one edi build and compares two runs |
| `cod_cif_census.py`  | Runs the same import over the whole COD catalogue, resumable, two builds    |
| `cod-cif-import.csv` | A committed result of `cod_cif_audit.py compare` for 809 COD entries        |

Both scripts need edi and Gemmi importable. Neither is run by a test, and no test downloads COD
data.

### What one import records

For each CIF, `cod_cif_audit.py` calls `edi.StructureFactory.from_cif_path` and then reads the
same file with Gemmi to list the fields the CIF leaves out and the value edi used instead
(cell lengths and angles, occupancy, element taken from the label, isotropic displacement).
The status is one of:

| Status                                | Meaning                                                      |
| ------------------------------------- | ------------------------------------------------------------ |
| `imported`                            | Imported, nothing missing from the source                    |
| `imported with defaults reported`     | Imported, some fields missing, and edi warned it used defaults |
| `imported with source fields absent`  | Imported, some fields missing, and edi did not warn          |
| `imported; source audit incomplete`   | Imported, but the Gemmi check could not match the model      |
| `refused`                             | edi raised an error; the detail column holds its message     |
| `timed out`, `process failed`         | The import took too long or crashed                          |

A status can end in `; no atom sites`. The census adds `probe failed` (the worker raised),
`pending` (not run yet) and `withheld by COD` (COD holds the coordinates back). `compare` writes
`not run` for an ID present in only one snapshot.

### The committed CSV

`cod-cif-import.csv` has one row per COD entry with these columns:

- `cod_entry_id`: the seven-digit COD ID.
- `initial_status`, `initial_detail`: the result with the baseline build.
- `status_after_fix`, `detail_after_fix`: the result with the candidate build.
- `source_url`: `https://www.crystallography.net/cod/<id>.cif@<revision>`, the exact COD
  revision that was imported. The scripts write this string; they do not fetch it.
- `cif_sha256`: the SHA-256 of the CIF bytes that were imported.

The IDs are 1000000 to 1000010, a few known controls (1000041, 1000236, 2000000, 3000000,
4000000, 5000000, 8000000, 9008506) and about 100 IDs from each of the COD ID prefixes listed in
the `cod_cif_audit.py` docstring.

Counts per outcome, baseline to candidate:

| `initial_status`                     | `status_after_fix`                | Rows |
| ------------------------------------ | --------------------------------- | ---: |
| `imported with source fields absent` | `imported with defaults reported` |  538 |
| `imported`                           | `imported`                        |  231 |
| `refused`                            | `refused`                         |   24 |
| `refused`                            | `imported with defaults reported` |   14 |
| `refused`                            | `imported`                        |    2 |
| Total                                |                                   |  809 |

Counted with:

```bash
python3 -c "import csv, collections; rows = list(csv.DictReader(open('tools/probes/cod-cif-import.csv'))); print(len(rows), collections.Counter((r['initial_status'], r['status_after_fix']) for r in rows).most_common())"
```

### What it shows and what it does not

It shows that, for the listed COD revisions and the two builds used, each entry either imports
or is refused with a stated reason, and which defaults edi applied. It does not show that the
imported values are right beyond the missing-field check, and it says nothing about COD entries
outside the list. The CSV is a record of one run, not a gate: nothing compares it with the
current code, so later importer changes are not reflected in it.

### Network use

`cod_cif_audit.py` makes no network requests. It reads `*.cif` files named by their seven-digit
ID from a local folder, and `snapshot` also runs `git rev-parse HEAD` in this checkout.

`cod_cif_census.py run` talks to `www.crystallography.net` over HTTPS only (any other scheme, or a
redirect away from HTTPS, is refused):

The archive is `https://www.crystallography.net/archives/2025/data/cod-rev297631-2025.02.07.zip`
and the live API is `https://www.crystallography.net/cod`.

| Request                                       | Used for                                                  |
| --------------------------------------------- | --------------------------------------------------------- |
| `HEAD` on the archive                         | Its size and ETag                                         |
| Ranged `GET` on the archive, `If-Match` ETag  | Reading the ZIP one window (`--window-mib`, 32) at a time |
| `GET <api>/result?id=<IDs>&format=zip&...`    | Entries the archive lacks, 100 per ZIP, halved on failure |
| `GET <api>/<id>.cif@<revision>`               | Single entries still missing after the batch ZIP          |

The live requests are spaced 10 seconds apart. `--archive` changes the archive URL and
`--live-base` points the live requests at an HTTPS mirror of the COD API.

Nothing is downloaded whole. Each archive window is held in memory, each CIF is written to a
temporary folder beside the database and deleted after both builds import it, and every result
goes into the SQLite database given by `--database`. Only CIFs whose `#$Revision:` header equals
the catalogue revision are imported; others are skipped and counted. The one exception is a
single `<id>.cif@<revision>` download whose header was copied from another COD entry, which is
checked by its `data_` block and `_cod_database_code` instead.

These parts run offline:

- `run --local-zip COD.zip` reads a local copy of the archive and makes no requests.
- `recheck` imports local CIF files with a newer build and stores the result beside the census
  row, after checking the revision and that the bytes match the census digest.
- `record-withheld DB FILE.tsv` stores the IDs COD withholds (tab-separated ID, revision, date).
- `export DB OUT.csv` writes one row per catalogue ID, with the columns above plus
  `rechecked_edi_commit`.

### Running the census

Inputs: a file of COD IDs, one per line; a COD revision CSV with `file` and `svnrevision` columns
(lines starting with `#` are skipped) that covers every ID; and two edi builds, each given as the
folder holding the `edi` package and the folder holding the `_edi` extension.

```bash
python tools/probes/cod_cif_census.py run --database census.sqlite \
    --ids cod-ids.txt --revisions cod-revisions.csv \
    --before-lib BASE/lib --before-extension BASE/ext \
    --after-lib CAND/lib --after-extension CAND/ext
python tools/probes/cod_cif_census.py export census.sqlite census.csv
```

To resume, run the same `run` command again. The database stores a hash of the ID and revision
list, the archive URL and a fingerprint of each build (its Python sources and extension binary),
and refuses to continue if any of them changed. Finished entries are skipped; timed out or failed
imports are tried again. Once the archive has been read through, its ETag is stored and later
runs go straight to the live requests. `--archive-only` stops after the archive, and
`--live-only` with `--live-ids FILE` limits the live requests to some IDs. The command exits 0
when no entry is left pending, 1 otherwise. `--jobs` (default 8) sets the number of parallel
import pairs and `--seconds` (default 60) the time allowed per import.

### Reproducing the committed CSV

The CSV comes from `cod_cif_audit.py`, not from the census:

1. Download each `source_url` into one folder as `<id>.cif` and check its SHA-256 against
   `cif_sha256`.
2. With the baseline build importable, run
   `python tools/probes/cod_cif_audit.py snapshot CACHE baseline.json`.
3. With the candidate build importable, run the same into `candidate.json`.
4. Run `python tools/probes/cod_cif_audit.py compare baseline.json candidate.json out.csv`.

`compare` refuses two snapshots whose bytes differ for the same ID. Each CIF is pinned by its COD
revision and digest. The builds are not named in the CSV: each JSON snapshot records the edi
commit, the extension's SHA-256, the Gemmi version and the linked crysta commit, but the snapshots
of the committed run are not in the repository.
