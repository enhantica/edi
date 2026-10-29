#pragma once

#include <map>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

// In-house EDI (EasyDiffraction STAR) reader/writer (ADR-0012). MVP1 reads the
// EDI project — a small bounded CIF subset (comments, data_ blocks,
// `_category.item value` items, loop_ tables). The document model round-trips
// byte-stably: comments, blanks, item order, and loops are preserved, so
// to_text(parse_edi(text)) reproduces canonical EDI and is idempotent. Numeric
// fields carry the CIF standard-uncertainty / free-flag encoding, decoded by
// decode_su (the writer's spelling is save_project.cpp's, ADR-0092). Malformed input
// raises EdiParseError with a line number.

namespace crysta {

// Raised when an EDI document is malformed (a ValueError subclass in Python).
struct EdiParseError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

// One element of a block (or the preamble). Polymorphic so the writer round-trips
// without dynamic dispatch beyond the rendering virtual.
struct EdiElement {
    EdiElement() = default;
    EdiElement(const EdiElement&) = default;
    EdiElement(EdiElement&&) = default;
    EdiElement& operator=(const EdiElement&) = default;
    EdiElement& operator=(EdiElement&&) = default;
    virtual ~EdiElement() = default;
    virtual std::vector<std::string> render_lines() const = 0;
};

// A verbatim comment line (preserved for faithful round-trip).
struct EdiComment : EdiElement {
    std::string text;
    explicit EdiComment(std::string text);
    std::vector<std::string> render_lines() const override;
};

// A blank separator line (preserved so layout round-trips).
struct EdiBlank : EdiElement {
    std::vector<std::string> render_lines() const override;
};

// A single `_category.item value` entry; value kept as a raw token.
struct EdiItem : EdiElement {
    std::string key;
    std::string value;
    EdiItem(std::string key, std::string value);
    std::vector<std::string> render_lines() const override;
};

// A loop_ table: header data-names plus whitespace-split rows (raw tokens, delimiters kept).
// Relay C13-T12 (ADR-0071 item 3, the file plane): the constructor is the one way a loop exists —
// parsed, translated from CIF or built by the writer — and it checks every identity column the
// loop carries (crysta::identity_columns) after decoding each cell once: a value outside the
// representable domain, or two equal ids, is refused by name. The header and the rows are private
// and read-only afterwards, so no later edit can bypass the check.
//
// A loop is an admitted VALUE: it may be copied (a copy is the same checked loop, and a move
// copies too, leaving its source whole), but it can never be ASSIGNED. Assignment would replace
// the header and the rows one member at a time without the check, so a failure between the two
// could leave a header over rows it was never checked with (relay C13-T12 review 9 F1). The
// members are const for exactly that reason.
struct EdiItem;
struct EdiLoop;

// The CIF names of a block translated from a CIF (ADR-0106), so a refusal can name the declaration
// it is about. Reading a value settles nothing: the importer settles every declaration against
// the written experiment once it is built.
struct EdiReads {
    // Every `.edi` name of the translated block with the CIF name it was spelled as.
    std::map<std::string, std::string> origin;
    // The declarations given as unknown (`?` or `.`), by `.edi` name, each as written with its
    // token: a refusal over a row they leave incomplete names them.
    std::map<std::string, std::string> unknown;
};

struct EdiLoop : EdiElement {
    EdiLoop(std::vector<std::string> keys, std::vector<std::vector<std::string>> rows);
    const std::vector<std::string>& keys() const { return keys_; }
    const std::vector<std::vector<std::string>>& rows() const { return rows_; }
    std::vector<std::string> render_lines() const override;
    std::shared_ptr<EdiReads> reads;  // set on a loop translated from a CIF

   private:
    void require_identity_columns() const;
    // const: the value boundary above — no assignment exists to bypass the constructor's check.
    // NOLINTNEXTLINE(cppcoreguidelines-avoid-const-or-ref-data-members)
    const std::vector<std::string> keys_;
    // NOLINTNEXTLINE(cppcoreguidelines-avoid-const-or-ref-data-members)
    const std::vector<std::vector<std::string>> rows_;
};

static_assert(!std::is_copy_assignable_v<EdiLoop> && !std::is_move_assignable_v<EdiLoop>,
              "an admitted loop is never reassigned around its identity check");

// A data_<name> block and its ordered elements.
class EdiBlock {
   public:
    explicit EdiBlock(std::string name);

    std::string name;
    std::vector<std::shared_ptr<EdiElement>> elements;

    std::vector<std::shared_ptr<EdiItem>> items() const;
    std::vector<std::shared_ptr<EdiLoop>> loops() const;
    std::optional<std::string> get(const std::string& key) const;
    std::shared_ptr<EdiLoop> loop_with(const std::string& key) const;
    // Relay C13-T2 (ADR-0082 §6): every loop with a column whose tag starts with `prefix` (a
    // category's columns), so a loop is found by any of its columns, not only one marker.
    std::vector<std::shared_ptr<EdiLoop>> loops_with_prefix(std::string_view prefix) const;
    std::vector<std::string> render_lines() const;
    std::shared_ptr<EdiReads> reads;  // set on a block translated from a CIF
};

// A parsed EDI file: a preamble plus ordered data_ blocks.
class EdiDocument {
   public:
    std::vector<std::shared_ptr<EdiElement>> preamble;
    std::vector<std::shared_ptr<EdiBlock>> blocks;

    std::shared_ptr<EdiBlock> block(const std::string& name) const;
    // Expose the pre-block (header-only) items/loops as a synthetic block: an EasyDiffraction
    // project.edi / analysis.edi carries its items at top level with no data_ header, so they
    // land in the preamble; this reads them through the same get/loop_with API (ADR-0040).
    std::shared_ptr<EdiBlock> root() const;
    // The document's single data_ block (structure/experiment files); throws EdiParseError
    // when the document has no block or more than one.
    std::shared_ptr<EdiBlock> only_block() const;
    std::string to_text() const;
};

// Parse EDI text into an EdiDocument (round-trip stable). Raises EdiParseError on
// a malformed line (item without a value, loop without column names, a data row
// outside any loop, a numeric token that is not value(su)).
EdiDocument parse_edi(const std::string& text);

// The values of a CIF2 list token, `[a b c]` -> {"a", "b", "c"}, each a raw token (quotes kept). A
// file holds such a token only after the CIF 2.0 heading `#\#CIF_2.0` on its first line (parse_edi
// refuses one elsewhere). Throws EdiParseError on a token that is not one list, or that nests a
// list.
std::vector<std::string> list_items(const std::string& token);

// Decode a numeric token's value, uncertainty, and free flag (CIF SU encoding):
// "3.89(2)" → (3.89, 0.02, true); "3.89" → (3.89, nullopt, false).
std::tuple<double, std::optional<double>, bool> decode_su(const std::string& token);

// Parse a plain numeric EDI data token — the raw numeric fields a project loads that
// carry no (su): a measured intensity/TOF/sigma, a background or excluded-region
// bound, a joint-fit weight. Locale-independent and finite-checked like decode_su, so
// a non-finite inf/nan never enters the model outside the free-parameter path
// (I-0014 / I-0017). Throws EdiParseError on a malformed or non-finite token.
double parse_edi_number(const std::string& token);

// The axis a `_data_range` declaration generates: `min` plus whole steps of `step`, up to `max`.
// The loader builds a declared grid with it and the writer proves a written range regenerates the
// grid.
std::vector<double> generate_range_grid(double min, double max, double step);

}  // namespace crysta
