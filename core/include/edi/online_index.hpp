// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <string>
#include <vector>

/// The index of an online collection and the searches over it (ADR-0068). A collection is plain files behind one
/// base URL with an `index.json` at its root; every interface reads the same index. The Crystallography Open
/// Database is searched through its own query service; its answers are mapped onto the same entries.
namespace edi::online {

/// One file of an entry, relative to the collection's base URL.
struct File {
    std::string path;    ///< relative path, no leading slash, no `..`
    std::string format;  ///< cif, edi, xye, xy, dat, txt, csv, int, hkl, zip
    std::string sha256;  ///< the file's digest, hex, when the index records it
    long long bytes = -1;  ///< the file's size, when the index records it
};

/// One item: a structure, a full experiment, a measured data set or a whole project.
struct Entry {
    std::string id;           ///< stable within the collection
    std::string kind;         ///< structure, experiment, data or project; tutorial in the docs' tutorials index
    std::string name;         ///< a short title, may be empty
    std::string description;  ///< a sentence more, may be empty
    std::string formula;      ///< Hill notation, may be empty
    std::vector<std::string> elements;  ///< the elements present, Hill order; from the formula when it is given
    std::string space_group;  ///< Hermann-Mauguin, may be empty
    std::vector<double> cell; ///< a, b, c, alpha, beta, gamma, or empty
    std::string radiation;    ///< neutron or xray, experiments and data
    std::string technique;    ///< powder or single crystal, with constant wavelength or time-of-flight
    std::string instrument;   ///< for example HRPT
    std::string facility;     ///< for example PSI
    std::string source;       ///< where the entry comes from, for the results table
    std::string authors;      ///< "Smith, J.; Doe, A." as the publication lists them, may be empty
    std::string journal;      ///< the journal's name, may be empty
    std::string volume;       ///< may be empty
    std::string first_page;   ///< may be empty
    std::string year;         ///< may be empty
    std::string doi;          ///< without a scheme, may be empty
    std::vector<std::string> structures;  ///< an experiment's linked structures, by their entry ids; may be empty
    std::vector<File> files;  ///< at least one
};

/// A short reference to the entry's publication: "Smith et al., Phys. Rev. B 40, 34 (2026)" from the authors
/// (the first author's surname, "et al." for more than one), journal, volume, first page and year, each omitted
/// when empty; empty when the entry names no publication.
std::string short_reference(const Entry& entry);

/// The two parts of that reference: the authors ("Smith et al.") and the rest ("Phys. Rev. B 40, 34 (2026)"), with
/// `journal` in place of the entry's journal when given (its abbreviation). Either part may be empty.
struct Reference {
    std::string authors;
    std::string where;
};
Reference reference_parts(const Entry& entry, const std::string& journal = {});

/// Where the publication is read: `https://doi.org/<doi>` when the entry has a DOI, else empty.
std::string reference_url(const Entry& entry);

struct Index {
    std::string schema;  ///< edi-data-index/1
    std::vector<Entry> entries;
};

/// Parse an `index.json`; refuses a malformed document with the reason.
Index parse_index(const std::string& text);

/// The search fields; an empty field does not filter. `id` matches whole; `formula`, after Hill normalisation,
/// matches an entry holding every one of its elements, amounts ignored, with the exact Hill matches listed first
/// (owner, 2026-11-04), or only the exact ones when `formula_exact` is set (COD, which searched exactly already);
/// `elements` as a set the entry's elements must contain, `space_group` without spaces, the rest as substrings.
struct Query {
    std::string id, name, formula, elements, space_group, radiation, technique, instrument;
    bool formula_exact = false;
};

/// The entries of `kind` that match `query`, in index order.
std::vector<const Entry*> search(const Index& index, const std::string& kind, const Query& query);

/// The entry with `id`, or null.
const Entry* find(const Index& index, const std::string& id);

/// A chemical formula in Hill notation: carbon first, hydrogen second, the other elements alphabetically; without
/// carbon every element alphabetically. Counts of one are omitted. Refuses text that is not a formula.
std::string hill_formula(const std::string& formula);

/// The elements of a formula, each once, in Hill order.
std::vector<std::string> formula_elements(const std::string& formula);

/// COD's query URL for `query` at `base`, answering in `format`: "json" for the entries' details, "count" for
/// their number, "lst" for their ids one per line (COD's documented formats).
std::string cod_search_url(const std::string& base, const Query& query, const std::string& format = "json");

/// COD's query URL for the details of the entries `ids` name (a chunk of a long answer).
std::string cod_details_url(const std::string& base, const std::vector<std::string>& ids);

/// The element list's symbols, commas or semicolons read as spaces; refuses text that is not a list.
std::vector<std::string> element_list(const std::string& text);

/// The entries in a COD JSON answer; each structure's CIF sits at `<base>/<id>.cif`.
std::vector<Entry> cod_entries(const std::string& text);

}  // namespace edi::online
