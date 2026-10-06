// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_MODEL_HPP
#define EDI_MODEL_HPP

#include <algorithm>
#include <array>
#include <bit>
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <functional>
#include <map>
#include <atomic>
#include <memory>
#include <optional>
#include <ostream>
#include <set>
#include <stdexcept>
#include <filesystem>
#include <string>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

// ADR-0018: edi's tables are built from crysta's columns, table cells and row anchors, shipped
// as headers in the SDK. No engine type crosses here: the engine model stays behind the adapter.
#include "crysta/anchors.hpp"
#include "crysta/column.hpp"
#include "crysta/schema.hpp"
#include "crysta/stamped.hpp"

// edi's user-facing product model (ADR-0009): Qt-free, engine-free value types the Python surface
// (E02) mirrors from diffraction-lib. It is edi's own model, insulated from crysta's engine model
// (ADR-0003 pt 5); the crysta adapter (adapter.cpp) is the only place that touches the engine.
// covers the TOF-Jorgensen calculate() path.edi/CIF file I/O is, refinement.

#include "edi/parameter_spec.hpp"

namespace edi {

struct ExperimentBase;
struct Structure;
class Project;
struct Parameter;
// ADR-0020: the publication transaction, declared in edi/calculation.hpp.
struct WorkSnapshot;
struct WorkStamps;
struct CalculationResult;
enum class PublishOutcome : std::uint8_t;

namespace detail {

class KeyedBase;

// The membership record an ItemVec owns and its attached items share. Items hold it STRONGLY —
// ADR-0013 prohibits production weak references — and the collection revokes it (owner =
// nullptr) in its destructor and re-points it in its move operations, so a held item that outlives
// its collection (ADR-0012 §1) can never reach it.
struct Membership {
    const KeyedBase* owner = nullptr;
};

// ADR-0012: whether a row is held by its collection, as the row and each of its parameter
// categories see it — a share of the collection's membership record, which the collection sets on
// insertion and removes on removal. A row a collection once held stays marked, so a detached row
// (removed, or its collection destroyed) is distinguishable from one no collection ever held. The
// link belongs to the object that carries it, never to its value: a copy starts unlinked and an
// assignment keeps its own.
class RowLink {
   public:
    RowLink() = default;
    RowLink(const RowLink&) noexcept {}
    RowLink& operator=(const RowLink&) noexcept { return *this; }
    ~RowLink() = default;

    bool attached() const noexcept { return record_ != nullptr && record_->owner != nullptr; }
    bool detached() const noexcept { return held_ && !attached(); }
    const Membership* record() const noexcept { return record_.get(); }

    void link(const std::shared_ptr<Membership>& record) noexcept {
        record_ = record;
        held_ = true;
    }
    void unlink() noexcept { record_.reset(); }

   private:
    std::shared_ptr<Membership> record_;
    bool held_ = false;
};

// An object's identity as a calculation input — a process-unique number each row and data node is
// born with, which a copy does not share and an assignment renews. So a replacement or a whole
// assignment is a write the currentness record sees even when every value is equal
// (ExperimentBase::computed_current).
class Epoch {
   public:
    Epoch() noexcept : value_(next()) {}
    Epoch(const Epoch& /*other*/) noexcept : value_(next()) {}
    // NOLINTNEXTLINE(bugprone-unhandled-self-assignment,cert-oop54-cpp) — every assignment renews
    Epoch& operator=(const Epoch& /*other*/) noexcept {
        value_ = next();
        return *this;
    }
    ~Epoch() = default;
    std::uint64_t value() const noexcept { return value_; }

   private:
    static std::uint64_t next() noexcept {
        static std::atomic<std::uint64_t> counter{0};
        return counter.fetch_add(1, std::memory_order_relaxed) + 1;
    }
    std::uint64_t value_;
};

// ADR-0018: the row of an object's non-loop categories. Its token comes from the process-wide
// counter crysta's tables use and is never reused. The non-loop categories of one object are one
// row, split by category, and the token names that row in each. A copy is a new row with a new
// token, as every edi identity is new on a copy; an assignment replaces the row's content and
// keeps the target's token.
class CategoryRow {
   public:
    CategoryRow() noexcept = default;
    CategoryRow(const CategoryRow& /*other*/) noexcept {}
    // NOLINTNEXTLINE(bugprone-unhandled-self-assignment,cert-oop54-cpp) — keeps its own token
    CategoryRow& operator=(const CategoryRow& /*other*/) noexcept { return *this; }
    ~CategoryRow() = default;
    crysta::RowToken token() const noexcept { return token_; }

   private:
    crysta::RowToken token_ = crysta::next_row_token();
};

// ADR-0018 §1 and §4: a table's columns, as the cells of its rows reach them. A loop table stores
// every cell of its rows in a typed value column, `crysta::Column<V>`, one for each column of its
// schema (a parameter is five columns), in row order. `values` are those columns in schema order,
// each the `crysta::Column<V>` of its cell's value type; `columns` are their stamps, and `newest`
// is the newest write to any cell the table holds.
//
// The item of a row keeps a read image of the row's cells, as a field that holds a loop in one
// cell keeps a read image of the table behind it. The image is what a read by reference returns,
// so that reference stays valid and current for as long as the item lives: in a table, out of
// one, and in several. Every write to a cell writes the image and the cell's column in every
// table that holds the row, in one step (`RowHold::write`).
struct TableNotes {
    std::vector<void*> values;
    std::vector<std::uint64_t> columns;
    std::uint64_t newest = 0;

    void note(std::size_t column, std::uint64_t identity) noexcept {
        columns[column] = std::max(columns[column], identity);
        newest = std::max(newest, identity);
    }
};
// One holding of a row: the table, and the row's position in it.
struct Holding {
    TableNotes* table = nullptr;
    std::size_t row = 0;
};
// The tables that hold one row, with one entry for each time a table holds it: an unkeyed table
// admits a row that another table holds, and the same row twice (ADR-0012 §1). The cells of the
// row point here for as long as any table holds it.
struct RowHold : std::enable_shared_from_this<RowHold> {
    std::vector<Holding> tables;

    // A write of a cell: its value goes to the cell's column at every position the row has, in
    // every table that holds it, and each of those tables notes the write. `V` is the column's
    // value type. Writing a number, a flag or an optional of one cannot fail. Copying a text can
    // fail to allocate, and that ends the program rather than leave a column that disagrees with
    // its row.
    template <typename V>
    void write(std::size_t column, std::uint64_t identity, const V& value) const noexcept {
        for (const Holding& held : tables) {
            static_cast<crysta::Column<V>*>(held.table->values[column])->write(held.row, value);
            held.table->note(column, identity);
        }
    }
};
// The value type of a cell's column: the cell's own, except a flag, which a column holds as a
// byte, because a column's buffer is one contiguous array and a vector of flags is none.
template <typename U>
struct ColumnValue {
    using type = U;
};
template <>
struct ColumnValue<bool> {
    using type = std::uint8_t;
};
class CellHold;

// The table behind a recording field that holds a loop category in one cell: crysta's, for a
// vector of pairs and for a map. A carried loop (CarriedLoop) keeps its item names as one string
// column and its cells as one string column for each carried column.
struct CarriedNames {
    static constexpr bool kTable = true;
    crysta::Column<std::string> names;

    std::size_t rows() const noexcept { return names.size(); }
    static CarriedNames of(const std::vector<std::string>& image) {
        return CarriedNames{crysta::Column<std::string>(image)};
    }
};
struct CarriedCells {
    static constexpr bool kTable = true;
    std::vector<crysta::Column<std::string>> columns;

    std::size_t rows() const noexcept { return columns.empty() ? 0 : columns.front().size(); }
    static CarriedCells of(const std::vector<std::vector<std::string>>& image) {
        std::size_t width = 0;
        for (const std::vector<std::string>& row : image) {
            width = std::max(width, row.size());
        }
        std::vector<std::vector<std::string>> cells(width);
        for (std::vector<std::string>& column : cells) {
            column.reserve(image.size());
        }
        for (const std::vector<std::string>& row : image) {
            for (std::size_t index = 0; index < width; ++index) {
                cells[index].push_back(index < row.size() ? row[index] : std::string());
            }
        }
        CarriedCells made;
        made.columns.reserve(width);
        for (std::vector<std::string>& column : cells) {
            made.columns.emplace_back(std::move(column));
        }
        return made;
    }
};
template <typename T>
struct TableBehind {
    using type = crysta::detail::AggregateTable<T>;
};
template <>
struct TableBehind<std::vector<std::string>> {
    using type = CarriedNames;
};
template <>
struct TableBehind<std::vector<std::vector<std::string>>> {
    using type = CarriedCells;
};

template <typename T>
struct is_optional : std::false_type {};
template <typename U>
struct is_optional<std::optional<U>> : std::true_type {};

// ADR-0018 §5: whether a move took content from its source, asked of the value the destination
// holds afterwards. A move copies a number, a flag or an optional of one, and takes nothing from an
// empty text or container, so their sources stay as they were. A text or a container that is not
// empty, and an optional that holds one, was taken from its source, which the move left empty.
template <typename T>
bool move_took(const T& taken) noexcept {
    if constexpr (std::is_trivially_copyable_v<T>) {
        return false;
    } else if constexpr (is_optional<T>::value) {
        return taken.has_value() && move_took(*taken);
    } else if constexpr (requires { taken.empty(); }) {
        return !taken.empty();
    } else {
        return true;
    }
}

// ADR-0018 §5: gives `live` the content of the working copy a `modify` callback edited. `live`
// stays the object it is, and a map keeps the node of every key that stays, so a held `const`
// reference to the value, or to an element the edit kept, is valid and current.
template <typename T>
void take_edit(T& live, const T& work) {
    if constexpr (requires {
                      typename T::key_type;
                      typename T::mapped_type;
                  }) {
        for (auto row = live.begin(); row != live.end();) {
            row = work.find(row->first) != work.end() ? std::next(row) : live.erase(row);
        }
        for (const auto& [key, mapped] : work) {
            live.insert_or_assign(key, mapped);
        }
    } else {
        live = work;
    }
}

template <typename T>
concept arrow_reaches_value = is_optional<T>::value && std::is_class_v<typename T::value_type>;

template <typename T>
class Written;
template <typename T>
struct is_written : std::false_type {};
template <typename T>
struct is_written<Written<T>> : std::true_type {};
// Whether a type is a class template specialisation that names a recording field among its type
// arguments (a test framework's expression wrapper is one). A comparison with such a type would
// ask the field's comparison about itself, so the field does not offer one.
template <typename U>
struct wraps_written : std::false_type {};
template <template <typename...> class Wrapper, typename... A>
struct wraps_written<Wrapper<A...>>
    : std::bool_constant<(is_written<std::remove_cvref_t<A>>::value || ...)> {};

// A model field that records its own writes. Every assignment — an equal value, a
// self-assignment and a whole-object assignment included — gives the field a new write identity
// (`written()`); a copy is a new field with an identity of its own. The structure geometry's
// freshness record encodes these identities (geometry_inputs), so a write to a geometry input
// cannot be spelled, natively or from Python, without staling the geometry: the field has no
// other way in. Reads convert to `const T&`.
//
// ADR-0018: a recording field is the cell view of edi's tables. It holds its value and its write
// identity in place, always. While a table holds the field's row, every write also tells that
// table (detail::RowHold); only a table makes it so, and a copy of a held field is held by no
// table. It offers the reads a former plain member took — the conversion, `get()`, `->` and `*`,
// an optional's and a container's const members, comparison and streaming — so a read site
// compiles unchanged. No non-const reference to the value exists: a write is an assignment, a
// compound assignment, `set`, `modify`, or an optional's `reset` and `emplace`, and each records
// itself.
//
// A field that holds a loop category in one cell — a vector of pairs, a map, a carried loop — has
// that loop's table behind it (`table()`): `get()` returns a read image of the table, which the
// write that changes the table rebuilds.
template <typename T>
class Written {
   public:
    using value_type = T;

    Written() = default;
    explicit Written(T value) : state_(std::move(value)) {}
    // The same, `noexcept` wherever taking the value is: for a member's default initialiser, so
    // that the class keeps the default-construction trait the plain member gave it. The
    // constructor above keeps its signature.
    Written(std::in_place_t /*tag*/, T value) noexcept(std::is_nothrow_constructible_v<State, T>)
        : state_(std::move(value)) {}
    template <typename U>
        requires(!std::same_as<std::remove_cvref_t<U>, Written> && std::convertible_to<U, T>)
    Written& operator=(U&& value) {
        T next = std::forward<U>(value);
        state_.store(std::move(next));
        return *this;
    }
    // One braced value of a list assignment (below): it is made from one value and from nothing
    // else, so an empty list and a list of several values never select it.
    struct Braced {
        template <typename U>
            requires(!std::same_as<std::remove_cvref_t<U>, Written> && std::convertible_to<U, T>)
        Braced(U&& from) : value(std::forward<U>(from)) {}  // NOLINT(google-explicit-constructor)
        T value;
    };
    // The assignments a former plain member took from a braced list. A container takes a list of
    // its elements: `regions = {{1.0, 2.0}}`, `values = {1, 2.0}`, `values = {}`. A member that
    // is no container takes `x = {}` as the assignment of a new field, which holds a
    // value-initialised `T`, and one braced value as that value.
    template <typename C = T>
        requires(!is_optional<C>::value) &&
                std::constructible_from<C, std::initializer_list<typename C::value_type>>
    Written& operator=(std::initializer_list<typename C::value_type> values) {
        state_.store(T(values));
        return *this;
    }
    Written& operator=(Braced one) {
        state_.store(std::move(one.value));
        return *this;
    }
    // Compound writes, for the arithmetic fields.
    Written& operator+=(const T& other) { return *this = state_.v() + other; }
    Written& operator-=(const T& other) { return *this = state_.v() - other; }
    Written& operator*=(const T& other) { return *this = state_.v() * other; }
    Written& operator/=(const T& other) { return *this = state_.v() / other; }
    void set(T value) { state_.store(std::move(value)); }
    // Changes the value through `edit(T&)` and records the write, also when `edit` throws
    // part-way, because the value may already have changed.
    //
    // The callback edits a working copy, never the field's own value, and the field takes the
    // copy's content when the callback ends. So a pointer or a reference the callback keeps,
    // to the value or to an element of it, names a local of this call: nothing it writes later
    // reaches the field unrecorded.
    template <typename Edit>
    void modify(Edit&& edit) {
        T work = state_.v();
        std::exception_ptr thrown;  // what the callback threw: rethrown once the write is recorded
        try {
            std::forward<Edit>(edit)(work);
        } catch (...) {
            thrown = std::current_exception();  // the cell still takes the part it wrote
        }
        try {
            take_edit(state_.v(), work);
        } catch (...) {
            state_.retabulate();  // a part of the content may have arrived
            state_.renew();
            throw;
        }
        state_.retabulate();
        state_.renew();
        if (thrown) {
            std::rethrow_exception(thrown);
        }
    }

    operator const T&() const noexcept { return state_.v(); }  // NOLINT(google-explicit-constructor)
    const T& get() const noexcept { return state_.v(); }
    // The value's members. An optional of a class value (an axis: an optional vector) reaches the
    // contained value, as `std::optional`'s arrow did on the plain member; every other field
    // keeps the arrow it had, to the value itself.
    const T* operator->() const noexcept
        requires(!arrow_reaches_value<T>)
    {
        return &state_.v();
    }
    auto operator->() const noexcept
        requires arrow_reaches_value<T>
    {
        return std::addressof(*state_.v());
    }
    // The value, or an optional's contained value, read-only.
    decltype(auto) operator*() const {
        if constexpr (is_optional<T>::value) {
            return (*state_.v());
        } else {
            return (state_.v());
        }
    }
    // The identity of the last write.
    std::uint64_t written() const noexcept { return state_.w(); }
    // Whether a table holds this cell's row.
    bool bound() const noexcept { return state_.hold != nullptr; }
    // The table behind a field that holds a loop category in one cell: its columns, in row order.
    const typename TableBehind<T>::type& table() const noexcept
        requires TableBehind<T>::type::kTable
    {
        return state_.table;
    }

    // An optional's reads and its two writes.
    explicit operator bool() const noexcept
        requires is_optional<T>::value
    {
        return state_.v().has_value();
    }
    bool has_value() const noexcept
        requires is_optional<T>::value
    {
        return state_.v().has_value();
    }
    decltype(auto) value() const
        requires is_optional<T>::value
    {
        return state_.v().value();
    }
    template <typename U>
    auto value_or(U&& fallback) const
        requires is_optional<T>::value
    {
        return state_.v().value_or(std::forward<U>(fallback));
    }
    void reset() noexcept
        requires is_optional<T>::value
    {
        state_.v().reset();
        state_.renew();
    }
    // As `std::optional::emplace`: the old value is destroyed first, so a construction that throws
    // leaves the optional empty. That is a change too, and it is recorded on both exits.
    template <typename... Args>
    void emplace(Args&&... args)
        requires is_optional<T>::value
    {
        try {
            state_.v().emplace(std::forward<Args>(args)...);
        } catch (...) {
            state_.renew();
            throw;
        }
        state_.renew();
    }

    // A container's and a string's const reads.
    auto begin() const
        requires requires(const T& t) { t.begin(); }
    {
        return state_.v().begin();
    }
    auto end() const
        requires requires(const T& t) { t.end(); }
    {
        return state_.v().end();
    }
    auto size() const
        requires requires(const T& t) { t.size(); }
    {
        return state_.v().size();
    }
    bool empty() const
        requires requires(const T& t) { t.empty(); }
    {
        return state_.v().empty();
    }
    template <typename K>
    decltype(auto) operator[](K&& key) const
        requires requires(const T& t, K&& k) { t[std::forward<K>(k)]; }
    {
        return state_.v()[std::forward<K>(key)];
    }
    template <typename K>
    decltype(auto) at(K&& key) const
        requires requires(const T& t, K&& k) { t.at(std::forward<K>(k)); }
    {
        return state_.v().at(std::forward<K>(key));
    }
    template <typename K>
    auto find(K&& key) const
        requires requires(const T& t, K&& k) { t.find(std::forward<K>(k)); }
    {
        return state_.v().find(std::forward<K>(key));
    }
    template <typename K>
    auto count(K&& key) const
        requires requires(const T& t, K&& k) { t.count(std::forward<K>(k)); }
    {
        return state_.v().count(std::forward<K>(key));
    }
    decltype(auto) front() const
        requires requires(const T& t) { t.front(); }
    {
        return state_.v().front();
    }
    decltype(auto) back() const
        requires requires(const T& t) { t.back(); }
    {
        return state_.v().back();
    }
    template <typename... A>
    decltype(auto) cbegin(A&&... a) const
        requires requires(const T& held) { held.cbegin(std::forward<A>(a)...); }
    {
        return state_.v().cbegin(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) cend(A&&... a) const
        requires requires(const T& held) { held.cend(std::forward<A>(a)...); }
    {
        return state_.v().cend(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) rbegin(A&&... a) const
        requires requires(const T& held) { held.rbegin(std::forward<A>(a)...); }
    {
        return state_.v().rbegin(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) rend(A&&... a) const
        requires requires(const T& held) { held.rend(std::forward<A>(a)...); }
    {
        return state_.v().rend(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) crbegin(A&&... a) const
        requires requires(const T& held) { held.crbegin(std::forward<A>(a)...); }
    {
        return state_.v().crbegin(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) crend(A&&... a) const
        requires requires(const T& held) { held.crend(std::forward<A>(a)...); }
    {
        return state_.v().crend(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) data(A&&... a) const
        requires requires(const T& held) { held.data(std::forward<A>(a)...); }
    {
        return state_.v().data(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) capacity(A&&... a) const
        requires requires(const T& held) { held.capacity(std::forward<A>(a)...); }
    {
        return state_.v().capacity(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) max_size(A&&... a) const
        requires requires(const T& held) { held.max_size(std::forward<A>(a)...); }
    {
        return state_.v().max_size(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) contains(A&&... a) const
        requires requires(const T& held) { held.contains(std::forward<A>(a)...); }
    {
        return state_.v().contains(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) lower_bound(A&&... a) const
        requires requires(const T& held) { held.lower_bound(std::forward<A>(a)...); }
    {
        return state_.v().lower_bound(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) upper_bound(A&&... a) const
        requires requires(const T& held) { held.upper_bound(std::forward<A>(a)...); }
    {
        return state_.v().upper_bound(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) equal_range(A&&... a) const
        requires requires(const T& held) { held.equal_range(std::forward<A>(a)...); }
    {
        return state_.v().equal_range(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) key_comp(A&&... a) const
        requires requires(const T& held) { held.key_comp(std::forward<A>(a)...); }
    {
        return state_.v().key_comp(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) value_comp(A&&... a) const
        requires requires(const T& held) { held.value_comp(std::forward<A>(a)...); }
    {
        return state_.v().value_comp(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) get_allocator(A&&... a) const
        requires requires(const T& held) { held.get_allocator(std::forward<A>(a)...); }
    {
        return state_.v().get_allocator(std::forward<A>(a)...);
    }

    // Comparison with whatever the value compares with. A type that compares through a template
    // (an optional, a container) would not find the conversion alone.
    template <typename U>
        requires(!std::same_as<U, Written> && !wraps_written<U>::value) &&
                requires(const T& t, const U& u) { t == u; }
    friend bool operator==(const Written& a, const U& b) {
        return a.state_.v() == b;
    }
    // An optional on the other side. Without these the standard library's comparison of a value
    // with an optional is the better match: it takes this cell as the VALUE, so an empty cell
    // would compare unequal to an empty optional (the app's publish compares a parameter's
    // uncertainty with its last published one this way).
    template <typename V>
    friend bool operator==(const Written& a, const std::optional<V>& b) {
        return a.state_.v() == b;
    }
    template <typename V>
    friend bool operator==(const std::optional<V>& a, const Written& b) {
        return a == b.state_.v();
    }
    template <typename V>
    friend bool operator!=(const Written& a, const std::optional<V>& b) {
        return !(a.state_.v() == b);
    }
    template <typename V>
    friend bool operator!=(const std::optional<V>& a, const Written& b) {
        return !(a == b.state_.v());
    }
    friend bool operator==(const Written& a, const Written& b)
        requires requires(const T& t) { t == t; }
    {
        return a.state_.v() == b.state_.v();
    }
    // Ordering, as the value orders: with another field, and with whatever the value orders with,
    // on either side.
    friend auto operator<=>(const Written& a, const Written& b)
        requires requires(const T& t) { t <=> t; }
    {
        return a.state_.v() <=> b.state_.v();
    }
    template <typename U>
        requires(!std::same_as<U, Written> && !wraps_written<U>::value) &&
                requires(const T& t, const U& u) { t <=> u; }
    friend auto operator<=>(const Written& a, const U& b) {
        return a.state_.v() <=> b;
    }
    friend std::ostream& operator<<(std::ostream& out, const Written& field)
        requires requires(std::ostream& o, const T& t) { o << t; }
    {
        return out << field.state_.v();
    }

   private:
    friend class CellHold;  // a table's holding of its rows' cells
    using Table = typename TableBehind<T>::type;

    // The cell's state, as one member, so the field's own copies and moves stay the compiler's. A
    // copy and a move give a state no table holds, with the source's content and a write identity
    // of their own; an assignment is a write of the target, which stays held as it was. A move
    // that takes the source's content is a write of the source too (`drained`).
    struct State {
        // A copy and a construction from a value throw only where the value's own copy or move, or
        // the building of a loop's table, can: a cell of a number, a flag or an optional of one keeps
        // the `noexcept` copy the plain member had. The default state allocates nothing, whatever the
        // table behind a loop cell declares (a default column holds no buffer), so it is `noexcept`
        // wherever the value's is.
        State() noexcept(std::is_nothrow_default_constructible_v<T>) {}
        explicit State(T held) noexcept(std::is_nothrow_move_constructible_v<T> && !Table::kTable)
            : value(std::move(held)) {
            tabulate();
        }
        State(const State& other) noexcept(std::is_nothrow_copy_constructible_v<T> &&
                                           std::is_nothrow_copy_constructible_v<Table>)
            : value(other.v()), table(other.table) {}
        State(State&& other) noexcept(std::is_nothrow_move_constructible_v<T>)
            : value(std::move(other.v())), table(std::move(other.table)) {
            if (move_took(value)) {
                other.drained();
            }
        }
        State& operator=(const State& other) noexcept(
            std::is_nothrow_copy_constructible_v<T> && std::is_nothrow_move_assignable_v<T> &&
            std::is_nothrow_copy_constructible_v<Table> &&
            std::is_nothrow_move_assignable_v<Table>) {
            if (this != &other) {
                T next = other.v();  // the one step that can throw, taken before any change
                Table made = other.table;
                v() = std::move(next);
                table = std::move(made);
            }
            renew();  // a self-assignment is a write too
            return *this;
        }
        State& operator=(State&& other) noexcept(std::is_nothrow_move_assignable_v<T>) {
            if (this != &other) {
                v() = std::move(other.v());
                table = std::move(other.table);
                if (move_took(v())) {
                    other.drained();
                }
            }
            renew();
            return *this;
        }
        ~State() = default;

        // The state, in place.
        const T& v() const noexcept { return value; }
        T& v() noexcept { return value; }
        std::uint64_t w() const noexcept { return identity; }
        // A write: a new identity. Every table that holds the row takes the value into the
        // cell's column and notes the write in that column's stamp and in its generation.
        void renew() noexcept {
            identity = Epoch().value();
            if constexpr (!Table::kTable) {
                if (hold != nullptr) {
                    using V = typename ColumnValue<T>::type;
                    if constexpr (std::is_same_v<V, T>) {
                        hold->template write<V>(column, identity, value);
                    } else {
                        hold->template write<V>(column, identity, static_cast<V>(value));
                    }
                }
            }
        }
        // A loop held in one cell: `store` builds the table of the new rows before anything
        // changes. After an in-place edit the rows have already changed: `retabulate` rebuilds
        // the table from them, and a failure to allocate it ends the program rather than leave a
        // table that disagrees with its read image. A moved-from loop is empty, as its table is.
        void tabulate() {
            if constexpr (Table::kTable) {
                table = Table::of(value);
            }
        }
        void retabulate() noexcept {
            try {
                tabulate();
            } catch (...) {
                std::terminate();
            }
        }
        void store(T next) {
            if constexpr (Table::kTable) {
                Table made = Table::of(next);
                value = std::move(next);
                table = std::move(made);
            } else {
                v() = std::move(next);
            }
            renew();
        }
        // The source of a move that took its content (`move_took`): its value has changed, so it
        // records a write, and the tables that hold its row take the value it is left with and
        // note the write. A move that takes nothing leaves its source as it was and unwritten.
        void drained() noexcept {
            if constexpr (Table::kTable) {
                value.clear();
            }
            renew();
        }

        T value{};
        std::uint64_t identity = Epoch().value();
        [[no_unique_address]] Table table;  // a loop's rows; `value` is their read image
        std::uint32_t column = 0;       // held: this cell's column in the tables that hold its row
        const RowHold* hold = nullptr;  // held: the tables that hold this cell's row
    };
    State state_;

    // A table's own step, which only CellHold calls: the row is held (or, with null, no longer
    // held). It is not a write, and nothing moves.
    void held_by(const RowHold* hold, std::size_t column) noexcept {
        static_assert(!Table::kTable, "a loop held in one cell is a table of its own");
        state_.hold = hold;
        state_.column = static_cast<std::uint32_t>(column);
    }
};

// The text form of Written: it reads as a string (ItemKey's read surface), and every assignment
// is a recorded write. The text is held privately, so no reference to it can be written through.
// It is a cell view too, as Written is.
class WrittenText {
   public:
    WrittenText() = default;
    WrittenText(std::string value) : state_(std::move(value)) {}  // NOLINT(google-explicit-constructor)
    WrittenText(const char* value) : state_(std::string(value)) {}  // NOLINT(google-explicit-constructor)
    WrittenText& operator=(std::string next) {
        state_.v() = std::move(next);
        state_.renew();
        return *this;
    }
    WrittenText& operator=(const char* next) { return *this = std::string(next); }

    const std::string& value() const noexcept { return state_.v(); }
    operator const std::string&() const noexcept { return state_.v(); }  // NOLINT(google-explicit-constructor)
    operator std::string_view() const noexcept { return state_.v(); }  // NOLINT(google-explicit-constructor)
    bool empty() const noexcept { return state_.v().empty(); }
    const char* c_str() const noexcept { return state_.v().c_str(); }
    std::size_t size() const noexcept { return state_.v().size(); }
    // The rest of a string's const reads, for the members that were plain strings.
    static constexpr std::size_t npos = std::string::npos;
    const char& operator[](std::size_t index) const { return state_.v()[index]; }
    template <typename... A>
    decltype(auto) at(A&&... a) const
        requires requires(const std::string& held) { held.at(std::forward<A>(a)...); }
    {
        return state_.v().at(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) front(A&&... a) const
        requires requires(const std::string& held) { held.front(std::forward<A>(a)...); }
    {
        return state_.v().front(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) back(A&&... a) const
        requires requires(const std::string& held) { held.back(std::forward<A>(a)...); }
    {
        return state_.v().back(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) data(A&&... a) const
        requires requires(const std::string& held) { held.data(std::forward<A>(a)...); }
    {
        return state_.v().data(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) begin(A&&... a) const
        requires requires(const std::string& held) { held.begin(std::forward<A>(a)...); }
    {
        return state_.v().begin(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) cbegin(A&&... a) const
        requires requires(const std::string& held) { held.cbegin(std::forward<A>(a)...); }
    {
        return state_.v().cbegin(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) end(A&&... a) const
        requires requires(const std::string& held) { held.end(std::forward<A>(a)...); }
    {
        return state_.v().end(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) cend(A&&... a) const
        requires requires(const std::string& held) { held.cend(std::forward<A>(a)...); }
    {
        return state_.v().cend(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) rbegin(A&&... a) const
        requires requires(const std::string& held) { held.rbegin(std::forward<A>(a)...); }
    {
        return state_.v().rbegin(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) crbegin(A&&... a) const
        requires requires(const std::string& held) { held.crbegin(std::forward<A>(a)...); }
    {
        return state_.v().crbegin(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) rend(A&&... a) const
        requires requires(const std::string& held) { held.rend(std::forward<A>(a)...); }
    {
        return state_.v().rend(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) crend(A&&... a) const
        requires requires(const std::string& held) { held.crend(std::forward<A>(a)...); }
    {
        return state_.v().crend(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) length(A&&... a) const
        requires requires(const std::string& held) { held.length(std::forward<A>(a)...); }
    {
        return state_.v().length(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) max_size(A&&... a) const
        requires requires(const std::string& held) { held.max_size(std::forward<A>(a)...); }
    {
        return state_.v().max_size(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) capacity(A&&... a) const
        requires requires(const std::string& held) { held.capacity(std::forward<A>(a)...); }
    {
        return state_.v().capacity(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) compare(A&&... a) const
        requires requires(const std::string& held) { held.compare(std::forward<A>(a)...); }
    {
        return state_.v().compare(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) starts_with(A&&... a) const
        requires requires(const std::string& held) { held.starts_with(std::forward<A>(a)...); }
    {
        return state_.v().starts_with(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) ends_with(A&&... a) const
        requires requires(const std::string& held) { held.ends_with(std::forward<A>(a)...); }
    {
        return state_.v().ends_with(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) substr(A&&... a) const
        requires requires(const std::string& held) { held.substr(std::forward<A>(a)...); }
    {
        return state_.v().substr(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) copy(A&&... a) const
        requires requires(const std::string& held) { held.copy(std::forward<A>(a)...); }
    {
        return state_.v().copy(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) find(A&&... a) const
        requires requires(const std::string& held) { held.find(std::forward<A>(a)...); }
    {
        return state_.v().find(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) rfind(A&&... a) const
        requires requires(const std::string& held) { held.rfind(std::forward<A>(a)...); }
    {
        return state_.v().rfind(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) find_first_of(A&&... a) const
        requires requires(const std::string& held) { held.find_first_of(std::forward<A>(a)...); }
    {
        return state_.v().find_first_of(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) find_first_not_of(A&&... a) const
        requires requires(const std::string& held) { held.find_first_not_of(std::forward<A>(a)...); }
    {
        return state_.v().find_first_not_of(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) find_last_of(A&&... a) const
        requires requires(const std::string& held) { held.find_last_of(std::forward<A>(a)...); }
    {
        return state_.v().find_last_of(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) find_last_not_of(A&&... a) const
        requires requires(const std::string& held) { held.find_last_not_of(std::forward<A>(a)...); }
    {
        return state_.v().find_last_not_of(std::forward<A>(a)...);
    }
    template <typename... A>
    decltype(auto) get_allocator(A&&... a) const
        requires requires(const std::string& held) { held.get_allocator(std::forward<A>(a)...); }
    {
        return state_.v().get_allocator(std::forward<A>(a)...);
    }
    std::uint64_t written() const noexcept { return state_.w(); }
    bool bound() const noexcept { return state_.hold != nullptr; }

    friend bool operator==(const WrittenText& a, const WrittenText& b) { return a.value() == b.value(); }
    friend bool operator!=(const WrittenText& a, const WrittenText& b) { return a.value() != b.value(); }
    friend bool operator==(const WrittenText& a, const std::string& b) { return a.value() == b; }
    friend bool operator!=(const WrittenText& a, const std::string& b) { return a.value() != b; }
    friend bool operator==(const std::string& a, const WrittenText& b) { return a == b.value(); }
    friend bool operator!=(const std::string& a, const WrittenText& b) { return a != b.value(); }
    friend bool operator==(const WrittenText& a, const char* b) { return a.value() == b; }
    friend bool operator!=(const WrittenText& a, const char* b) { return a.value() != b; }
    friend auto operator<=>(const WrittenText& a, const WrittenText& b) { return a.value() <=> b.value(); }
    friend auto operator<=>(const WrittenText& a, const std::string& b) { return a.value() <=> b; }
    friend auto operator<=>(const WrittenText& a, const char* b) { return a.value() <=> b; }
    friend std::string operator+(const WrittenText& a, const WrittenText& b) { return a.value() + b.value(); }
    friend std::string operator+(const WrittenText& a, char b) { return a.value() + b; }
    friend std::string operator+(char a, const WrittenText& b) { return a + b.value(); }
    friend std::string operator+(const std::string& a, const WrittenText& b) { return a + b.value(); }
    friend std::string operator+(const WrittenText& a, const std::string& b) { return a.value() + b; }
    friend std::string operator+(const char* a, const WrittenText& b) { return a + b.value(); }
    friend std::string operator+(const WrittenText& a, const char* b) { return a.value() + b; }
    friend std::ostream& operator<<(std::ostream& out, const WrittenText& text) {
        return out << text.value();
    }

   private:
    friend class CellHold;  // a table's holding of its rows' cells

    // The cell's state, as one member (see Written::State).
    struct TextState {
        TextState() = default;
        explicit TextState(std::string held) : text(std::move(held)) {}
        TextState(const TextState& other) : text(other.v()) {}
        // A move that takes the source's text is a write of the source, which the tables that
        // hold its row note. A move of an empty text takes nothing.
        TextState(TextState&& other) noexcept : text(std::move(other.v())) {
            if (move_took(text)) {
                other.renew();
            }
        }
        TextState& operator=(const TextState& other) {
            if (this != &other) {
                v() = other.v();
            }
            renew();
            return *this;
        }
        TextState& operator=(TextState&& other) noexcept {
            if (this != &other) {
                v() = std::move(other.v());
                if (move_took(text)) {
                    other.renew();
                }
            }
            renew();
            return *this;
        }
        ~TextState() = default;

        const std::string& v() const noexcept { return text; }
        std::string& v() noexcept { return text; }
        std::uint64_t w() const noexcept { return identity; }
        void renew() noexcept {
            identity = Epoch().value();
            if (hold != nullptr) {
                hold->write<std::string>(column, identity, text);
            }
        }

        std::string text;
        std::uint64_t identity = Epoch().value();
        std::uint32_t column = 0;
        const RowHold* hold = nullptr;
    };
    TextState state_;

    void held_by(const RowHold* hold, std::size_t column) noexcept {
        state_.hold = hold;
        state_.column = static_cast<std::uint32_t>(column);
    }
};

// The experiment data node a handed-out data object was copied from — the experiment and the node's
// identity then — so a write through the object reaches that node while it is still the one the
// object came from (diffraction-lib's `experiment.data` is the live category). Set only by the
// Python `data` getter, which keeps the experiment alive for as long as the object lives. A copy
// starts unlinked and an assignment keeps its own, so an experiment's own node, which is always
// assigned or copied in, is never linked.
class DataSource {
   public:
    DataSource() = default;
    DataSource(const DataSource& /*other*/) noexcept {}
    // NOLINTNEXTLINE(bugprone-unhandled-self-assignment,cert-oop54-cpp) — keeps its own link
    DataSource& operator=(const DataSource& /*other*/) noexcept { return *this; }
    ~DataSource() = default;

    void link(ExperimentBase& experiment, std::uint64_t node) noexcept {
        experiment_ = &experiment;
        node_ = node;
    }
    ExperimentBase* experiment() const noexcept { return experiment_; }
    std::uint64_t node() const noexcept { return node_; }

   private:
    ExperimentBase* experiment_ = nullptr;
    std::uint64_t node_ = 0;
};

// The category holding a parameter, as the parameter's Python handle last reached it (X12). It
// points at a sibling inside the same enclosing object, so it never outlives what it names; a copy
// starts without one and an assignment keeps its own, so no copy or assignment carries another
// row's attachment.
class CategoryRef {
   public:
    CategoryRef() = default;
    CategoryRef(const CategoryRef&) noexcept {}
    CategoryRef& operator=(const CategoryRef&) noexcept { return *this; }
    ~CategoryRef() = default;

    void point_at(const RowLink& link) noexcept { link_ = &link; }
    const RowLink* get() const noexcept { return link_; }

   private:
    const RowLink* link_ = nullptr;
};

}  // namespace detail

// What a parameter's relation makes it (edi ADR-0024): free to vary, fixed or tied by symmetry, or set
// by a declared constraint. Derived from crysta's relation graph (refresh_relations, io.hpp); never
// saved.
enum class Dependence : std::uint8_t { Independent, SymmetryFixed, SymmetryTied, Constrained };

// A user-facing scalar with refinement state: value, standard uncertainty (absolute), and a
// free/fit flag. Maps 1:1 onto the engine's ParameterState.
struct Parameter {
    // The value records its own writes, so a raw assignment of the value it already holds is a
    // write the structure geometry sees. It reads as a double.
    detail::Written<double> value{0.0};
    // Standard uncertainty. std::optional so an empty-bracket `value()` (refinable with no prior uncertainty)
    // is representable as ABSENT — provably distinct from a fixed value and from a zero-uncertainty refined
    // `value(0)`. Defaults to PRESENT 0.0, so every default-/brace-constructed Parameter keeps its pre-change
    // public zero-uncertainty representation; std::nullopt is produced only by the parser's
    // `value()` branch (io.cpp parse_parameter) and an explicit public None (bindings / _parameter).
    // ADR-0018: the attributes are cells too, and record their writes.
    detail::Written<std::optional<double>> uncertainty{0.0};
    detail::Written<bool> free{false};
    // The persisted pre-fit snapshot upstream's fit-undo restores from (diffraction-lib
    // `start_value`/`start_uncertainty`). Captured for each free parameter at fit start,
    // serialized in analysis.edi's `_fit_parameter` loop (schema 3), cleared by undo
    // (single-level fit-undo). Disengaged = no fit state recorded.
    detail::Written<std::optional<double>> start_value;
    detail::Written<std::optional<double>> start_uncertainty;
    // Shared static metadata. Attached by model constructors and the spec-preserving write paths;
    // null only on a bare Parameter{} that no reachable Project may carry (the substrate gate
    // proves it). Copies share the pointer.
    const ParameterSpec* spec = nullptr;
    // The category that holds this parameter, for the Python handle's attachment answer.
    // Never copied: see detail::CategoryRef.
    detail::CategoryRef category;
    // Renewed by every admitted write of the value, whatever value it leaves, so an equal-value
    // write stales the computed categories it feeds. A write to the uncertainty, free flag or fit
    // start is not a write to an input and leaves it.
    detail::Epoch epoch;
    // Set by refresh_relations and apply_relations; a dependent's free flag stays false.
    Dependence dependence = Dependence::Independent;

    Parameter() = default;
    Parameter(double value_, std::optional<double> esd_ = 0.0, bool free_ = false)
        : value(value_), uncertainty(esd_), free(free_) {}

    // Whether a collection holds this parameter's row. False for a parameter no row ever held.
    bool is_attached() const noexcept { return category.get() != nullptr && category.get()->attached(); }
    // Whether its row was held and no longer is — removed, or its collection destroyed. Such a
    // parameter keeps its last values and refuses writes through its Python handle.
    bool is_detached() const noexcept { return category.get() != nullptr && category.get()->detached(); }
    // ADR-0018: whether a table holds this parameter's row.
    bool bound() const noexcept { return value.bound(); }
};

// The free flag's rule (edi ADR-0024): a dependent stays dependent, so freeing one changes nothing and
// answers false; the caller says so with crysta's `crysta.domain.dependent_free_ignored`.
inline bool set_free(Parameter& parameter, bool free) {
    if (free && parameter.dependence != Dependence::Independent) {
        return false;
    }
    parameter.free = free;
    return true;
}

// Set a parameter's value under its admissible range — the Python
// `Parameter.value` setter's rule and message (check_admissible), for the app's writes.
inline void assign_value(Parameter& parameter, double value) {
    check_admissible(parameter.spec, value, parameter.spec != nullptr ? parameter.spec->name : "value");
    parameter.value = value;
    parameter.epoch = detail::Epoch();  // A write, whatever the value
}

namespace detail {
// An id as a refusal message spells it — crysta's `printable_id` (printable ASCII and well-formed
// UTF-8 text as is, every other byte as `\xHH`), reached through the
// adapter (core/src/adapter.cpp, edi's one crysta contact), so edi names ids exactly as crysta
// does. A raw NUL would end what() there, dropping the id and the rule after it.
std::string printable_id(const std::string& id);
}  // namespace detail

// ADR-0016: collection-owned loop ids — the one uniqueness predicate of edi's model plane. Refuses
// (std::invalid_argument) the first id that occurs twice, naming the category, the id and `where`.
// Inline (like the rest of this header) so every consumer TU list links unchanged.
inline void require_unique_ids(const std::vector<std::string>& ids, const std::string& category,
                               const std::string& where) {
    std::set<std::string> seen;
    for (const std::string& id : ids) {
        if (!seen.insert(id).second) {
            throw std::invalid_argument(where + " refuses two " + category + "s named '" +
                                        detail::printable_id(id) +
                                        "': ids are unique within a loop category");
        }
    }
}

// ADR-0016: a datablock's canonical key — the name, or the category's default spelling when
// empty (crysta's `datablock_key`, which every persisted form uses).
inline std::string datablock_key(const std::string& name, const std::string& default_spelling) {
    return name.empty() ? default_spelling : name;
}

class ItemKey;

namespace detail {

// A project's revocable reference to itself, as crysta's ProjectOwnerLink: one record per project
// object, set to the project while it lives and cleared when it is destroyed. Every collection of the
// project, and every collection inside its structures and experiments, holds the record, so one that
// outlives its project, or has left it, reads none (edi ADR-0024).
struct ProjectLink {
    Project* project = nullptr;
};

// The project being built on this thread, from its first base to its last member.
inline thread_local Project* project_being_built = nullptr;

// The project's own record, as a base so it exists before any member: every constructor, copies and
// moves included, makes a record naming this project. An assignment keeps each side's.
class ProjectAnchor {
   public:
    const std::shared_ptr<ProjectLink>& link() const noexcept { return link_; }

   protected:
    ProjectAnchor() { open(); }
    ProjectAnchor(const ProjectAnchor& /*other*/) { open(); }
    ProjectAnchor(ProjectAnchor&& /*other*/) { open(); }
    // NOLINTNEXTLINE(bugprone-unhandled-self-assignment,cert-oop54-cpp) — keeps its own record
    ProjectAnchor& operator=(const ProjectAnchor& /*other*/) noexcept { return *this; }
    ProjectAnchor& operator=(ProjectAnchor&& /*other*/) noexcept { return *this; }
    ~ProjectAnchor();

   private:
    friend class ProjectTail;
    void open();
    std::shared_ptr<ProjectLink> link_;
    Project* outer_ = nullptr;  // the project being built when this one began (a nested build)
};

// The project's last member: built after every collection, it links them all to the record, and so does
// every assignment, which runs it last too. So a project made any way (built, loaded, copied, moved or
// assigned) has its links from the start (edi ADR-0024).
class ProjectTail {
   public:
    ProjectTail() { close(); }
    ProjectTail(const ProjectTail& /*other*/) { close(); }
    ProjectTail(ProjectTail&& /*other*/) noexcept { close(); }
    // NOLINTNEXTLINE(bugprone-unhandled-self-assignment,cert-oop54-cpp) — relinks its own project
    ProjectTail& operator=(const ProjectTail& /*other*/) noexcept {
        relink();
        return *this;
    }
    ProjectTail& operator=(ProjectTail&& /*other*/) noexcept {
        relink();
        return *this;
    }
    ~ProjectTail() = default;

   private:
    void close() noexcept;
    void relink() const noexcept;
    Project* owner_ = nullptr;
};

// The collections inside a structure or an experiment take the link of the collection that admits it
// (null when it leaves), so a retained one follows its item from project to project.
inline void link_nested(Structure& structure, const std::shared_ptr<const ProjectLink>& link) noexcept;
inline void link_nested(ExperimentBase& experiment, const std::shared_ptr<const ProjectLink>& link) noexcept;

// A keyed collection, as its members' ids see it.
class KeyedBase {
   public:
    KeyedBase() = default;
    // The host belongs to the collection object, never to its value. A copied or moved-into
    // collection starts without one and an assignment keeps its own, so the host is either null
    // or the project this very collection is a member of.
    KeyedBase(const KeyedBase& /*other*/) noexcept {}
    KeyedBase(KeyedBase&& /*other*/) noexcept {}
    // NOLINTNEXTLINE(bugprone-unhandled-self-assignment,cert-oop54-cpp) — keeps its own host
    KeyedBase& operator=(const KeyedBase& /*other*/) noexcept { return *this; }
    KeyedBase& operator=(KeyedBase&& /*other*/) noexcept { return *this; }
    virtual ~KeyedBase() = default;
    // Admit renaming `key` — the id of one of this collection's items — to `next`, or throw. Returns
    // false when `key` is not stored here (a stale record): the caller renames as detached.
    virtual bool admit_rename(const ItemKey& key, const std::string& next) const = 0;
    // The live project this collection belongs to, as a member or inside one of its structures or
    // experiments; null otherwise (edi ADR-0024).
    Project* host() const noexcept { return host_link_ ? host_link_->project : nullptr; }

   protected:
    const std::shared_ptr<const ProjectLink>& host_link() const noexcept { return host_link_; }

   private:
    friend class edi::Project;
    friend void link_nested(Structure& structure, const std::shared_ptr<const ProjectLink>& link) noexcept;
    friend void link_nested(ExperimentBase& experiment,
                            const std::shared_ptr<const ProjectLink>& link) noexcept;
    std::shared_ptr<const ProjectLink> host_link_;
};


}  // namespace detail

// The id of a keyed item — its FIRST data member, so a whole-item assignment runs this check
// before it copies anything else. Reads as a string; every write is a rename the owning collection
// admits; a copy is detached.
class ItemKey {
   public:
    ItemKey() = default;
    ItemKey(std::string value) : value_(std::move(value)) {}  // NOLINT(google-explicit-constructor)
    ItemKey(const char* value) : value_(value) {}             // NOLINT(google-explicit-constructor)
    // A copy is detached and standalone, whatever its source is bound to.
    ItemKey(const ItemKey& other) : value_(other.v()) {}
    // No moves. A keyed item's implicit move would move every OTHER member out of an attached item
    // while its key only copies, so a refused `std::swap` of two siblings — its temporary
    // move-constructed from the first — destroyed the first one's payload (a structure's sites, an
    // experiment's rows) on unwinding. Deleting the key's moves defines each keyed item's
    // defaulted moves as deleted, which overload resolution ignores: moving a keyed item COPIES
    // it, and the source is never drained.
    ItemKey(ItemKey&&) = delete;
    ItemKey& operator=(ItemKey&&) = delete;
    ~ItemKey() = default;
    ItemKey& operator=(const ItemKey& other) {
        if (this != &other) {
            rename(other.v());
        } else {
            renew();  // a self-assignment is a write too
        }
        return *this;
    }
    ItemKey& operator=(std::string next) {
        rename(std::move(next));
        return *this;
    }
    ItemKey& operator=(const char* next) {
        rename(std::string(next));
        return *this;
    }

    const std::string& value() const { return v(); }
    operator const std::string&() const { return v(); }  // NOLINT(google-explicit-constructor)
    bool empty() const { return v().empty(); }
    const char* c_str() const { return v().c_str(); }
    std::size_t size() const { return v().size(); }
    bool attached() const { return membership_ != nullptr && membership_->owner != nullptr; }
    // The collection this id belongs to, or nullptr (a detached item).
    const detail::KeyedBase* owner() const { return attached() ? membership_->owner : nullptr; }

    void rename(std::string next) {
        if (attached() && membership_->owner->admit_rename(*this, next)) {
            v() = std::move(next);
            renew();
            return;
        }
        membership_.reset();
        v() = std::move(next);
        renew();
    }
    // The identity of the last admitted rename, an equal one included.
    std::uint64_t written() const noexcept { return written_; }
    // ADR-0018: whether a table holds this id's row.
    bool bound() const noexcept { return hold_ != nullptr; }

    friend bool operator==(const ItemKey& a, const ItemKey& b) { return a.v() == b.v(); }
    friend bool operator!=(const ItemKey& a, const ItemKey& b) { return a.v() != b.v(); }
    friend bool operator==(const ItemKey& a, const std::string& b) { return a.v() == b; }
    friend bool operator!=(const ItemKey& a, const std::string& b) { return a.v() != b; }
    friend bool operator==(const std::string& a, const ItemKey& b) { return a == b.v(); }
    friend bool operator!=(const std::string& a, const ItemKey& b) { return a != b.v(); }
    friend bool operator==(const ItemKey& a, const char* b) { return a.v() == b; }
    friend bool operator!=(const ItemKey& a, const char* b) { return a.v() != b; }
    friend bool operator<(const ItemKey& a, const ItemKey& b) { return a.v() < b.v(); }
    friend std::string operator+(const std::string& a, const ItemKey& b) { return a + b.v(); }
    friend std::string operator+(const ItemKey& a, const std::string& b) { return a.v() + b; }
    friend std::string operator+(const char* a, const ItemKey& b) { return a + b.v(); }
    friend std::string operator+(const ItemKey& a, const char* b) { return a.v() + b; }
    friend std::string operator+(const ItemKey& a, char b) { return a.v() + b; }
    friend std::ostream& operator<<(std::ostream& out, const ItemKey& key) {
        return out << key.v();
    }

   private:
    template <typename>
    friend class ItemVec;
    friend class detail::CellHold;  // a table's holding of its rows' cells

    const std::string& v() const noexcept { return value_; }
    std::string& v() noexcept { return value_; }
    // A write: a new identity. Every table that holds the row takes the id into its id column
    // and notes the write in that column's stamp and in its generation.
    void renew() noexcept {
        written_ = detail::Epoch().value();
        if (hold_ != nullptr) {
            hold_->write<std::string>(column_, written_, value_);
        }
    }
    void held_by(const detail::RowHold* hold, std::size_t column) noexcept {
        hold_ = hold;
        column_ = static_cast<std::uint32_t>(column);
    }

    std::string value_;
    std::shared_ptr<detail::Membership> membership_;
    std::uint64_t written_ = detail::Epoch().value();
    std::uint32_t column_ = 0;                // held: the id column of the tables that hold the row
    const detail::RowHold* hold_ = nullptr;  // held: the tables that hold this id's row
};

template <typename T>
class ItemVec;

namespace detail {
// ADR-0018 §1: the typed value columns that store one cell field of every row of a table, in
// row order. A cell of a value has one column of that value; a text and an id have a column of
// strings; a parameter has five.
struct ParameterColumns {
    crysta::Column<double> value;
    crysta::Column<std::optional<double>> uncertainty;
    crysta::Column<std::uint8_t> free;
    crysta::Column<std::optional<double>> start_value;
    crysta::Column<std::optional<double>> start_uncertainty;
};
template <typename Field>
struct FieldColumns;
template <typename U>
struct FieldColumns<Written<U>> {
    using type = crysta::Column<typename ColumnValue<U>::type>;
};
template <>
struct FieldColumns<WrittenText> {
    using type = crysta::Column<std::string>;
};
template <>
struct FieldColumns<ItemKey> {
    using type = crysta::Column<std::string>;
};
template <>
struct FieldColumns<Parameter> {
    using type = ParameterColumns;
};
template <typename Member>
struct MemberField;
template <typename Field, typename Class>
struct MemberField<Field Class::*> {
    using type = Field;
};
template <typename Fields>
struct ColumnsFor;
template <typename... Members>
struct ColumnsFor<std::tuple<Members...>> {
    using type =
        std::tuple<typename FieldColumns<typename MemberField<Members>::type>::type...>;
};
// The value columns of a row type's table: one entry for each field its schema names, in schema
// order.
template <typename Row>
using RowColumns =
    typename ColumnsFor<std::remove_const_t<decltype(crysta::RowSchema<Row>::fields)>>::type;

// ADR-0018 §1: the one way a table reaches the cells of its rows. It tells them which tables
// hold their row, reads that back, reads their write identities, and gathers their values into
// the columns of a table. Only ItemVec uses it.
class CellHold {
   private:
    template <typename>
    friend class ::edi::ItemVec;

    template <typename U>
    static constexpr std::size_t width(const Written<U>* /*cell*/) noexcept { return 1; }
    static constexpr std::size_t width(const WrittenText* /*cell*/) noexcept { return 1; }
    static constexpr std::size_t width(const ItemKey* /*cell*/) noexcept { return 1; }
    static constexpr std::size_t width(const Parameter* /*cell*/) noexcept { return 5; }

    template <typename U>
    static void set(Written<U>& cell, const RowHold* hold, std::size_t& column) noexcept {
        cell.held_by(hold, column++);
    }
    static void set(WrittenText& cell, const RowHold* hold, std::size_t& column) noexcept {
        cell.held_by(hold, column++);
    }
    static void set(ItemKey& cell, const RowHold* hold, std::size_t& column) noexcept {
        cell.held_by(hold, column++);
    }
    static void set(Parameter& cell, const RowHold* hold, std::size_t& column) noexcept {
        set(cell.value, hold, column);
        set(cell.uncertainty, hold, column);
        set(cell.free, hold, column);
        set(cell.start_value, hold, column);
        set(cell.start_uncertainty, hold, column);
    }

    template <typename U>
    static const RowHold* of(const Written<U>& cell) noexcept { return cell.state_.hold; }
    static const RowHold* of(const WrittenText& cell) noexcept { return cell.state_.hold; }
    static const RowHold* of(const ItemKey& cell) noexcept { return cell.hold_; }
    static const RowHold* of(const Parameter& cell) noexcept { return of(cell.value); }

    template <typename U>
    static void note(const Written<U>& cell, TableNotes& notes, std::size_t& column) noexcept {
        notes.note(column++, cell.written());
    }
    static void note(const WrittenText& cell, TableNotes& notes, std::size_t& column) noexcept {
        notes.note(column++, cell.written());
    }
    static void note(const ItemKey& cell, TableNotes& notes, std::size_t& column) noexcept {
        notes.note(column++, cell.written());
    }
    static void note(const Parameter& cell, TableNotes& notes, std::size_t& column) noexcept {
        note(cell.value, notes, column);
        note(cell.uncertainty, notes, column);
        note(cell.free, notes, column);
        note(cell.start_value, notes, column);
        note(cell.start_uncertainty, notes, column);
    }

    // The columns the cells of a row type make, in schema order.
    template <typename Row>
    static constexpr std::size_t columns() noexcept {
        return std::apply(
            [](const auto&... field) {
                return (std::size_t{0} + ... +
                        width(static_cast<const std::remove_cvref_t<
                                  decltype(std::declval<Row&>().*field)>*>(nullptr)));
            },
            crysta::RowSchema<Row>::fields);
    }
    // Every cell of `row` points at `hold`: the tables that hold the row, or none.
    template <typename Row>
    static void hold(Row& row, const RowHold* hold) noexcept {
        std::size_t column = 0;
        std::apply([&](const auto&... field) { (set(row.*field, hold, column), ...); },
                   crysta::RowSchema<Row>::fields);
    }
    // The tables that hold `row`, read from the first cell its schema lists; null for a row no
    // table holds and for a row type without cells.
    template <typename Row>
    static const RowHold* held(const Row& row) noexcept {
        using Fields = std::remove_const_t<decltype(crysta::RowSchema<Row>::fields)>;
        if constexpr (std::tuple_size_v<Fields> == 0) {
            return nullptr;
        } else {
            return of(row.*std::get<0>(crysta::RowSchema<Row>::fields));
        }
    }
    // A table that takes `row` notes the last write of each of its cells in the cell's column.
    template <typename Row>
    static void note_all(const Row& row, TableNotes& notes) noexcept {
        std::size_t column = 0;
        std::apply([&](const auto&... field) { (note(row.*field, notes, column), ...); },
                   crysta::RowSchema<Row>::fields);
    }

    // The value columns, in schema column order: what a cell's write reaches by its column.
    template <typename V>
    static void reach(crysta::Column<V>& column, std::vector<void*>& found) {
        found.push_back(&column);
    }
    static void reach(ParameterColumns& columns, std::vector<void*>& found) {
        found.push_back(&columns.value);
        found.push_back(&columns.uncertainty);
        found.push_back(&columns.free);
        found.push_back(&columns.start_value);
        found.push_back(&columns.start_uncertainty);
    }
    template <typename Columns>
    static std::vector<void*> value_columns(Columns& columns) {
        std::vector<void*> found;
        std::apply([&found](auto&... column) { (reach(column, found), ...); }, columns);
        return found;
    }

    // One value column of `rows`: what `read` returns for each row, in row order.
    template <typename V, typename Rows, typename Read>
    static crysta::Column<V> gathered(const Rows& rows, const Read& read) {
        std::vector<V> values;
        values.reserve(rows.size());
        for (const auto& row : rows) {
            values.push_back(static_cast<V>(read(*row)));
        }
        return crysta::Column<V>(std::move(values));
    }
    template <typename U, typename Rows, typename Member>
    static void gather(crysta::Column<typename ColumnValue<U>::type>& column, const Rows& rows,
                       Member member, const Written<U>* /*cell*/) {
        column = gathered<typename ColumnValue<U>::type>(
            rows, [member](const auto& row) -> const U& { return (row.*member).get(); });
    }
    template <typename Rows, typename Member>
    static void gather(crysta::Column<std::string>& column, const Rows& rows, Member member,
                       const WrittenText* /*cell*/) {
        column = gathered<std::string>(
            rows, [member](const auto& row) -> const std::string& { return (row.*member).value(); });
    }
    template <typename Rows, typename Member>
    static void gather(crysta::Column<std::string>& column, const Rows& rows, Member member,
                       const ItemKey* /*cell*/) {
        column = gathered<std::string>(
            rows, [member](const auto& row) -> const std::string& { return (row.*member).value(); });
    }
    template <typename Rows, typename Member>
    static void gather(ParameterColumns& columns, const Rows& rows, Member member,
                       const Parameter* /*cell*/) {
        columns.value = gathered<double>(
            rows, [member](const auto& row) { return (row.*member).value.get(); });
        columns.uncertainty = gathered<std::optional<double>>(
            rows, [member](const auto& row) { return (row.*member).uncertainty.get(); });
        columns.free = gathered<std::uint8_t>(
            rows, [member](const auto& row) { return (row.*member).free.get(); });
        columns.start_value = gathered<std::optional<double>>(
            rows, [member](const auto& row) { return (row.*member).start_value.get(); });
        columns.start_uncertainty = gathered<std::optional<double>>(
            rows, [member](const auto& row) { return (row.*member).start_uncertainty.get(); });
    }
    // The value columns of `rows`, gathered from the rows' cells: the allocating step of a change
    // of a table's rows. It changes nothing.
    template <typename Row, typename Rows>
    static RowColumns<Row> columns_of(const Rows& rows) {
        RowColumns<Row> made;
        gather_fields<Row>(made, rows,
                           std::make_index_sequence<std::tuple_size_v<RowColumns<Row>>>());
        return made;
    }
    template <typename Row, typename Rows, std::size_t... Index>
    static void gather_fields(RowColumns<Row>& made, const Rows& rows,
                              std::index_sequence<Index...> /*fields*/) {
        (gather(std::get<Index>(made), rows, std::get<Index>(crysta::RowSchema<Row>::fields),
                static_cast<const typename MemberField<std::remove_cvref_t<decltype(std::get<Index>(
                    crysta::RowSchema<Row>::fields))>>::type*>(nullptr)),
         ...);
    }
};
}  // namespace detail

namespace detail {
// ADR-0018: the canonical encoding of one cell of a one-row table. A cell that records its writes
// contributes the identity of its last write, so an equal-value write changes the encoding. A
// plain member contributes its value: the encoding sees every changed value of it and nothing
// else, because a plain member has no write identity (I18). Numbers are their exact bit patterns,
// text is length-prefixed and presence is encoded apart from any value.
inline void encode_bits(std::string& out, std::uint64_t value) {
    static constexpr char kHex[] = "0123456789abcdef";
    for (int shift = 60; shift >= 0; shift -= 4) {
        out += kHex[(value >> shift) & 0xFU];
    }
}
template <typename T>
void encode_cell(std::string& out, const std::optional<T>& cell);
inline void encode_cell(std::string& out, const std::string& text) {
    encode_bits(out, text.size());
    out += text;
    out += '\x1e';
}
inline void encode_cell(std::string& out, double value) {
    encode_bits(out, std::bit_cast<std::uint64_t>(value));
}
template <typename T>
    requires(std::is_integral_v<T> || std::is_enum_v<T>)
void encode_cell(std::string& out, T value) {
    encode_bits(out, static_cast<std::uint64_t>(static_cast<std::int64_t>(value)));
}
template <typename T>
void encode_cell(std::string& out, const Written<T>& cell) {
    encode_bits(out, cell.written());
}
inline void encode_cell(std::string& out, const WrittenText& cell) {
    encode_bits(out, cell.written());
}
inline void encode_cell(std::string& out, const ItemKey& key) { encode_bits(out, key.written()); }
// A parameter is a column: its value's last write and its own identity, then its attributes.
inline void encode_cell(std::string& out, const Parameter& parameter) {
    encode_cell(out, parameter.value);
    encode_bits(out, parameter.epoch.value());
    encode_cell(out, parameter.uncertainty);
    encode_cell(out, parameter.free);
    encode_cell(out, parameter.start_value);
    encode_cell(out, parameter.start_uncertainty);
}
template <typename T>
void encode_cell(std::string& out, const std::optional<T>& cell) {
    out += cell.has_value() ? 'S' : '-';
    if (cell.has_value()) {
        encode_cell(out, *cell);
    }
}
}  // namespace detail

// ADR-0018: the table view of one non-loop category of `owner`. A non-loop category is a table
// of one row whose cells stand in the object that owns it. `Category` is its
// schema (below, after the model): `Owner`, `name`, `columns` — pointers to the owner's members
// that hold the cells — and `items`.
template <typename Category>
class OneRow {
   public:
    using Owner = typename Category::Owner;

    explicit OneRow(const Owner& owner) noexcept : owner_(&owner) {}

    static constexpr std::size_t rows() noexcept { return 1; }
    crysta::RowToken token() const noexcept { return owner_->table_row.token(); }
    // The table's generation: the canonical encoding of exactly the schema's columns. A write
    // that changes one of them changes it; a write to any other cell of the owner does not.
    std::string generation() const {
        std::string out;
        std::apply(
            [this, &out](const auto&... column) {
                (detail::encode_cell(out, owner_->*column), ...);
            },
            Category::columns);
        return out;
    }

   private:
    const Owner* owner_;
};

namespace detail {
// A schema names one file-item entry per column.
template <typename Columns, typename Items>
constexpr bool one_entry_per_column(const Columns& /*columns*/, const Items& items) noexcept {
    return std::tuple_size_v<Columns> == std::size(items);
}
}  // namespace detail

// How a keyed collection reads its items' ids (specialised beside each keyed type): where the id
// lives, the key it compares (an empty datablock name compares as its default spelling) and the
// category a refusal names. An item type without a specialisation is unkeyed (a background point).
template <typename T>
struct KeyTraits;

// How a collection links the rows it holds — every RowLink a row carries, its own and each
// parameter category's inside it. Specialised beside each item type that holds parameters; an
// item type without parameters has nothing to link. Linking cannot throw, so a collection's
// commit stays nothrow (ADR-0016 §2).
template <typename T>
struct RowTraits {
    static void link(T&, const std::shared_ptr<detail::Membership>&) noexcept {}
    static void unlink(T&) noexcept {}
    static const detail::RowLink* primary(const T&) noexcept { return nullptr; }
};

template <typename T>
concept KeyedItem = requires(T& item) {
    { KeyTraits<T>::key(item) } -> std::same_as<ItemKey&>;
};

// Item storage for the model's collections. Items are held by shared_ptr so a binding-surface
// reference to an item stays valid across every collection mutation and a removed item survives
// while a caller still holds it (reference identity INSIDE one live collection) — while COPYING
// an owner deep-clones every item (`Project probe = model` in adapter.cpp::validate_index writes
// sentinels into the copy and the live model must never see them). Putting the deep copy on the
// member type instead of rule-of-five on each owner means no owner class can forget it.
//
// ADR-0016: for a keyed item type the collection OWNS its items' ids. Storage is private: access
// hands out `const Ptr&` and const iterators, so a slot cannot be reseated from outside; each
// mutator validates the candidate result before it commits (the ids unique by their canonical key,
// and no item another live collection holds — one collection per item) and (re-)attaches every
// stored item after it, so no path leaves an attached item unchecked or an item attached to a
// collection that does not hold it. A mutator that throws — a refusal, or an allocation failure —
// leaves the collection as it was: everything that can throw (clones, the candidate storage, the
// membership record) is prepared before the commit, and the commit and re-attachment cannot throw.
//
// ADR-0018: the collection is a column table. Its schema (`crysta::RowSchema`) names its
// columns, each row has a token that is never reused, and it has a generation. Every cell of its
// rows is stored in a typed value column of the table, a
// `crysta::Column<V>` for each schema column, in row order (`column`). A snapshot
// of a column never changes under its holder: a write moves the column to another buffer first.
//
// The item of a row is the row's handle. It keeps a read image of the row's cells, and a read by
// reference returns the image, so that reference stays valid and current for as long as the item
// lives: before the collection takes it, while it holds it, after it removes it, and when
// another unkeyed collection holds it too (ADR-0012 §1). A write to a cell writes the image and
// the cell's column in every table that holds the row, in one step, so the table's generation is
// the newest change of its rows or of any cell of them. An item no table holds is a standalone
// row with its last values.
//
// The table's own state — the value columns, the row anchors, the column stamps and the hold
// records — is one heap object that never moves, so the collection itself may move. A change of
// the rows does its allocating work first (the candidate, its value columns, the hold records
// and the anchors), and its commit cannot throw.
template <typename T>
class ItemVec final : public detail::KeyedBase {
   public:
    using Ptr = std::shared_ptr<T>;
    using const_iterator = typename std::vector<Ptr>::const_iterator;

    ItemVec() = default;
    // Admission of a whole collection of shared items (the loader's and the bulk paths' spelling).
    explicit ItemVec(std::vector<Ptr> items) { assign(std::move(items)); }
    ItemVec(const ItemVec& other) : detail::KeyedBase() { *this = other; }
    ItemVec& operator=(const ItemVec& other) {
        if (this != &other) {
            std::vector<Ptr> clones;
            clones.reserve(other.store_.items().size());
            for (const Ptr& item : other.store_.items()) {
                clones.push_back(std::make_shared<T>(*item));  // a clone's id is detached
            }
            require_admissible(clones, "copy");
            replace_rows(std::move(clones));
        } else {
            store_.touch();  // a self-assignment is a write
        }
        return *this;
    }
    // A move hands the items, their membership record and their table over, re-pointed at the new
    // owner; the moved-from collection is left empty with neither.
    ItemVec(ItemVec&& other) noexcept
        : detail::KeyedBase(),
          membership_(std::move(other.membership_)),
          table_(std::move(other.table_)) {
        store_.edit() = std::move(other.store_.edit());  // the moved-from collection is written too
        if (membership_) {
            membership_->owner = this;
        }
        if (table_) {
            table_->store = &store_;
        }
        other.store_.edit().clear();
    }
    ItemVec& operator=(ItemVec&& other) noexcept {
        if (this != &other) {
            release_all();
            detach_all();
            if (membership_) {
                membership_->owner = nullptr;
            }
            membership_ = std::move(other.membership_);
            table_ = std::move(other.table_);
            store_.edit() = std::move(other.store_.edit());
            if (membership_) {
                membership_->owner = this;
            }
            if (table_) {
                table_->store = &store_;
            }
            other.store_.edit().clear();
            link_items();  // the items now belong where this collection does
        } else {
            store_.touch();  // a self-move-assignment is a write
        }
        return *this;
    }
    ~ItemVec() override {
        release_all();  // a held item outlives its collection with its values (ADR-0012 §1)
        detach_all();
        if (membership_) {
            membership_->owner = nullptr;  // revoked: a held item can never reach this collection
        }
    }

    const_iterator begin() const { return store_.items().begin(); }
    const_iterator end() const { return store_.items().end(); }
    // The collection's membership record — its identity, which a calculation records for the
    // collections it read. Null until the collection first held an item.
    std::shared_ptr<const detail::Membership> record() const noexcept { return membership_; }
    // The identity of the last admitted write. Every non-const member renews it — an insertion, a
    // removal, a replacement or an assignment, of the very items the collection already held and
    // of the collection to itself included — so removing a row and adding the same object back,
    // assigning the same pointers in the same order, and `sites = sites` are each a write its
    // readers see. The store below makes it so by construction; a refused mutation changes nothing
    // and records nothing.
    std::uint64_t generation() const noexcept { return store_.generation(); }
    // ADR-0018: the table's generation — the newer of the last change of the rows and the last
    // write to any cell the table holds.
    std::uint64_t category_stamp() const noexcept {
        return table_ ? table_->category_stamp() : store_.generation();
    }
    // The token of row `i`: from the process-wide counter, never reused. A replacement of the rows
    // gives every row a new one.
    crysta::RowToken token(std::size_t i) const { return table_->anchors.token(i); }
    std::size_t size() const { return store_.items().size(); }
    bool empty() const { return store_.items().empty(); }
    const Ptr& front() const { return store_.items().front(); }
    const Ptr& back() const { return store_.items().back(); }
    const Ptr& operator[](std::size_t i) const { return store_.items()[i]; }

    // By column (ADR-0018 §2): the typed value column that stores one cell field of every row,
    // in row order — `crysta::Column<V>` for a cell of a value, a text or an id, and a
    // parameter's five columns for a parameter. `member` is a field the row's schema names.
    // Read-only: a write goes through the row's cell. A reader that keeps a column's buffer
    // keeps those values: a later write moves the column to another buffer.
    template <typename Field, typename Class>
    const typename detail::FieldColumns<Field>::type& column(Field Class::* member) const {
        using Found = typename detail::FieldColumns<Field>::type;
        static const Found none{};
        const Found* found = nullptr;
        find_column(member, found, none,
                    std::make_index_sequence<std::tuple_size_v<detail::RowColumns<T>>>());
        if (found == nullptr) {
            throw std::invalid_argument(std::string(crysta::RowSchema<T>::name) +
                                        " has no column of that member");
        }
        return *found;
    }

    // Appends the caller's item (shared — reference semantics, ADR-0012 §1), refused when its id is
    // taken or another live collection holds it.
    void push_back(Ptr item) {
        std::vector<Ptr> candidate = store_.items();
        candidate.push_back(item);
        require_admissible(candidate, "insertion");
        std::shared_ptr<detail::Membership> record = first_record();
        std::unique_ptr<Table> made = first_table();
        Table& table = made ? *made : *table_;
        std::shared_ptr<crysta::detail::RowAnchor> anchor =
            crysta::detail::AnchorList::fresh(&table, &Table::anchors);
        std::shared_ptr<detail::RowHold> hold = Table::record_of(*item, 1);
        table.holds.reserve(candidate.size());
        typename Table::Columns columns = detail::CellHold::columns_of<T>(candidate);
        table.anchors.add_slot();  // the last step that can throw; nothing has changed yet
        install(record, made);
        store_.edit() = std::move(candidate);
        table_->columns = std::move(columns);
        table_->take(*store_.items().back(), std::move(hold), store_.items().size() - 1);
        table_->anchors.fill_last(std::move(anchor), table_.get());
        attach_all();
    }
    // Appends a copy of a value.
    void push_back(T value) { push_back(std::make_shared<T>(std::move(value))); }
    // Replaces the item at `i` (the old one is detached; a held reference survives).
    void replace_at(std::size_t i, Ptr item) {
        std::vector<Ptr> candidate = store_.items();
        candidate.at(i) = std::move(item);
        require_admissible(candidate, "replacement");
        replace_rows(std::move(candidate));
    }
    // Wholesale replacement sharing the passed items (a reordering of this collection's own items
    // included); refused when two share an id or another live collection holds one.
    void assign(std::vector<Ptr> items) {
        require_admissible(items, "assignment");
        replace_rows(std::move(items));
    }
    void erase_at(std::size_t i) {
        const Ptr old = store_.items().at(i);
        std::vector<Ptr> rest = store_.items();
        rest.erase(rest.begin() + static_cast<std::ptrdiff_t>(i));
        typename Table::Columns columns = detail::CellHold::columns_of<T>(rest);
        std::vector<std::shared_ptr<const void>> kept(1);
        // The commit: nothing below can throw.
        store_.edit() = std::move(rest);
        table_->release(*old, i);
        table_->columns = std::move(columns);
        table_->anchors.revoke_and_erase(i, i + 1, std::move(kept));
        detach_one(old);
    }
    void clear() {
        if (table_) {
            std::vector<std::shared_ptr<const void>> kept(table_->anchors.size());
            release_all();
            detach_all();
            store_.edit().clear();
            table_->columns = typename Table::Columns();
            table_->anchors.revoke_and_erase(0, table_->anchors.size(), std::move(kept));
            return;
        }
        detach_all();
        store_.edit().clear();
    }

    bool admit_rename(const ItemKey& key, const std::string& next) const override {
        if constexpr (KeyedItem<T>) {
            std::size_t at = store_.items().size();
            for (std::size_t index = 0; index < store_.items().size(); ++index) {
                if (&KeyTraits<T>::key(*store_.items()[index]) == &key) {
                    at = index;
                    break;
                }
            }
            if (at == store_.items().size()) {
                return false;
            }
            const std::string wanted = KeyTraits<T>::canonical(next);
            for (std::size_t index = 0; index < store_.items().size(); ++index) {
                if (index != at &&
                    KeyTraits<T>::canonical(KeyTraits<T>::key(*store_.items()[index]).value()) == wanted) {
                    throw std::invalid_argument(
                        std::string(KeyTraits<T>::category()) + " '" +
                        detail::printable_id(key.value()) + "' cannot be renamed to '" +
                        detail::printable_id(next) + "': another " +
                        KeyTraits<T>::category() + " already has that id, and ids are unique");
                }
            }
            return true;
        } else {
            (void)key;
            (void)next;
            return false;
        }
    }

   private:
    // Admission of a candidate storage: every item is new to this collection or already its own,
    // appears once, is held by no other live collection, and the ids are unique by canonical key.
    void require_admissible(const std::vector<Ptr>& candidate, const std::string& where) const {
        if constexpr (KeyedItem<T>) {
            for (std::size_t index = 0; index < candidate.size(); ++index) {
                if (!candidate[index]) {
                    throw std::invalid_argument(where + " refuses an empty item");
                }
                for (std::size_t other = index + 1; other < candidate.size(); ++other) {
                    if (candidate[index] == candidate[other]) {
                        throw std::invalid_argument(
                            where + " refuses " + KeyTraits<T>::category() + " '" +
                            detail::printable_id(KeyTraits<T>::key(*candidate[index]).value()) +
                            "' twice: one item is stored once, and ids are unique");
                    }
                }
            }
            std::vector<std::string> keys;
            keys.reserve(candidate.size());
            for (const Ptr& item : candidate) {
                const ItemKey& key = KeyTraits<T>::key(*item);
                if (key.owner() != nullptr && key.owner() != this) {
                    throw std::invalid_argument(
                        where + " refuses " + KeyTraits<T>::category() + " '" +
                        detail::printable_id(key.value()) +
                        "': it already belongs to another collection — add a copy instead");
                }
                keys.push_back(KeyTraits<T>::canonical(key.value()));
            }
            require_unique_ids(keys, KeyTraits<T>::category(), where);
        } else {
            (void)candidate;
            (void)where;  // an unkeyed collection (the background) admits as it always did
        }
    }
    void attach_all() noexcept {
        for (const Ptr& item : store_.items()) {
            if constexpr (KeyedItem<T>) {
                KeyTraits<T>::key(*item).membership_ = membership_;
            }
            RowTraits<T>::link(*item, membership_);
        }
        link_items();
    }
    // A structure's or experiment's own collections take this collection's project link (edi ADR-0024).
    void link_items() noexcept {
        if constexpr (std::is_same_v<T, Structure> || std::is_base_of_v<ExperimentBase, T>) {
            for (const Ptr& item : store_.items()) {
                detail::link_nested(*item, host_link());
            }
        }
    }
    void detach_one(const Ptr& item) noexcept {
        if (!item) {
            return;
        }
        if constexpr (KeyedItem<T>) {
            if (KeyTraits<T>::key(*item).membership_ == membership_) {
                KeyTraits<T>::key(*item).membership_.reset();
            }
        }
        const detail::RowLink* row = RowTraits<T>::primary(*item);
        if (row != nullptr && row->record() == membership_.get()) {
            RowTraits<T>::unlink(*item);
            if constexpr (std::is_same_v<T, Structure> || std::is_base_of_v<ExperimentBase, T>) {
                detail::link_nested(*item, nullptr);  // it left this project
            }
        }
    }
    void detach_all() noexcept {
        for (const Ptr& item : store_.items()) {
            detach_one(item);
        }
    }

    // The items and the identity of their last write, in one place. The vector is private to the
    // store and the only non-const way to it is edit(), which renews the generation first. So no
    // member of the collection — present or future — can change what it holds without recording
    // a write: the compiler refuses the attempt. touch() records a write that changes nothing,
    // which only a self-assignment is.
    class Store {
       public:
        const std::vector<Ptr>& items() const noexcept { return items_; }
        std::vector<Ptr>& edit() noexcept {
            generation_ = detail::Epoch();
            return items_;
        }
        void touch() noexcept { generation_ = detail::Epoch(); }
        std::uint64_t generation() const noexcept { return generation_.value(); }

       private:
        std::vector<Ptr> items_;
        detail::Epoch generation_;
    };

    // ADR-0018: the table's own state — the row anchors, the stamps of its columns and the hold
    // record of each row — as one heap object. It never moves, so it is the owner crysta's anchors
    // name and the address its rows' cells report their writes to, while the collection that holds
    // it may move.
    class Table final : public crysta::detail::RowsBase {
       public:
        Table() : notes{detail::CellHold::value_columns(columns), {}, 0} {
            notes.columns.assign(detail::CellHold::columns<T>(), 0);
        }
        Table(const Table&) = delete;
        Table(Table&&) = delete;
        Table& operator=(const Table&) = delete;
        Table& operator=(Table&&) = delete;
        ~Table() override = default;

        void* row_of(const crysta::detail::RowAnchor* anchor) noexcept override {
            const std::size_t index = anchors.index_of(anchor);
            return index < store->items().size() ? store->items()[index].get() : nullptr;
        }
        const void* row_of(const crysta::detail::RowAnchor* anchor) const noexcept override {
            const std::size_t index = anchors.index_of(anchor);
            return index < store->items().size() ? store->items()[index].get() : nullptr;
        }
        std::uint64_t category_stamp() const noexcept override {
            return std::max(store->generation(), notes.newest);
        }

        // The hold record of `item`, with room for `more` further entries: the record its cells
        // already point at when a table holds it (this one or another), else a new one. This is
        // the allocating step of taking a row, and it changes nothing.
        static std::shared_ptr<detail::RowHold> record_of(const T& item, std::size_t more) {
            const detail::RowHold* held = detail::CellHold::held(item);
            // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast): the record is the tables' own
            std::shared_ptr<detail::RowHold> record =
                held != nullptr ? const_cast<detail::RowHold*>(held)->shared_from_this()
                                : std::make_shared<detail::RowHold>();
            record->tables.reserve(record->tables.size() + more);
            return record;
        }
        // Takes `item` as row `row`, whose values the columns already hold: its cells write to
        // this table from now on, beside every other table that holds the row, and the table
        // notes what they hold.
        void take(T& item, std::shared_ptr<detail::RowHold> record, std::size_t row) noexcept {
            record->tables.push_back(detail::Holding{&notes, row});  // room: record_of
            detail::CellHold::hold(item, record.get());
            detail::CellHold::note_all(item, notes);
            holds.push_back(std::move(record));  // room was reserved by the caller
        }
        // Lets row `row` go, and gives every later row the position it moves to. The item's cells
        // no longer write to this row. An item no table holds any more is a standalone row with
        // its last values.
        void release(T& item, std::size_t row) noexcept {
            const std::shared_ptr<detail::RowHold> record = std::move(holds[row]);
            holds.erase(holds.begin() + static_cast<std::ptrdiff_t>(row));
            drop(item, *record, row);
            for (std::size_t later = row; later < holds.size(); ++later) {
                for (detail::Holding& held : holds[later]->tables) {
                    if (held.table == &notes && held.row == later + 1) {
                        held.row = later;
                        break;
                    }
                }
            }
        }
        void drop(T& item, detail::RowHold& record, std::size_t row) noexcept {
            const auto mine = std::find_if(
                record.tables.begin(), record.tables.end(), [this, row](const detail::Holding& held) {
                    return held.table == &notes && held.row == row;
                });
            if (mine != record.tables.end()) {
                record.tables.erase(mine);
            }
            if (record.tables.empty()) {
                detail::CellHold::hold(item, nullptr);
            }
        }

        // The value columns: every cell of every row, a typed column for each schema column.
        using Columns = detail::RowColumns<T>;
        Columns columns;
        crysta::detail::AnchorList anchors;
        detail::TableNotes notes;
        std::vector<std::shared_ptr<detail::RowHold>> holds;  // each row's hold record, in row order
        const Store* store = nullptr;  // the collection's rows; re-pointed when it moves
    };

    // A collection that never held an item has neither a membership record nor a table. The
    // first admission makes both BEFORE its commit, privately, and `install` hands them to the
    // collection at the commit: a step of the preparation that throws leaves the collection with
    // neither, as it was, so `record()` has not changed for a mutator that refused. A collection
    // holding items always has its record, and the record moves with them. Every collection has
    // the record, keyed or not — an unkeyed row's parameters report their attachment through it
    // too (X12).
    std::shared_ptr<detail::Membership> first_record() const {
        if (membership_) {
            return nullptr;
        }
        std::shared_ptr<detail::Membership> made = std::make_shared<detail::Membership>();
        made->owner = this;
        return made;
    }
    std::unique_ptr<Table> first_table() const {
        if (table_) {
            return nullptr;
        }
        std::unique_ptr<Table> made = std::make_unique<Table>();
        made->store = &store_;
        return made;
    }
    void install(std::shared_ptr<detail::Membership>& record,
                 std::unique_ptr<Table>& table) noexcept {
        if (record) {
            membership_ = std::move(record);
        }
        if (table) {
            table_ = std::move(table);
        }
    }
    // Every row is let go: the cells of each no longer report to this table.
    void release_all() noexcept {
        if (table_) {
            const std::vector<Ptr>& items = store_.items();
            for (std::size_t index = 0; index < items.size(); ++index) {
                table_->drop(*items[index], *table_->holds[index], index);
            }
            table_->holds.clear();
        }
    }
    // Replaces the rows by `candidate`, which the caller has admitted. The table lets every old
    // row go, takes the value columns of the result and every row of it; no item's image moves.
    // Every row of the result gets a new anchor (a whole replacement revokes every prior
    // anchor).
    void replace_rows(std::vector<Ptr> candidate) {
        std::shared_ptr<detail::Membership> record = first_record();
        std::unique_ptr<Table> made = first_table();
        Table& table = made ? *made : *table_;
        // Everything that allocates: the value columns of the result, one hold record for each
        // distinct item of it, with room for every time the result holds it, the list of them,
        // and the anchors.
        typename Table::Columns columns = detail::CellHold::columns_of<T>(candidate);
        std::vector<std::shared_ptr<detail::RowHold>> records;
        records.reserve(candidate.size());
        for (std::size_t index = 0; index < candidate.size(); ++index) {
            const auto first = std::find(candidate.begin(), candidate.begin() + static_cast<std::ptrdiff_t>(index), candidate[index]);
            const std::size_t at = static_cast<std::size_t>(first - candidate.begin());
            if (at < index) {
                records.push_back(records[at]);  // the same item again: its one record
                continue;
            }
            const std::size_t times = static_cast<std::size_t>(
                std::count(candidate.begin(), candidate.end(), candidate[index]));
            records.push_back(Table::record_of(*candidate[index], times));
        }
        std::vector<std::shared_ptr<detail::RowHold>> next_holds;
        next_holds.reserve(candidate.size());
        crysta::detail::AnchorList next =
            crysta::detail::AnchorList::fresh(&table, &Table::anchors, candidate.size());
        std::vector<std::shared_ptr<const void>> kept(table.anchors.size());
        // The commit: nothing below can throw.
        install(record, made);
        std::vector<Ptr>& stored = store_.edit();
        const std::vector<Ptr> old = std::move(stored);
        for (std::size_t index = 0; index < old.size(); ++index) {
            table_->drop(*old[index], *table_->holds[index], index);
        }
        table_->holds = std::move(next_holds);
        stored = std::move(candidate);
        table_->columns = std::move(columns);
        for (std::size_t index = 0; index < stored.size(); ++index) {
            table_->take(*stored[index], std::move(records[index]), index);
        }
        table_->anchors.swap(next);
        next.revoke_and_erase(0, next.size(), std::move(kept));
        table_->anchors.repoint(table_.get());
        for (const Ptr& item : old) {
            if (std::find(stored.begin(), stored.end(), item) == stored.end()) {
                detach_one(item);
            }
        }
        attach_all();
    }

    // The column of schema field `Index`, when that field is `member`.
    template <std::size_t Index, typename Member, typename Found>
    void pick_column(Member member, const Found*& found, const Found& none) const {
        const auto field = std::get<Index>(crysta::RowSchema<T>::fields);
        if constexpr (std::is_same_v<std::remove_const_t<decltype(field)>, Member>) {
            if (field == member) {
                found = table_ ? &std::get<Index>(table_->columns) : &none;
            }
        }
    }
    template <typename Member, typename Found, std::size_t... Index>
    void find_column(Member member, const Found*& found, const Found& none,
                     std::index_sequence<Index...> /*fields*/) const {
        (pick_column<Index>(member, found, none), ...);
    }

    std::shared_ptr<detail::Membership> membership_;
    Store store_;
    std::unique_ptr<Table> table_;
};

// A column crysta computed and published, held as crysta's own immutable buffer. The adapter
// shares it and never copies it, and nothing in edi writes it: edi computes none of these numbers
// (ADR-0073 §1). Empty until a calculation published one.
template <typename T>
class ComputedColumn {
   public:
    using Buffer = std::shared_ptr<const std::vector<T>>;

    ComputedColumn() = default;
    explicit ComputedColumn(Buffer buffer) : buffer_(std::move(buffer)) {}

    const std::vector<T>& values() const noexcept { return buffer_ ? *buffer_ : none(); }
    const Buffer& buffer() const noexcept { return buffer_; }
    std::size_t size() const noexcept { return values().size(); }
    bool empty() const noexcept { return values().empty(); }
    const T& operator[](std::size_t index) const { return values()[index]; }
    auto begin() const noexcept { return values().begin(); }
    auto end() const noexcept { return values().end(); }
    void clear() noexcept { buffer_.reset(); }

   private:
    static const std::vector<T>& none() noexcept {
        static const std::vector<T> empty;
        return empty;
    }

    Buffer buffer_;
};

// One crystallographic site (field names match diffraction-lib and the
// `.edi` format — `_atom_site.id/type_symbol/wyckoff_letter/adp_iso`).
// enable_shared_from_this on the four item types: nanobind's shared_ptr caster then returns a
// true co-owner for an already-shared object instead of an owner-capturing pointer that would
// pin the Python wrapper inside the collection (I4: wrapper release without storage loss). A
// value COPY of an item gets fresh, empty weak state (standard semantics) — deep copies stay
// independent.
struct AtomSite : std::enable_shared_from_this<AtomSite> {
    ItemKey id;  // site id, e.g. "Ca" (the identity-path key);: owned by atom_sites
    // Scattering type symbol, e.g. "Ca". A geometry input: it records its own writes.
    detail::WrittenText type_symbol;
    detail::WrittenText wyckoff_letter = "";  // Wyckoff letter (optional; "" = general)
    // `_atom_site.adp_type` as STORED: "" when the source carried
    // no column; "Biso" when it carried Biso — or Uiso, whose value the loader converts to B at the
    // boundary, so the stored token names the stored representation. Written back iff non-empty. A
    // geometry input: it records its own writes.
    detail::WrittenText adp_type;
    Parameter fract_x;
    Parameter fract_y;
    Parameter fract_z;
    Parameter occupancy{1.0};
    Parameter adp_iso{0.0};  // isotropic ADP stored as Biso (Å²), crysta's convention

    // Attaches the parameter specs. Defined inline in this header so every consumer TU list
    // (the hidden C++ probes compile core sources directly) links unchanged.
    AtomSite();

    // The node's parameters in field order, and the free subset (diffraction-lib's
    // `parameters` / `free_parameters` on every node; the absorbed rows).
    std::vector<Parameter*> parameters() {
        return {&fract_x, &fract_y, &fract_z, &occupancy, &adp_iso};
    }
    std::vector<Parameter*> free_parameters();
    // Whether a collection holds the row this belongs to; that collection sets it.
    detail::RowLink row;
    // This row's identity as a calculation input.
    detail::Epoch epoch;
};

// ADR-0016: an atom-site id keys the site's identity paths and storage.
template <>
struct KeyTraits<AtomSite> {
    static ItemKey& key(AtomSite& site) { return site.id; }
    static const ItemKey& key(const AtomSite& site) { return site.id; }
    static std::string canonical(const std::string& id) { return id; }
    static const char* category() { return "atom site"; }
};

// An atom site is a row of its structure's `atom_sites`.
template <>
struct RowTraits<AtomSite> {
    static void link(AtomSite& site, const std::shared_ptr<detail::Membership>& record) noexcept {
        site.row.link(record);
    }
    static void unlink(AtomSite& site) noexcept { site.row.unlink(); }
    static const detail::RowLink* primary(const AtomSite& site) noexcept { return &site.row; }
};

}  // namespace edi

// ADR-0018: the columns of the `_atom_site` table.
namespace crysta {
template <>
struct RowSchema<edi::AtomSite> {
    static constexpr const char* name = "_atom_site";
    static constexpr auto fields = std::tuple{&edi::AtomSite::id, &edi::AtomSite::type_symbol, &edi::AtomSite::wyckoff_letter, &edi::AtomSite::adp_type, &edi::AtomSite::fract_x, &edi::AtomSite::fract_y, &edi::AtomSite::fract_z, &edi::AtomSite::occupancy, &edi::AtomSite::adp_iso};
    static constexpr std::array items{"id", "type_symbol", "wyckoff_letter", "adp_type", "fract_x", "fract_y", "fract_z", "occupancy", "adp_iso"};
    static constexpr std::array cif{"_atom_site_label", "_atom_site_type_symbol", "_atom_site_Wyckoff_symbol", "_atom_site_fract_x", "_atom_site_fract_y", "_atom_site_fract_z", "_atom_site_occupancy", "_atom_site_B_iso_or_equiv", "_atom_site_U_iso_or_equiv"};
};
}  // namespace crysta

namespace edi {

// The space-group category: the Hermann-Mauguin designation plus the raw ITA
// coordinate-system code — `""` code = absent: the adapter takes the name-only
// resolution path; present => the exact (name, code) setting via crysta's
// resolve_space_group_by_hm_code, all fail-closed policy staying in crysta's resolver.
struct SpaceGroup {
    // e.g. "I 21 3", and e.g. "2" for F d -3 m origin choice 2. Geometry inputs: each records its
    // own writes.
    detail::WrittenText name_h_m;
    detail::WrittenText coord_system_code;
    // `_space_group.it_number` (IUCr IT number). Presence-tracked:
    // absent when the source carried no tag, written back iff present. Identity stays the
    // (name_h_m, coord_system_code) pair the adapter resolves on.
    std::optional<int> it_number;
    // Renewed by every Python write, whatever value it leaves.
    detail::Epoch epoch;
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;
};

// A crystal structure's cell: the six cell parameters.
struct Cell {
    Parameter length_a{1.0};
    Parameter length_b{1.0};
    Parameter length_c{1.0};
    Parameter angle_alpha{90.0};  // degrees
    Parameter angle_beta{90.0};
    Parameter angle_gamma{90.0};

    Cell();  // attaches the parameter specs (inline below, like AtomSite's)

    std::vector<Parameter*> parameters() {
        return {&length_a, &length_b, &length_c, &angle_alpha, &angle_beta, &angle_gamma};
    }
    std::vector<Parameter*> free_parameters();
    // Whether a collection holds the row this belongs to; that collection sets it.
    detail::RowLink row;
    // This row's identity as a calculation input.
    detail::Epoch epoch;
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;
};

// The structure's bond-generation cutoffs, in angstrom. Each is presence-tracked: an unset one
// takes crysta's default (0 and 0.25), and a structure that declares neither writes no `_geom`. edi
// stores them; crysta's bond rule reads them.
struct Geom {
    // Each records its own writes: assigning the value it holds is a write.
    detail::Written<std::optional<double>> min_bond_distance_cutoff;
    detail::Written<std::optional<double>> bond_distance_inc;
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;
};

// A view window in fractional coordinates, inclusive at both ends of each axis (crysta
// `ViewWindow`). It is view state, so edi keeps it and passes it to the read; crysta stores none.
struct ViewWindow {
    std::array<double, 3> min{0.0, 0.0, 0.0};
    std::array<double, 3> max{1.0, 1.0, 1.0};
};

// Crysta's computed structure categories, each column crysta's own immutable buffer (shared,
// never copied, never written here). edi computes none of these numbers: no expansion, no bond,
// no distance and no Cartesian coordinate. Every `id` is positional, the 1-based row.
struct SpaceGroupSymop {  // `_space_group_symop`
    ComputedColumn<std::string> operation_xyz;
    std::size_t size() const noexcept { return operation_xyz.size(); }
};
struct ExpandedAtomSites {  // `_expanded_atom_site`
    ComputedColumn<std::string> atom_site_id;
    ComputedColumn<std::string> site_symmetry;
    ComputedColumn<double> fract_x;
    ComputedColumn<double> fract_y;
    ComputedColumn<double> fract_z;
    ComputedColumn<double> cartn_x;
    ComputedColumn<double> cartn_y;
    ComputedColumn<double> cartn_z;
    ComputedColumn<double> occupancy;
    ComputedColumn<double> u_iso;
    ComputedColumn<std::int32_t> cluster_id;
    std::size_t size() const noexcept { return atom_site_id.size(); }
};
struct GeomBonds {  // `_geom_bond`
    ComputedColumn<std::int32_t> expanded_atom_site_id_1;
    ComputedColumn<std::int32_t> expanded_atom_site_id_2;
    ComputedColumn<std::string> atom_site_label_1;
    ComputedColumn<std::string> atom_site_label_2;
    ComputedColumn<std::string> site_symmetry_1;
    ComputedColumn<std::string> site_symmetry_2;
    ComputedColumn<double> distance;
    std::size_t size() const noexcept { return distance.size(); }
};
struct CartnTransform {  // `_atom_sites_cartn_transform`: r = M x, row-major
    std::array<double, 9> matrix{};
    std::string axes;
};
struct StructureGeometry {
    SpaceGroupSymop space_group_symop;
    ExpandedAtomSites expanded_atom_sites;
    GeomBonds geom_bond;
    CartnTransform atom_sites_cartn_transform;
    ViewWindow window;
};

namespace detail {
struct GeometrySource;  // what a structure's stored geometry was computed from (below)
}  // namespace detail

struct Structure : std::enable_shared_from_this<Structure> {
    // Datablock id, e.g. "ncaf" ("" for programmatic models);: owned by Project::structures,
    // which compares its canonical key (an empty name is `structure`).
    ItemKey name;
    SpaceGroup space_group;
    Cell cell;
    ItemVec<AtomSite> atom_sites;  // Shared items, deep-copied with the structure
    // Element -> coherent bound neutron scattering length b_c (fm). Empty => the adapter uses crysta's
    // default table (load_neutron_scattering); a non-empty map overrides it (isotopes / custom lengths).
    // A loop category held in one cell; written whole or with `modify`.
    detail::Written<std::map<std::string, double>> scattering_lengths_fm;

    // The cell's parameters, then every site's, in collection order.
    std::vector<Parameter*> parameters();
    std::vector<Parameter*> free_parameters();
    // This structure's identity as a calculation input.
    detail::Epoch epoch;

    // The bond cutoffs — an input of the computed structure categories and of nothing else.
    Geom geom;
    // The computed structure categories for the unit cell, crysta's (structure_geometry below), and
    // what they were computed from. Project::calculate() fills them; a value read fills them too.
    StructureGeometry geometry;
    std::shared_ptr<const detail::GeometrySource> geometry_source;
    // Whether `geometry` describes this structure now: it was computed here, and no geometry input
    // — a cell value, the space group, the site rows, a site's id, type symbol, coordinates,
    // occupancy or ADP, `geom` — was written since. Every such input records its own writes
    // (detail::Written, detail::WrittenText, ItemKey, ItemVec::generation), so the answer holds
    // for every route, native ones and equal-value writes included. A write to anything else — the
    // structure's name, its scattering lengths, a Wyckoff letter, an experiment — leaves it
    // current. A UI reads through it and never computes; a copy is never current.
    bool geometry_current() const;
    // The value read: computes `geometry` through crysta when it is not current, then returns it.
    // Throws what crysta throws; nothing earlier stays readable.
    const StructureGeometry& current_geometry();
};

// The ONE geometry read. crysta computes the four categories for `window` from the structure as
// it is now; edi shares the buffers. Pure: it stores nothing. Throws crysta's
// std::invalid_argument on a window or a `geom` value it refuses.
StructureGeometry structure_geometry(const Structure& structure, const ViewWindow& window = {});

// A geometry computed for a view window, with what it was computed from, so its holder can ask
// whether it still describes the structure (window_geometry_current).
struct WindowGeometry {
    StructureGeometry geometry;
    std::shared_ptr<const detail::GeometrySource> source;
};
WindowGeometry window_geometry(const Structure& structure, const ViewWindow& window);
bool window_geometry_current(const Structure& structure, const WindowGeometry& result);

// crysta's defaults for the two `geom` values (0 and 0.25 angstrom), which an unset one takes.
double default_min_bond_distance_cutoff();
double default_bond_distance_inc();

// ADR-0016: a structure name is a datablock, compared by its canonical key.
template <>
struct KeyTraits<Structure> {
    static ItemKey& key(Structure& structure) { return structure.name; }
    static const ItemKey& key(const Structure& structure) { return structure.name; }
    static std::string canonical(const std::string& name) { return datablock_key(name, "structure"); }
    static const char* category() { return "structure"; }
};

// A structure is a row of the project's `structures`; its cell is its parameter category (its
// sites are rows of their own collection).
template <>
struct RowTraits<Structure> {
    static void link(Structure& structure, const std::shared_ptr<detail::Membership>& record) noexcept {
        structure.cell.row.link(record);
    }
    static void unlink(Structure& structure) noexcept { structure.cell.row.unlink(); }
    static const detail::RowLink* primary(const Structure& structure) noexcept {
        return &structure.cell.row;
    }
};

}  // namespace edi

// ADR-0018: the structure collection is a table of datablock rows. Its one column is the id; a
// datablock's own fields live in its own categories.
namespace crysta {
template <>
struct RowSchema<edi::Structure> {
    static constexpr const char* name = "structure";
    static constexpr auto fields = std::tuple{&edi::Structure::name};
    static constexpr std::array items{"data_"};
};
}  // namespace crysta

namespace edi {

// One line-segment background anchor: fixed position (TOF), refinable intensity.
struct LineSegment : std::enable_shared_from_this<LineSegment> {
    detail::Written<double> position{0.0};
    Parameter intensity{0.0};

    LineSegment() { intensity.spec = &spec::background_intensity; }

    std::vector<Parameter*> parameters() { return {&intensity}; }
    std::vector<Parameter*> free_parameters();
    // Whether a collection holds the row this belongs to; that collection sets it.
    detail::RowLink row;
    // This row's identity as a calculation input.
    detail::Epoch epoch;
};

// A background point is a row of its experiment's `background`.
template <>
struct RowTraits<LineSegment> {
    static void link(LineSegment& point, const std::shared_ptr<detail::Membership>& record) noexcept {
        point.row.link(record);
    }
    static void unlink(LineSegment& point) noexcept { point.row.unlink(); }
    static const detail::RowLink* primary(const LineSegment& point) noexcept { return &point.row; }
};

}  // namespace edi

// ADR-0018: the columns of the `_background` table.
namespace crysta {
template <>
struct RowSchema<edi::LineSegment> {
    static constexpr const char* name = "_background";
    static constexpr auto fields = std::tuple{&edi::LineSegment::position, &edi::LineSegment::intensity};
    static constexpr std::array items{"position", "intensity"};
    static constexpr std::array legacy{"_pd_background", "_easydiffraction_background"};
    static constexpr std::array cif{"_pd_background_line_segment_X", "_pd_background_line_segment_intensity"};
    // The `_background.type` this table serves.
    static constexpr std::array variants{"line-segment"};
};
}  // namespace crysta

namespace edi {

// One term of a polynomial or Chebyshev background (diffraction-lib
// `PolynomialTerm`): its fixed order m and its refinable coefficient B_m.
struct PolynomialTerm : std::enable_shared_from_this<PolynomialTerm> {
    detail::Written<int> order{0};
    Parameter coef{0.0};

    PolynomialTerm() { coef.spec = &spec::background_coef; }

    std::vector<Parameter*> parameters() { return {&coef}; }
    std::vector<Parameter*> free_parameters();
    // Whether a collection holds the row this belongs to; that collection sets it.
    detail::RowLink row;
    // This row's identity as a calculation input.
    detail::Epoch epoch;
};

// A background term is a row of its experiment's `background_terms`.
template <>
struct RowTraits<PolynomialTerm> {
    static void link(PolynomialTerm& term, const std::shared_ptr<detail::Membership>& record) noexcept {
        term.row.link(record);
    }
    static void unlink(PolynomialTerm& term) noexcept { term.row.unlink(); }
    static const detail::RowLink* primary(const PolynomialTerm& term) noexcept { return &term.row; }
};

}  // namespace edi

// The columns of the `_background` table when `_background.type` is
// `chebyshev` or `polynomial`. `_background` is a type-switched category: the selector and the
// model's constants are its one-row schema (BackgroundCategory), and each type's rows are the loop
// schema whose `variants` names it.
namespace crysta {
template <>
struct RowSchema<edi::PolynomialTerm> {
    static constexpr const char* name = "_background";
    static constexpr auto fields = std::tuple{&edi::PolynomialTerm::order, &edi::PolynomialTerm::coef};
    static constexpr std::array items{"order", "coef"};
    static constexpr std::array variants{"chebyshev", "polynomial"};
};
}  // namespace crysta

namespace edi {

// ---: the four experiment-type axes (upstream's classification, typed) -------------------
//
// diffraction-lib identifies an experiment by four independent typed enums and selects the item
// class from the combination; edi mirrors the axes exactly (names, values, verbatim tokens) so a
// new axis is a new field, never a new product of enum values. The old single-axis
// `ExperimentKind` and the verbatim `beam_mode` string are retired: consumers switch on
// `experiment_type` axes, and each enum's token IS the verbatim `.edi` spelling.
enum class SampleFormEnum : std::uint8_t { POWDER, SINGLE_CRYSTAL };
enum class BeamModeEnum : std::uint8_t { CONSTANT_WAVELENGTH, TIME_OF_FLIGHT };
enum class RadiationProbeEnum : std::uint8_t { NEUTRON, XRAY };
enum class ScatteringTypeEnum : std::uint8_t { BRAGG, TOTAL };

// The typed peak-profile selector (was the bare `peak_type` string). Only the profiles edi can
// compute are members; the two reserved CW rung tokens stay refused BY NAME in the loader and
// factories exactly as before (they are not representable states).
enum class PeakProfileTypeEnum : std::uint8_t {
    TOF_JORGENSEN,
    TOF_JORGENSEN_VON_DREELE,
    CWL_PSEUDO_VOIGT,
    // Diffraction-lib's members, verbatim.
    CWL_THOMPSON_COX_HASTINGS,
    CWL_PSEUDO_VOIGT_BERAR_BALDINOZZI_ASYMMETRY,
    TOF_PSEUDO_VOIGT,
};

// Verbatim tokens (the `.edi` spellings; the CW beam mode has a SPACE and is quoted on write).
inline const char* token(SampleFormEnum value) {
    return value == SampleFormEnum::POWDER ? "powder" : "single crystal";
}
inline const char* token(BeamModeEnum value) {
    return value == BeamModeEnum::CONSTANT_WAVELENGTH ? "constant wavelength" : "time-of-flight";
}
inline const char* token(RadiationProbeEnum value) {
    return value == RadiationProbeEnum::NEUTRON ? "neutron" : "xray";
}
inline const char* token(ScatteringTypeEnum value) {
    return value == ScatteringTypeEnum::BRAGG ? "bragg" : "total";
}
inline const char* token(PeakProfileTypeEnum value) {
    switch (value) {
        case PeakProfileTypeEnum::TOF_JORGENSEN: return "tof-jorgensen";
        case PeakProfileTypeEnum::TOF_JORGENSEN_VON_DREELE: return "tof-jorgensen-von-dreele";
        case PeakProfileTypeEnum::CWL_PSEUDO_VOIGT: return "cwl-pseudo-voigt";
        case PeakProfileTypeEnum::CWL_THOMPSON_COX_HASTINGS: return "cwl-thompson-cox-hastings";
        case PeakProfileTypeEnum::CWL_PSEUDO_VOIGT_BERAR_BALDINOZZI_ASYMMETRY:
            return "cwl-pseudo-voigt-berar-baldinozzi-asymmetry";
        case PeakProfileTypeEnum::TOF_PSEUDO_VOIGT: return "tof-pseudo-voigt";
    }
    return "tof-jorgensen";
}

// The experiment-type category: four presence-tracked axes (std::optional — absent means the
// source declared nothing; the writer emits a tag iff present) with the declared edi defaults.
// Three defaults match upstream; `beam_mode` deliberately defaults TIME_OF_FLIGHT where upstream
// defaults CW — edi's entire pre-CW corpus is TOF and the loader derives the mode from the
// `_peak.type` family when the tag is absent (argued divergence, parity document).
struct ExperimentType {
    std::optional<SampleFormEnum> sample_form;
    std::optional<BeamModeEnum> beam_mode;
    std::optional<RadiationProbeEnum> radiation_probe;
    std::optional<ScatteringTypeEnum> scattering_type;

    SampleFormEnum effective_sample_form() const { return sample_form.value_or(SampleFormEnum::POWDER); }
    BeamModeEnum effective_beam_mode() const { return beam_mode.value_or(BeamModeEnum::TIME_OF_FLIGHT); }
    RadiationProbeEnum effective_radiation_probe() const {
        return radiation_probe.value_or(RadiationProbeEnum::NEUTRON);
    }
    ScatteringTypeEnum effective_scattering_type() const {
        return scattering_type.value_or(ScatteringTypeEnum::BRAGG);
    }
    // Renewed by every Python write, whatever value it leaves.
    detail::Epoch epoch;
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;
};

// One bank's measured pattern. Supplied by the caller to a joint refinement, and — from — also
// read from a project's embedded `_data.*` loop by the loader. The axis is MODE-NAMED and
// presence-tracked — exactly one of `two_theta` / `time_of_flight` is
// engaged (both-or-neither fails closed at every loader/refinement boundary, and the
// engaged axis must agree with the owning experiment's `experiment_type.beam_mode`);
// `intensity_meas` is the measured intensity and `intensity_meas_su` its standard uncertainty
// (never a derived Poisson approximation). `axis()` is the mode-agnostic accessor.
//
// ADR-0018 §6: the measured columns are columns of the `_data` table, each a recording cell that
// holds the column's values in place, in the node. The vector a read returns is therefore one
// object for as long as the node lives, as the plain vector member was: a reference to it,
// `axis()` included, stays valid and current through the first write to an empty column, through
// every later write, and through a copy, an assignment and a move of the node, whose source keeps
// its own vector objects. A disengaged axis has no vector to refer to, as an empty optional had
// none. A write is an assignment or a
// `write_column`, and each records itself; no non-const reference to the values exists.
struct PdDataBase {
    detail::Written<std::optional<std::vector<double>>> two_theta;
    detail::Written<std::optional<std::vector<double>>> time_of_flight;
    detail::Written<std::vector<double>> intensity_meas;
    detail::Written<std::vector<double>> intensity_meas_su;
    // diffraction-lib's computed `_data` columns on the engaged axis: crysta's published units,
    // which Project::calculate() reads through crysta's current-result path. They land in the
    // model, never returned alongside it, and are empty until a calculation ran. An excluded row's
    // numbers are NaN, never 0; `calc_status` says
    // `incl` or `excl`.
    ComputedColumn<double> d_spacing;
    ComputedColumn<double> intensity_calc;
    ComputedColumn<double> intensity_bkg;
    ComputedColumn<std::string> calc_status;
    // ADR-0021 §2: crysta's residual — measured minus calculated on the included rows, NaN on
    // the excluded ones, empty for a calculation-only experiment. Published with the columns
    // above; never saved, and not a Python member.
    ComputedColumn<double> residual;
    // This data node's identity as a calculation input, and, for a data object handed out by the
    // Python `data` getter, the experiment node it came from.
    detail::Epoch epoch;
    detail::DataSource source;
    // Review 9 F1: renewed by every write to a measured or axis column, whatever value it leaves, so
    // an equal-value write stales the categories; kept apart from `epoch`, which links a handed-out
    // object to this node.
    detail::Epoch written;

    // A write to a measured column or to the axis. The object's computed columns no longer describe
    // it, so they are cleared; and when it was handed out as an experiment's data node that is still
    // the one it came from, the write reaches that node too, whose computed categories its experiment
    // then reads as not current.
    void write_column(detail::Written<std::vector<double>> PdDataBase::* column,
                      std::vector<double> values);
    void write_axis(detail::Written<std::optional<std::vector<double>>> PdDataBase::* axis,
                    std::optional<std::vector<double>> values);
    // Whether this handed-out object's computed columns still describe its experiment — the node it
    // came from is still in place, the experiment's computed categories are current, and these are
    // still that node's columns. An object no getter handed out answers false.
    bool computed_current() const;
    // The computed columns a value read of this handed-out object returns — its experiment's
    // current ones, calculated first when they are not (ExperimentBase::ensure_computed, whose
    // errors it throws). An object no experiment node stands behind — never handed out, or its node
    // since replaced — has no computed columns.
    const PdDataBase& computed_for_read() const;

    void clear_computed() noexcept {
        d_spacing.clear();
        intensity_calc.clear();
        intensity_bkg.clear();
        calc_status.clear();
        residual.clear();
    }

    // The engaged axis — fails closed on none-or-both (I13), so no caller can read an
    // ambiguous pattern.
    const std::vector<double>& axis() const {
        if (two_theta.has_value() == time_of_flight.has_value()) {
            throw std::invalid_argument(
                "edi PdDataBase: exactly one of two_theta / time_of_flight must be engaged");
        }
        return two_theta ? *two_theta : *time_of_flight;
    }
};

// ---: the experiment category tree (the flat 38-field ExperimentBase is retired) -------------

// The peak-profile category. TOF names follow the `.edi`/upstream vocabulary
// (`rise_alpha_*`/`decay_beta_*` the back-to-back exponential, `broad_gauss_*`/`broad_lorentz_*`
// the broadening channels — the channel is named once, in the prefix, per upstream `55f93a10`).
// The five CW parameters keep the presence-tracking idiom: `std::nullopt` means never supplied,
// so a TOF experiment carries no CW state at all; the loader requires all five on a
// `cwl-*` experiment and the adapter fails closed on a programmatic CW model missing one.
struct PeakBase {
    // The profile selector TOKEN (seam 20 / I15, registration-live): the verbatim `_peak.type`
    // string, so a class-plus-registration extension is representable without a rebuild —
    // crysta's storage shape, mirrored. Presence-tracked: absent keeps the historical TOF path
    // and the writer emits `_peak.type` iff present. The three shipped kernels keep their
    // PeakProfileTypeEnum spellings on the Python surface (the view's getter maps them); the
    // two reserved CW rungs stay refused by name in the loader.
    std::optional<std::string> type;
    double cutoff_fwhm = 20.0;
    // TOF Gaussian / back-to-back exponential block.
    Parameter rise_alpha_0, rise_alpha_1, decay_beta_0, decay_beta_1;
    Parameter broad_gauss_sigma_0, broad_gauss_sigma_1, broad_gauss_sigma_2;
    Parameter broad_gauss_size, broad_gauss_strain;
    // TOF Lorentzian (JvD) block; all zero for a pure Jorgensen experiment.
    Parameter broad_lorentz_gamma_0, broad_lorentz_gamma_1, broad_lorentz_gamma_2;
    Parameter broad_lorentz_size, broad_lorentz_strain;
    // CW rung-0 block (Caglioti U/V/W + Lorentz X/Y), presence-tracked.
    std::optional<Parameter> broad_gauss_u, broad_gauss_v, broad_gauss_w;
    std::optional<Parameter> broad_lorentz_x, broad_lorentz_y;
    // The CW asymmetry coefficients, presence-tracked like the block above and engaged only on
    // the `_peak.type` that carries them — Finger-Cox-Jephcoat (S/L, D/L) on
    // `cwl-thompson-cox-hastings`, Berar-Baldinozzi on `cwl-pseudo-voigt-berar-baldinozzi-asymmetry`.
    std::optional<Parameter> asym_fcj_1, asym_fcj_2;
    std::optional<Parameter> asym_beba_a0, asym_beba_b0, asym_beba_a1, asym_beba_b1;
    std::optional<Parameter> asym_beba_limit;  // FullProf AsyLim, deg; default 180

    PeakBase();  // attaches the parameter specs (inline below)

    // The block's parameters in field order, present optionals included (R18).
    std::vector<Parameter*> parameters();
    // Whether a collection holds the row this belongs to; that collection sets it.
    detail::RowLink row;
    // This row's identity as a calculation input.
    detail::Epoch epoch;
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;
};

// The instrument category: the 4-term d<->TOF calibration (it is crysta's instrument[3] and
// diffraction-lib's TofPdInstrument.calib_d_to_tof_reciprocal), the bank take-off angle
// (degrees — the unit lives in the spec metadata, not the name), and the presence-tracked CW
// pair.
struct InstrumentBase {
    Parameter calib_d_to_tof_offset, calib_d_to_tof_linear, calib_d_to_tof_quadratic,
        calib_d_to_tof_reciprocal;
    Parameter setup_twotheta_bank{152.827};
    std::optional<Parameter> setup_wavelength, calib_twotheta_offset;
    // The CW line shifts (SyCos, SySin), presence-tracked — absent is the loader's default 0 on
    // both sides, so a model that never declared them crosses exactly as before.
    std::optional<Parameter> calib_sample_displacement, calib_sample_transparency;
    // The X-ray CW monochromator polarization (K, 2theta_m in degrees), presence-tracked. An X-ray CW
    // load engages both at upstream's default 0 (K = 0 is no correction); a neutron or TOF experiment
    // never carries them.
    std::optional<Parameter> setup_polarization_coefficient, setup_monochromator_twotheta;

    InstrumentBase();  // attaches the parameter specs (inline below)

    std::vector<Parameter*> parameters();  // field order, present optionals included (R18)
    // Whether a collection holds the row this belongs to; that collection sets it.
    detail::RowLink row;
    // This row's identity as a calculation input.
    detail::Epoch epoch;
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;
};

// One row of the `_linked_structure` loop: a structure (phase) the experiment's pattern sums, its
// scale, and whether it takes part. A disabled link is kept and saved but neither calculated nor
// fitted. Keyed by the structure's datablock name.
struct LinkedStructure : std::enable_shared_from_this<LinkedStructure> {
    ItemKey structure_id;  // Owned by the experiment's linked_structures (e.g. "ncaf")
    Parameter scale{1.0};
    detail::Written<bool> enabled{true};

    LinkedStructure() { scale.spec = &spec::linked_structure_scale; }

    std::vector<Parameter*> parameters() { return {&scale}; }  // R18
    // Whether a collection holds the row this belongs to; that collection sets it.
    detail::RowLink row;
    // This row's identity as a calculation input.
    detail::Epoch epoch;
};

// The absorption category — the per-bank FullProf ABSCOR pair behind the `_absorption.*`
// keys: a typed family's parameters exist IFF
// `type` says so — a loaded TOF "cylinder" block always holds both (a missing key defaults to
// 0), any other loaded state holds neither. ABSCOR1 is the wavelength-linear muR coefficient
// (muR = ABSCOR1 * lambda, kernel-proven); ABSCOR2's lambda-power is unpinned in the engine, so
// freeing it is a hard error there and its spelling deliberately stays FullProf's (parity doc).
struct AbsorptionBase {
    std::optional<Parameter> abscor1;
    std::optional<Parameter> abscor2;
    // The CW cylinder body — muR = mu * R (R the cylinder RADIUS), evaluated by the engine at
    // each reflection's Bragg theta. A typed family's parameters exist iff the type says so:
    // TOF "cylinder" carries the ABSCOR pair, CW "cylinder-hewat"/"cylinder-lobanov" carry
    // mu_r, "none" carries nothing.
    std::optional<Parameter> mu_r;
    std::optional<std::string> type;  // `_absorption.type`, e.g. "cylinder" / "none"

    std::vector<Parameter*> parameters();  // the present family body, in order (R18)
    // Whether a collection holds the row this belongs to; that collection sets it.
    detail::RowLink row;
    // This row's identity as a calculation input.
    detail::Epoch epoch;
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;
};

// The largest absolute Miller index a texture axis component may take — the loader's bound, held at
// every programmatic entrance too (crysta's kPreferredOrientationAxisBound).
inline constexpr int kPreferredOrientationAxisBound = 1000;

// One row of upstream's `preferred_orientation` category — the March-Dollase correction of the
// structure `structure_id` names: fitted r and random fraction, a fixed integer
// reciprocal-lattice axis (never [0 0 0]). Constant wavelength only.
struct PrefOrient : std::enable_shared_from_this<PrefOrient> {
    ItemKey structure_id;  // Owned by the experiment's preferred_orientation
    Parameter march_r{1.0};
    Parameter march_random_fract{0.0};
    detail::Written<int> index_h{0};
    detail::Written<int> index_k{0};
    detail::Written<int> index_l{1};

    PrefOrient() {
        march_r.spec = &spec::preferred_orientation_march_r;
        march_random_fract.spec = &spec::preferred_orientation_march_random_fract;
    }

    std::vector<Parameter*> parameters() { return {&march_r, &march_random_fract}; }
    // Whether a collection holds the row this belongs to; that collection sets it.
    detail::RowLink row;
    // This row's identity as a calculation input.
    detail::Epoch epoch;
};

// A `.edi` loop kept exactly as read: its item names without the category prefix, and each row's
// cells as written.
struct CarriedLoop {
    detail::Written<std::vector<std::string>> columns;
    detail::Written<std::vector<std::vector<std::string>>> rows;
};

// A linked structure is keyed by the structure it links, compared as a datablock name.
template <>
struct KeyTraits<LinkedStructure> {
    static ItemKey& key(LinkedStructure& row) { return row.structure_id; }
    static const ItemKey& key(const LinkedStructure& row) { return row.structure_id; }
    static std::string canonical(const std::string& id) { return datablock_key(id, "structure"); }
    static const char* category() { return "linked structure"; }
};

// A linked structure is a row of its experiment's `linked_structures`.
template <>
struct RowTraits<LinkedStructure> {
    static void link(LinkedStructure& row, const std::shared_ptr<detail::Membership>& record) noexcept {
        row.row.link(record);
    }
    static void unlink(LinkedStructure& row) noexcept { row.row.unlink(); }
    static const detail::RowLink* primary(const LinkedStructure& row) noexcept { return &row.row; }
};

// ADR-0016: a texture row is keyed by the structure it corrects.
template <>
struct KeyTraits<PrefOrient> {
    static ItemKey& key(PrefOrient& row) { return row.structure_id; }
    static const ItemKey& key(const PrefOrient& row) { return row.structure_id; }
    static std::string canonical(const std::string& id) { return id; }
    static const char* category() { return "preferred orientation"; }
};

// A texture row is a row of its experiment's `preferred_orientation`.
template <>
struct RowTraits<PrefOrient> {
    static void link(PrefOrient& row, const std::shared_ptr<detail::Membership>& record) noexcept {
        row.row.link(record);
    }
    static void unlink(PrefOrient& row) noexcept { row.row.unlink(); }
    static const detail::RowLink* primary(const PrefOrient& row) noexcept { return &row.row; }
};

}  // namespace edi

// ADR-0018: the columns of the `_linked_structure` table.
namespace crysta {
template <>
struct RowSchema<edi::LinkedStructure> {
    static constexpr const char* name = "_linked_structure";
    static constexpr auto fields = std::tuple{&edi::LinkedStructure::structure_id, &edi::LinkedStructure::scale, &edi::LinkedStructure::enabled};
    static constexpr std::array items{"structure_id", "scale", "enabled"};
    static constexpr std::array legacy{"_easydiffraction_sc_crystal_block", "_sc_crystal_block", "_pd_phase_block"};
};
}  // namespace crysta

// ADR-0018: the columns of the `_preferred_orientation` table.
namespace crysta {
template <>
struct RowSchema<edi::PrefOrient> {
    static constexpr const char* name = "_preferred_orientation";
    static constexpr auto fields = std::tuple{&edi::PrefOrient::structure_id, &edi::PrefOrient::march_r, &edi::PrefOrient::march_random_fract, &edi::PrefOrient::index_h, &edi::PrefOrient::index_k, &edi::PrefOrient::index_l};
    static constexpr std::array items{"structure_id", "march_r", "march_random_fract", "index_h", "index_k", "index_l"};
    static constexpr std::array legacy{"_pd_pref_orient_March_Dollase", "_pref_orient", "_easydiffraction_pref_orient"};
};
}  // namespace crysta

namespace edi {

// The `_refln` loop crysta computed for an experiment, one row per Laue orbit, each column
// crysta's shared buffer. `position` is the reflection's 2θ in degrees on a constant-wavelength
// experiment and its time of flight in µs on a TOF one. Empty until a calculation published it. An
// imported file's own loop stays in `carried_reflections`.
struct PowderReflnDataBase {
    ComputedColumn<std::string> structure_id;
    ComputedColumn<double> d_spacing;
    ComputedColumn<double> sin_theta_over_lambda;
    ComputedColumn<std::int32_t> index_h;
    ComputedColumn<std::int32_t> index_k;
    ComputedColumn<std::int32_t> index_l;
    ComputedColumn<double> f_calc;
    ComputedColumn<double> f_squared_calc;
    ComputedColumn<double> position;
    // For an object the Python `refln` getter handed out, the experiment it came from;
    // unlinked on a copy (detail::DataSource).
    detail::DataSource source;
    // Whether this handed-out object's rows are still its experiment's current `refln`.
    bool computed_current() const;
    // The rows a value read of this handed-out object returns — its experiment's current `refln`,
    // calculated first when it is not (ExperimentBase::ensure_computed, whose errors it throws). An
    // object no getter handed out has no rows.
    const PowderReflnDataBase& computed_for_read() const;

    std::size_t size() const noexcept { return d_spacing.size(); }
    void clear() noexcept {
        structure_id.clear();
        d_spacing.clear();
        sin_theta_over_lambda.clear();
        index_h.clear();
        index_k.clear();
        index_l.clear();
        f_calc.clear();
        f_squared_calc.clear();
        position.clear();
    }
};

// The mode-named leaves (diffraction-lib `PowderCwlReflnData` / `PowderTofReflnData`): the position
// column is `two_theta` on the first and `time_of_flight` on the second.
struct PowderCwlReflnData final : PowderReflnDataBase {
    PowderCwlReflnData() = default;
    explicit PowderCwlReflnData(PowderReflnDataBase base) : PowderReflnDataBase(std::move(base)) {}
};

struct PowderTofReflnData final : PowderReflnDataBase {
    PowderTofReflnData() = default;
    explicit PowderTofReflnData(PowderReflnDataBase base) : PowderReflnDataBase(std::move(base)) {}
};

// A single-bank experiment, categorised: experiment_type / peak / instrument /
// linked_structure / absorption / background / excluded_regions / data. Parameter leaf names
// match the engine's public vocabulary through the adapter's label tables.
namespace detail {
// What an experiment's computed categories — its data node's computed columns and `refln` — were
// calculated from: the encoding of every calculation input at that calculation (calculation_inputs,
// core/src/canonical_encoding.hpp), and the membership records of the collections that held the
// experiment and the structures it was calculated against. A project's record of editor transactions.
// Every admitted edit through the editor (Project::note_edit) renews it, and a calculation records
// it, so an edit stales every bank's computed categories until the next calculation, whatever value
// it leaves and whichever field it writes. Held by the project through EditLog.
struct EditRecord {
    Epoch epoch;
};

// What a structure's stored geometry was computed from — the encoding of every geometry input
// with the identity of its last write (geometry_inputs, core/src/canonical_encoding.hpp). The
// project's editor record is NOT part of it: that record renews on every app edit, whichever
// field it writes, and most fields are no input of the geometry.
//
// The declared relations set coordinates and cell values (edi ADR-0024), so the relations it was
// computed under are recorded too: the owning project's record (null for a structure alone), its alias
// and constraint collections (null for one that has never held a row) and their encoding
// (relation_inputs). The geometry is current only while the structure has that same owner, or none,
// and the declarations are unchanged.
struct GeometrySource {
    std::string inputs;
    std::shared_ptr<const ProjectLink> owner;
    std::shared_ptr<const Membership> aliases;
    std::shared_ptr<const Membership> constraints;
    std::string relations;
};

// The project's handle on its EditRecord, which is never null: a copy starts its own record; an
// assignment is an edit of the target; a move hands the record to the destination and leaves the
// moved-from log a fresh one, so a moved-from project that is assigned or repopulated again still
// owns a record. A move allocates that fresh record before it changes anything, so a failed
// allocation leaves both logs as they were.
class EditLog {
   public:
    EditLog() : record_(std::make_shared<EditRecord>()) {}
    EditLog(const EditLog& /*other*/) : EditLog() {}
    EditLog(EditLog&& other) : record_(std::exchange(other.record_, std::make_shared<EditRecord>())) {}
    // NOLINTNEXTLINE(bugprone-unhandled-self-assignment,cert-oop54-cpp) — an assignment is an edit
    EditLog& operator=(const EditLog& /*other*/) noexcept {
        renew();
        return *this;
    }
    EditLog& operator=(EditLog&& other) {
        if (this != &other) {
            record_ = std::exchange(other.record_, std::make_shared<EditRecord>());
        }
        return *this;
    }
    ~EditLog() = default;

    void renew() noexcept { record_->epoch = Epoch(); }
    const std::shared_ptr<EditRecord>& record() const noexcept { return record_; }

   private:
    std::shared_ptr<EditRecord> record_;  // never null
};

struct ComputedSource {
    std::string inputs;
    std::shared_ptr<const Membership> experiments;
    std::shared_ptr<const Membership> structures;
    std::shared_ptr<const EditRecord> edits;  // the project's editor record, and its identity then
    std::uint64_t edits_at = 0;
    // The project's record and its alias and constraint collections and their encoding then (edi
    // ADR-0024), as GeometrySource records them: a declaration write leaves the computed categories
    // stale, an equal rewrite and a first row included.
    std::shared_ptr<const ProjectLink> owner;
    std::shared_ptr<const Membership> aliases;
    std::shared_ptr<const Membership> constraints;
    std::string relations;
};
}  // namespace detail

struct ExperimentBase : std::enable_shared_from_this<ExperimentBase> {
    // Datablock id, e.g. "wish_1_10";: owned by Project::experiments, which compares its canonical
    // key (an empty name is `experiment`).
    ItemKey name;
    ExperimentType experiment_type;
    // ADR-0014: the X-ray scattering-source selectors, presence-tracked and written back as declared;
    // absent selects crysta's defaults (wk1995 / cromer-liberman).
    std::optional<std::string> xray_form_factor;
    std::optional<std::string> xray_dispersion;
    // ADR-0014: the neutron scattering-length source, same rules; absent serves crysta's default
    // table, rauch2003ext.
    std::optional<std::string> neutron_scattering_length;
    PeakBase peak;
    InstrumentBase instrument;
    // The structures (phases) this experiment's pattern sums, one row for a single phase; a new
    // experiment links one unnamed structure.
    ItemVec<LinkedStructure> linked_structures{
        std::vector<std::shared_ptr<LinkedStructure>>{std::make_shared<LinkedStructure>()}};
    // The one link: the single-phase shortcut. Throws when the experiment links none or several, so
    // a bank of several phases is never read or written as its first one.
    LinkedStructure& linked_structure();
    const LinkedStructure& linked_structure() const;
    AbsorptionBase absorption;
    ItemVec<PrefOrient> preferred_orientation;  // One row per textured linked structure
    ItemVec<LineSegment> background;  // Shared items, deep-copied with the experiment
    // The declared background model (`_background.type`), the one selector: `line-segment`
    // computes from `background`, `chebyshev` (FullProf Nba -5) and
    // `polynomial` (FullProf Nba 0) from `background_terms`. The polynomial declares its origin
    // (FullProf Bkpos), the Chebyshev series its normalisation domain; a model holds only its own
    // type's rows and constants (crysta refuses any other).
    std::string background_type = "line-segment";
    ItemVec<PolynomialTerm> background_terms;
    std::optional<double> background_origin;
    std::optional<double> background_x_min;
    std::optional<double> background_x_max;
    // (start, end) axis pairs. A loop category held in one cell.
    detail::Written<std::vector<std::pair<double, double>>> excluded_regions;
    // The `_refln` loop a file carries — the reflections of the calculation that wrote it
    // (diffraction-lib writes them; crysta's writer does not). edi does not model reflections, so the
    // rows are kept as read, verbatim, shown read-only and never written back. Disengaged = the file
    // declared no `_refln` loop.
    std::optional<CarriedLoop> carried_reflections;
    // The reflections crysta computed, beside the `data` node's computed columns.
    PowderReflnDataBase refln;
    double dataset_weight = 1.0;  // joint-fit weight from analysis.edi
    // This bank's share of the project's last joint fit (`_fit_result_bank`, beside the project's
    // `_fit_result`; crysta's ExperimentBase carries the same): the points it fitted, its weighted-profile
    // R factor and its raw chi-square. Absent when the project holds no joint fit result.
    std::optional<int> fit_n_data_points;
    std::optional<double> fit_prof_wr_factor;
    std::optional<double> fit_chi_square;

    // The bank's embedded measured data, parsed from the `.edi` `_data.*` loop.
    // Presence-tracked: `std::nullopt` means the source file declared no `_data` loop at all.
    // Under the one-loader ruling a loaded project's experiment always carries this field —
    // either measured data (fit-ready) or the `_data_range`-generated grid (calculation-only);
    // an entity built by a factory may still legitimately carry none. The writer round-trips
    // presence: the `_data` loop is written iff this field is engaged.
    std::optional<PdDataBase> data;

    // True iff the source declared a `_data_range.<axis>_min/_max/_step` calculation grid instead
    // of measured data (the project's own contents select calculate vs fit). `data` then holds
    // the generated axis with EMPTY intensity vectors, the fit entry points refuse, and the
    // writer refuses to persist the grid as an observation.
    bool calculation_only = false;

    // The TOF/CW dispatch axis: the declared `experiment_type.beam_mode` where the source
    // carried one, else derived from the TYPED peak profile (a typed-axis read, not a string
    // sniff — pre-epoch files legitimately omit the beam-mode tag), else the edi default. The
    // loader's four-case matrix guarantees a declared value never contradicts the profile.
    BeamModeEnum effective_beam_mode() const {
        if (experiment_type.beam_mode) {
            return *experiment_type.beam_mode;
        }
        if (peak.type && peak.type->starts_with("cwl-")) {  // Every CW rung
            return BeamModeEnum::CONSTANT_WAVELENGTH;
        }
        return BeamModeEnum::TIME_OF_FLIGHT;
    }

    // The calculation `data`'s computed columns and `refln` came from, set by Project::calculate
    // (null = never calculated here). A copy shares it, and is never current: see
    // computed_current().
    std::shared_ptr<const detail::ComputedSource> computed_source;
    // This experiment's identity as a calculation input.
    detail::Epoch epoch;
    // Whether `data`'s computed columns and `refln` describe this experiment now: it is still held
    // by the collection that held it at the calculation, the structures it was calculated against
    // still exist, and no calculation input — a parameter value, a structure, the experiment's
    // settings, background, excluded regions or data grid — has changed since. Every read of the
    // computed categories goes through it (the Python `data` and `refln` getters, the app, save), so
    // a write by any route, or a refused calculation, never leaves an old result readable.
    bool computed_current() const;
    // The value read. When the computed categories are not current it calculates them through the
    // project that holds this experiment, and throws what that calculation throws. An experiment no
    // project holds can neither prove them current nor calculate them, so it throws
    // std::invalid_argument. A UI never calls it: it reads through computed_current() and
    // recalculates on its own queue.
    void ensure_computed();

    // The bank's parameters — peak, instrument, linked structure, absorption, background — in
    // field order, engaged optionals only; and the free subset.
    std::vector<Parameter*> parameters();
    std::vector<Parameter*> free_parameters();
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;
};

// The concrete leaves of the structural adoption — value subclasses over the categorised model, so
// the loader, the factories and Python hand out the one experiment/data shape this product implements
// while the writer and adapter keep consuming the base. Upstream siblings (single-crystal, total
// scattering, Bayesian results) arrive with their physics. The abstract experiment intermediates: the
// powder base homes the pd-shared members exactly where upstream places them; the single-crystal base
// exists and refuses Python construction until its physics arrives (the C++ constructors serve the
// leaf's delegation chain — neither is bound with an init).
struct PdExperimentBase : ExperimentBase {
    PdExperimentBase() = default;
    explicit PdExperimentBase(const ExperimentBase& base) : ExperimentBase(base) {}
    // An experiment's name is an ItemKey, which has no moves, so moving an experiment COPIES it,
    // and a copy-assignment is a checked rename that can refuse. The moves are declared as
    // exactly that — potentially throwing copies — rather than left implicit (crysta's shape
    // too).
    PdExperimentBase(const PdExperimentBase&) = default;
    PdExperimentBase& operator=(const PdExperimentBase&) = default;
    PdExperimentBase(PdExperimentBase&&) noexcept(false) = default;
    PdExperimentBase& operator=(PdExperimentBase&&) noexcept(false) = default;
    ~PdExperimentBase() = default;
};

struct ScExperimentBase : ExperimentBase {
    ScExperimentBase() = default;
    explicit ScExperimentBase(const ExperimentBase& base) : ExperimentBase(base) {}
    // An experiment's name is an ItemKey, which has no moves, so moving an experiment COPIES it,
    // and a copy-assignment is a checked rename that can refuse. The moves are declared as
    // exactly that — potentially throwing copies — rather than left implicit (crysta's shape
    // too).
    ScExperimentBase(const ScExperimentBase&) = default;
    ScExperimentBase& operator=(const ScExperimentBase&) = default;
    ScExperimentBase(ScExperimentBase&&) noexcept(false) = default;
    ScExperimentBase& operator=(ScExperimentBase&&) noexcept(false) = default;
    ~ScExperimentBase() = default;
};

struct BraggPdExperiment final : PdExperimentBase {
    BraggPdExperiment() = default;
    explicit BraggPdExperiment(const ExperimentBase& base) : PdExperimentBase(base) {}
    // An experiment's name is an ItemKey, which has no moves, so moving an experiment COPIES it,
    // and a copy-assignment is a checked rename that can refuse. The moves are declared as
    // exactly that — potentially throwing copies — rather than left implicit (crysta's shape
    // too).
    BraggPdExperiment(const BraggPdExperiment&) = default;
    BraggPdExperiment& operator=(const BraggPdExperiment&) = default;
    BraggPdExperiment(BraggPdExperiment&&) noexcept(false) = default;
    BraggPdExperiment& operator=(BraggPdExperiment&&) noexcept(false) = default;
    ~BraggPdExperiment() = default;
};

// ADR-0016: an experiment name is a datablock, compared by its canonical key.
template <>
struct KeyTraits<BraggPdExperiment> {
    static ItemKey& key(BraggPdExperiment& experiment) { return experiment.name; }
    static const ItemKey& key(const BraggPdExperiment& experiment) { return experiment.name; }
    static std::string canonical(const std::string& name) {
        return datablock_key(name, "experiment");
    }
    static const char* category() { return "experiment"; }
};

// An experiment is a row of the project's `experiments`; its parameter categories are the peak, the
// instrument and the absorption (its linked-structure, background and texture rows are rows of their
// own collections).
template <>
struct RowTraits<BraggPdExperiment> {
    static void link(BraggPdExperiment& experiment,
                     const std::shared_ptr<detail::Membership>& record) noexcept {
        experiment.peak.row.link(record);
        experiment.instrument.row.link(record);
        experiment.absorption.row.link(record);
    }
    static void unlink(BraggPdExperiment& experiment) noexcept {
        experiment.peak.row.unlink();
        experiment.instrument.row.unlink();
        experiment.absorption.row.unlink();
    }
    static const detail::RowLink* primary(const BraggPdExperiment& experiment) noexcept {
        return &experiment.peak.row;
    }
};

}  // namespace edi

// ADR-0018: the experiment collection is a table of datablock rows. Its one column is the id; a
// datablock's own fields live in its own categories.
namespace crysta {
template <>
struct RowSchema<edi::BraggPdExperiment> {
    static constexpr const char* name = "experiment";
    static constexpr auto fields = std::tuple{&edi::BraggPdExperiment::name};
    static constexpr std::array items{"data_"};
};
}  // namespace crysta

namespace edi {

struct PdCwlData final : PdDataBase {
    PdCwlData() = default;
    explicit PdCwlData(PdDataBase base) : PdDataBase(std::move(base)) {}
};

struct PdTofData final : PdDataBase {
    PdTofData() = default;
    explicit PdTofData(PdDataBase base) : PdDataBase(std::move(base)) {}
};

// One accepted iteration, as edi reports it. An edi-owned value type, mapped from the engine's
// progress record in the adapter: the public surface stays engine-free (ADR-0003 — the adapter is
// the ONLY crysta contact), so edi's API does not change shape when crysta's does.
// `reduced_chi_square` and `elapsed_ms` are derived once, engine-side, so no caller re-derives them.
struct IterationRecord {
    int iteration = 0;
    double rwp = 0.0;
    double reduced_chi_square = 0.0;
    double elapsed_ms = 0.0;
    // Trial probes this iteration that the engine rejected because the model was UNEVALUABLE
    // there, as opposed to evaluable-but-worse. Nonzero means the descent was feeling a domain
    // boundary in this iteration. Carried verbatim from the engine's own per-iteration count — edi
    // never recomputes it (ADR-0009).
    int unevaluable_trials = 0;
    // The step's parameter values by edi identity path — what a live surface draws the pattern of.
    // Carried on the streamed record only (a subscriber's); the history keeps none.
    std::map<std::string, double> values;
};

// Why a refinement stopped — deliberately NOT collapsed into `converged`, so a fit that exhausted
// its iteration budget is distinguishable from one that could not take a step. Mirrors the engine's
// REACHABLE set; diverged/singular are reserved there and never emitted, because nothing detects
// them today. adds UNAVAILABLE: the fit did not converge and the CAUSE was not persisted, so it
// cannot be reported. It is reached only by reconstruction from a scan's `results.csv`, which
// records a success BIT and no cause — never by a live fit, which always knows whether it exhausted
// its budget or could not take a step. Mirrors crysta::FitStatus::Unavailable (ADR-0057 shape).
// adds SUPERSEDED (ADR-0057): a model input was written while the fit ran, so the fit published
// nothing. Mirrors crysta::FitStatus::Superseded.
enum class FitStatus : std::uint8_t {
    DONE,
    MAX_ITER,
    NO_STEP,
    CANCELLED,
    ERROR,
    UNAVAILABLE,
    SUPERSEDED
};

// Optional per-iteration progress subscriber. Passing none costs nothing: with no subscriber there
// is no host crossing at all, while the history below is populated either way.
using IterationCallback = std::function<void(const IterationRecord&)>;

// The cooperative cancel predicate crysta polls between iterations (and a scan once more before
// committing a file's row). True stops the fit cleanly: a single or joint fit returns its
// partial result as CANCELLED; a scan records no row for the unfinished file, writes nothing
// back, and leaves analysis/results.csv as the resume point. Empty = never.
using CancelCallback = std::function<bool()>;

// The facts a live surface needs BEFORE iteration 1 to print the streamed table's header and pre-fit
// starting row — bank names, both point counts, the free count, and the initial-model (pre-fit)
// record. edi-owned and adapter-local: the adapter assembles it from facts it already owns once the
// residual provider is built, and delivers it to the host BEFORE it ever calls crysta.
// `pre_fit` is iteration 0 (the initial model's Rwp/reduced-chi2 at the start params), so the human
// table can open with it and iteration 1 can show its improvement over it.
struct FitPreamble {
    bool joint = false;
    std::vector<std::string> banks;  // bank names (joint); empty for a single-bank fit
    std::size_t n_points_loaded = 0;
    std::size_t n_points_fitted = 0;
    std::size_t n_free = 0;
    IterationRecord pre_fit;
};

// Optional one-shot preamble subscriber, fired exactly once before the LM loop. Like
// `IterationCallback`, passing none costs nothing (no host crossing). Surface-local: this seam does
// not cross into crysta — the adapter owns the facts and publishes them to edi's host.
using PreambleCallback = std::function<void(const FitPreamble&)>;

// One completed scan file, fired after crysta's driver has APPENDED that file's results.csv
// row. Every field is read back from the committed row, never computed alongside it;
// `file_name` is the scan file's own name, no directory. `converged` mirrors the row's success
// cell — the field a progress line's ok/fail split and a summary's NAMED failures both come
// from.
struct ScanFileRecord {
    std::string file_name;
    bool converged = false;
    double reduced_chi_square = 0.0;
    int iterations = 0;
    // The row's cells as crysta appended them (the live event; empty for a resumed row read back).
    std::vector<std::string> cells;
    // Why the file's fit stopped, as crysta's ledger (results-provenance.csv) records it beside the row; empty when
    // it was not recorded.
    std::string termination;
};

// Optional per-file completion subscriber. Passing none costs nothing: with no
// subscriber the adapter never reads the CSV mid-scan at all.
using FileCompleteCallback = std::function<void(const ScanFileRecord&)>;

// The whole-scan preamble, fired exactly once before the first file's fit — the seam a progress
// surface takes its `N` from (the count comes from HERE, never from counting iteration
// restarts). `total_files` is the declared walk's size; `completed_rows` is every row ALREADY
// recorded in analysis/results.csv when the call resumes a partial scan — empty on a fresh one
// — so a resumed scan's aggregates start truthful. Surface-local like FitPreamble: the adapter
// derives the facts (the same walk and resume rows crysta's driver reads) and publishes them to
// edi's host; nothing crosses into crysta.
//
// Review-1 F2: the prior state crosses this seam as the ROWS THEMSELVES, never as counters
// beside them. The retired shape carried `completed_files`/`ok_count`/`fail_count` and no
// per-file facts, so a consumer could only seed whole-scan COUNTERS from history while its
// names, chi-squares and elapsed time covered this invocation alone — one scan presented from
// two populations. Carrying the rows makes that split unspellable HERE rather than merely
// unspelled: there is no count to seed independently of the facts it counts, so every scan-wide
// aggregate a consumer forms is a fold over one population. The one quantity history cannot
// supply is TIME — a committed row records iterations, never duration — so elapsed-based
// quantities stay explicitly current-run and say so (report.hpp `measured_completed`).
struct ScanPreamble {
    int total_files = 0;
    std::vector<ScanFileRecord> completed_rows;
};

// Optional whole-scan preamble subscriber. Passing none costs nothing (no host crossing); it
// fires only when the scan walk is resolvable — an unresolvable walk is crysta's refusal to
// make, and a preamble for a scan that cannot start would report a fabrication.
using ScanStartCallback = std::function<void(const ScanPreamble&)>;

// The outcome of a whole-fit refinement: edi delegates the entire Levenberg-Marquardt loop to crysta's
// public minimizer (crysta::fit_problem, ADR-0005) through the adapter and maps the result back. edi's own
// value type — no crysta type OR engine label crosses the boundary (ADR-0003 pt 5). `values`/`uncertainty`
// are keyed by **edi-owned parameter identity paths** that resolve through the public model (e.g.
// `experiment.sigma2`, `structure.atom_sites[Ca].fract_x`,
// `experiment.background[0].intensity`) — never a raw crysta label (Ca.x / offset / background[0]).
// The adapter's crysta-label -> edi-path translation is total and fail-closed; the same refined
// value + e.s.d. is also written back onto the project's own model Parameters (Project::fit). One
// bank's post-fit goodness metrics, edi's own value type over crysta::BankMetric. Every field is
// COMPUTED BY THE ENGINE and merely carried here — nothing recomputes a metric on the edi side, and
// above all not in the example, whose job is presentation only.
struct BankMetric {
    std::string name;          // the bank's datablock id, e.g. "wish_5_6"
    std::size_t n_points = 0;  // points remaining after that bank's excluded regions are applied
    double rwp = 0.0;          // that bank's weighted-profile R-factor (NOT the global one)
    double chi_square = 0.0;   // that bank's raw chi-square
};

struct FitResultBase {
    std::map<std::string, double> values;  // edi-owned identity path -> refined value
    std::map<std::string, double> uncertainty;     // edi-owned identity path -> refined standard uncertainty
    // Pre-fit value per identity path, captured from the engine provider BEFORE the minimizer runs
    // and translated through the same resolver as `values`, so `start` and `values` share one key
    // set. This is what lets a caller render a start-vs-value "change" column without re-reading
    // the project or re-deriving anything.
    std::map<std::string, double> start;
    // Per-bank metrics, captured from the live joint provider before it is destroyed. **Joint
    // refinement only — empty for a single-bank fit**, mirroring crysta exactly: its
    // single-file result carries no per-bank block, and its `full` per-bank line is joint-only.
    std::vector<BankMetric> banks;
    double rwp = 0.0;                 // weighted-profile R-factor (global)
    double reduced_chi_square = 0.0;  // reduced chi-square (goodness-of-fit)
    int iterations = 0;
    bool converged = false;
    // . Both point counts, named — reporting only one of them under a `pts` heading is: `loaded`
    // is what the project carried, `fitted` is what entered the residual (after each bank's
    // excluded regions), and reduced chi-square is normalised by the FITTED count. On the
    // single-bank path `banks` is empty, so neither count is derivable from it; they are
    // first-class fields precisely so both paths can answer.
    std::size_t n_points_loaded = 0;
    std::size_t n_points_fitted = 0;
    // Per-iteration history. ALWAYS populated, callback or not: a notebook caller cannot consume a
    // streaming callback after the fact, so the history has to be readable off the result. Collected
    // by crysta::IterationHistoryCollector, the one place rwp/reduced-chi2/elapsed are derived.
    std::vector<IterationRecord> iterations_history;
    // The pre-fit record (iteration 0) — the initial model's Rwp/reduced-chi2 evaluated at the
    // start params BEFORE any refinement step (crysta::pre_fit_record). ALWAYS populated, callback
    // or not, so the post-hoc human report can render the pre-fit starting row and seed iteration
    // 1's `change` from it — mirroring `iterations_history`. Not a minimizer step.
    IterationRecord pre_fit;
    // Wall time of the refinement itself, measured around the minimizer call.
    double elapsed_ms = 0.0;
    // Why the fit stopped, as the machine record reports it — distinct from `converged`, so a fit
    // that hit the iteration cap is distinguishable from one that could not take a step.
    FitStatus status = FitStatus::DONE;
    // The engine's boundary-contact diagnostic: trial probes rejected because the model was
    // unevaluable there — over the whole descent, and in the final executed iteration
    // specifically. Both are 0 on a boundary-free fit. A `converged` outcome with a nonzero
    // terminal count stopped while the descent was still feeling a domain boundary — the one
    // signal that separates boundary-limited convergence from an interior optimum. Counts, never a
    // threshold; carried verbatim from the engine.
    int unevaluable_trials = 0;
    int terminal_unevaluable_trials = 0;
    // The SAME refined values and e.s.d.s, keyed by crysta ENGINE label rather than by edi identity
    // path. Retained because the machine record is crysta's artifact and must use crysta's
    // parameter identity on every surface: at `full` the record carries two lines per parameter, so
    // a different spelling on each side would make every one of them differ and the cross-surface
    // diff would prove nothing. edi's identity paths remain the key set of
    // `values`/`uncertainty`/`start` and are what the HUMAN format shows.
    std::map<std::string, double> engine_values;
    std::map<std::string, double> engine_uncertainty;
    // The descent-flow registry id the engine reports for this run (crysta schema 7) — carried
    // verbatim: the machine record must name its descent, and edi never re-derives an engine
    // fact (ADR-0009).
    std::string descent;
    // The engine's work counters, carried verbatim — per bank whether its reflection sum ran
    // folded, and the number of reflection structure factors the solve evaluated (crysta
    // FitResultBase). They are counts, not timings, so the same project fitted through crysta's
    // own Python package reports the same numbers.
    std::vector<bool> reflections_folded;
    std::uint64_t structure_factor_evaluations = 0;
};

// The least-squares concrete result: the leaf every fit entry point hands back — edi has one minimizer
// path; `BayesianFitResult` arrives with the Bayesian
// feature (D43), which also brings the result-kind selection seam.
struct LeastSquaresFitResult final : FitResultBase {
    LeastSquaresFitResult() = default;
    explicit LeastSquaresFitResult(FitResultBase base) : FitResultBase(std::move(base)) {}
};

// The descent-strategy registry, forwarded from the LINKED crysta engine at call time:
// `descent_ids()` is registration order — exactly crysta's `--list-descents` order — and
// `default_descent()` is the id an omitted selection runs. edi transcribes neither (the
// anti-drift contract: the set is crysta's, resolved from crysta, so the two surfaces cannot
// diverge by construction).
std::vector<std::string> descent_ids();
std::string default_descent();
// The absorption vocabulary and its two spellings are crysta's own table, asked through the
// adapter. edi keeps no list and no mapping of its own.
//   - the spellings a file of this beam mode may declare;
//   - the file spelling of `token`, which may already be one or may be crysta's registry token
//     (`cylinder-hewat` on time-of-flight is the file's `cylinder`); an unknown one throws
//     std::invalid_argument;
//   - crysta's registry token of a file spelling — the word edi's class registry is keyed by.
std::vector<std::string> absorption_file_tokens(BeamModeEnum mode);
std::string absorption_file_token(BeamModeEnum mode, const std::string& token);
std::string absorption_registry_token(BeamModeEnum mode, const std::string& file_token);
// A peak type registered at run time (edi::register_peak_type, the Python registration seam) is
// registered with crysta's peak registry too, which is the vocabulary the crossing reads: a type
// edi alone knew would be refused there. It computes with its family's base profile, as before.
// Idempotent.
void register_engine_peak_type(const std::string& token, BeamModeEnum mode);
// The hooks a crysta-vs-edi parity check reads. `engine_model_dump` is crysta's own dump of the
// engine project a calculation of `project` builds — the model in MODEL tokens, which a saved
// file cannot show; the other two are crysta's fold resolution for that engine project and its
// structure-factor work counter.
std::string engine_model_dump(const Project& project);
bool engine_folds_reflections(const Project& project);
std::uint64_t engine_structure_factor_evaluations() noexcept;
// The chi-square tolerance a fit uses when `_minimizer.chi_square_tolerance` is not declared: the
// LINKED crysta's default, forwarded like default_descent() (the app shows the value the minimizer
// actually uses).
double default_chi_square_tolerance();
// The iteration bound a fit uses when `_minimizer.max_iterations` is not declared (the fit policy's cap),
// for the app to show the value the minimizer actually uses, as the tolerance above.
int default_max_iterations();

// Fail-closed descent-id validation at edi's boundary: an unknown non-empty id throws
// std::invalid_argument naming the registered set (the ADR-0060 shape) — edi never passes an id
// through for crysta to reject, because that error would name crysta's surface to an edi user.
// `where` prefixes the message ("edi fit", "edi descent", ...). Empty is "no selection".
void validate_descent(const std::string& descent, const std::string& where);

// Project metadata container: the plain data the upstream category carries as descriptors.
// Timestamps are STAR-format strings ('%d %b %Y %H:%M:%S', UTC — upstream
// _PROJECT_TIMESTAMP_FORMAT); `timestamp` empty = no fit recorded yet. Persisted as
// `project.edi`'s `_metadata.*` block: the delegated save writes it (crysta's engaged writer) and
// `load_project` restores it, so the round trip is identity on every written field. Mirrors
// crysta.
struct ProjectMetadata {
    ProjectMetadata();
    std::string name = "untitled_project";
    std::string title = "Untitled Project";
    std::string description;
    std::string path;           // kept in step with Project.path by load / save_as
    std::string created;        // construction time (UTC)
    std::string last_modified;  // construction time; update_last_modified() refreshes
    std::string timestamp;      // latest fit timestamp; empty = none
    void update_last_modified();
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;
};

// One `_sequential_fit_extract` rule — a regex applied line-by-line to a scan data file's
// text; the first matching line's capture group 1 lands in the results.csv column named by
// `target` (e.g. `diffrn.ambient_temperature`). Mirrors crysta's SequentialExtractRule.
struct SequentialExtractRule {
    ItemKey id;  // Unique within SequentialFitConfig::extract
    detail::WrittenText target;
    detail::WrittenText pattern;
    detail::Written<bool> required{std::in_place, true};
};

// ADR-0016: an extract-rule id names one scan rule.
template <>
struct KeyTraits<SequentialExtractRule> {
    static ItemKey& key(SequentialExtractRule& rule) { return rule.id; }
    static const ItemKey& key(const SequentialExtractRule& rule) { return rule.id; }
    static std::string canonical(const std::string& id) { return id; }
    static const char* category() { return "sequential-fit extract rule"; }
};

}  // namespace edi

// ADR-0018: the columns of the `_sequential_fit_extract` table.
namespace crysta {
template <>
struct RowSchema<edi::SequentialExtractRule> {
    static constexpr const char* name = "_sequential_fit_extract";
    static constexpr auto fields = std::tuple{&edi::SequentialExtractRule::id, &edi::SequentialExtractRule::target, &edi::SequentialExtractRule::pattern, &edi::SequentialExtractRule::required};
    static constexpr std::array items{"id", "target", "pattern", "required"};
};
}  // namespace crysta

namespace edi {

// One `_alias` row (diffraction-lib `Alias`): the short name an expression uses, and the unique name
// (`<datablock>.<category>[.<entry>].<name>`) of the parameter it stands for.
struct ParameterAlias {
    ItemKey id;
    detail::WrittenText parameter_unique_name;
};

template <>
struct KeyTraits<ParameterAlias> {
    static ItemKey& key(ParameterAlias& alias) { return alias.id; }
    static const ItemKey& key(const ParameterAlias& alias) { return alias.id; }
    static std::string canonical(const std::string& id) { return id; }
    static const char* category() { return "alias"; }
};

// One `_constraint` row (diffraction-lib `Constraint`): `<alias> = <expression>`, kept as declared.
// crysta parses it; edi never does. A disabled constraint stays in the project and is not applied.
struct ParameterConstraint {
    ItemKey id;
    detail::WrittenText expression;
    detail::Written<bool> enabled{std::in_place, true};
};

template <>
struct KeyTraits<ParameterConstraint> {
    static ItemKey& key(ParameterConstraint& constraint) { return constraint.id; }
    static const ItemKey& key(const ParameterConstraint& constraint) { return constraint.id; }
    static std::string canonical(const std::string& id) { return id; }
    static const char* category() { return "constraint"; }
};

}  // namespace edi

namespace crysta {
template <>
struct RowSchema<edi::ParameterAlias> {
    static constexpr const char* name = "_alias";
    static constexpr auto fields = std::tuple{&edi::ParameterAlias::id, &edi::ParameterAlias::parameter_unique_name};
    static constexpr std::array items{"id", "parameter_unique_name"};
};
template <>
struct RowSchema<edi::ParameterConstraint> {
    static constexpr const char* name = "_constraint";
    static constexpr auto fields = std::tuple{&edi::ParameterConstraint::id, &edi::ParameterConstraint::expression, &edi::ParameterConstraint::enabled};
    static constexpr std::array items{"id", "expression", "enabled"};
};
}  // namespace crysta

namespace edi {

// The analysis.edi `_sequential_fit.*` declaration (mirrors crysta's SequentialFitConfig): a
// directory of per-file scan data fitted one after another against the single template
// experiment, by crysta's own sequential driver — edi carries the declaration across the
// boundary and never re-implements the loop or the CSV writer (criterion 6's one writer,
// literal).
struct SequentialFitConfig {
    std::string data_dir;
    std::string file_pattern = "*";
    bool reverse = false;
    // The template dataset: the scan file whose data the template experiment holds (set_scan_template_file).
    std::string template_file;
    ItemVec<SequentialExtractRule> extract;  // Ids unique by construction
    bool declared() const { return !data_dir.empty(); }
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;
};

// The last fit's result, as analysis.edi persists it in diffraction-lib's `_fit_result` category
// (crysta's FitResultRecord, which a save hands it to). A fit records it (Project::fit,
// Project::fit_joint), an undo clears it, a load restores it; held while `result_kind` is set. Fields
// crysta does not compute yet (the profile R factor, the expected R, shift/s.u., correlations, the
// single-crystal R factors) are not carried; each bank's share of a joint fit is on its experiment.
struct FitResultRecord {
    std::string result_kind;  // `deterministic`; empty: no fit result is held
    bool success = false;
    std::string message;
    int iterations = 0;
    double fitting_time = 0.0;  // seconds
    double reduced_chi_square = 0.0;
    std::string objective_name;
    double objective_value = 0.0;
    int n_data_points = 0;
    int n_parameters = 0;
    int n_free_parameters = 0;
    int degrees_of_freedom = 0;
    bool covariance_available = false;
    std::string exit_reason;  // crysta's status label: done, max_iter, no_step, cancelled
    double prof_wr_factor = 0.0;
    std::string profile_function;     // empty: not written
    std::string background_function;  // empty: not written
    // The descent that produced the result, so a reopened result names its own minimizer rather than the
    // one selected since; empty in a record written before it.
    std::string descent;
    bool held() const { return !result_kind.empty(); }
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;
};

// The CLOSED declared set of `_fitting_mode.type` values, in ONE place on this side of the
// boundary. It MUST equal crysta's set (crysta/model.hpp
// `is_declared_fitting_mode`); the two copies exist because edi's core keeps engine types out of
// everything but adapter.cpp (ADR-0003, and the unit tier builds without the engine), so the
// equality is held by a gate rather than by a shared symbol. Do not add a value to one side only.
//
//   single       one experiment, one fit
//   joint        several banks, one simultaneous fit
//   sequential   scan: each file seeded from the previous fit's converged parameters
//   independent  scan: each file seeded from the SAME initial parameters
// Both scan modes execute SERIALLY; the distinction is the starting point, never concurrency.
inline bool is_declared_fitting_mode(const std::string& mode) {
    return mode == "single" || mode == "joint" || mode == "sequential" || mode == "independent";
}
// True for the two modes driven by crysta's scan driver over a declared `_sequential_fit` block.
// A site that means "a scan" asks this instead of comparing against `sequential` and forgetting
// `independent` — which is exactly how the mode contract drifted in the first place.
inline bool is_scan_fitting_mode(const std::string& mode) {
    return mode == "sequential" || mode == "independent";
}
inline std::string declared_fitting_modes() {
    return "'single', 'joint', 'sequential', 'independent'";
}

// The SPELLING half of the scan-directory containment rule, mirroring crysta's
// `validate_sequential_data_dir`. edi never resolves `data_dir` against a filesystem
// itself (crysta's driver owns that, and owns the symlink check with it), so this side rejects
// the spellings that can be judged without one: empty, absolute, or carrying a `..` component.
// Refusing here means an escaping declaration never crosses the boundary at all.
inline void validate_sequential_data_dir(const std::string& data_dir, const std::string& where) {
    if (data_dir.empty()) {
        throw std::invalid_argument("_sequential_fit.data_dir is empty" + where);
    }
    const std::filesystem::path declared(data_dir);
    if (declared.is_absolute() || declared.has_root_name() || declared.has_root_directory()) {
        throw std::invalid_argument("_sequential_fit.data_dir '" + data_dir +
                                    "' is absolute - it is declared RELATIVE to the project "
                                    "directory" +
                                    where);
    }
    for (const std::filesystem::path& part : declared) {
        if (part == "..") {
            throw std::invalid_argument("_sequential_fit.data_dir '" + data_dir +
                                        "' contains a '..' component - it is declared RELATIVE "
                                        "to the project directory and may not leave it" +
                                        where);
        }
    }
}

// The top-level user object. calculate(tof_grid) runs the edi model through the crysta adapter and
// returns the calculated intensity on the supplied TOF grid (len == tof_grid.size()); the grid is
// the caller's argument (no measured data needed for a pure forward calculation).
class Project : public detail::ProjectAnchor {
   public:
    // A default project holds ONE default structure and ONE default experiment, so the
    // programmatic single-block flow (`p.structure()...`, `calculate()`) works unchanged;
    // the loader replaces both vectors wholesale.
    Project()
        : structures(std::vector<ItemVec<Structure>::Ptr>{std::make_shared<Structure>()}),
          experiments(std::vector<ItemVec<BraggPdExperiment>::Ptr>{
              std::make_shared<BraggPdExperiment>()}) {}
    // The copying (Structure, BraggPdExperiment) constructor is RETIRED at every exposure
    // layer — native included, not just the Python
    // overload. Population goes through the collections; deleted, not removed,
    // so a reintroduction at any call site is a compile error naming this ruling.
    Project(Structure, BraggPdExperiment) = delete;

    // The reference-shaped forward calculation (diffraction-lib `Analysis.calculate`): NO
    // arguments — the model is the single source of truth. Iterates every experiment; per bank
    // the grid is the data node's engaged axis, the bank angle and window cutoff are the
    // experiment's own declared values, and the scattering lengths are the structure's
    // declared map (else the built-in table). Crysta calculates and publishes every bank at
    // once, and edi reads the published units through crysta's current-result path into each
    // experiment's computed `data` columns and `refln`, never returned alongside the model.
    // Every bank gets its results, or none does. Fails closed (std::invalid_argument -> Python
    // ValueError) on an experiment without a data node.
    void calculate();

    // The fit and undo POSTCONDITION: make the stored calculated pattern describe the model it
    // sits beside. Ordinarily `calculate()` at the current state. A model can legitimately have NO
    // calculable pattern (a converged fit can move the declared CW grid's corrected span out of
    // (0, 180) deg, which the forward path refuses by design), and then the stored pattern is
    // CLEARED rather than left holding a series describing a model that is gone: clearing is the
    // post-load state, so it makes no claim and every consumer already handles it, while keeping
    // the old series would be a stale pattern nothing marks stale and propagating would make a
    // CONVERGED fit raise after writing its values. Absorbs only the declared
    // std::invalid_argument "cannot be calculated" failure; anything else propagates.
    void refresh_calculated_pattern();

    // THE FIT-COMPLETION CONTRACT, binding on every `fit*` entry below. Completing a fit writes BOTH
    // halves of the model: the fitted values AND the stored calculated pattern beside them. Each fit
    // path refreshes `data->intensity_calc` for every experiment it fitted, through `calculate()`
    // above — the ordinary model-only forward path, run LAST so the pattern describes the model a
    // SAVE would serialise — so the stored pattern always equals a fresh calculate at the fitted
    // state and no consumer has to ask for it. The two halves always move together — nothing marks a
    // half-refreshed project stale, so a partial refresh would be worse than a stale one. A fit that
    // REFUSES (every boundary check throws before any write-back) writes neither. There is no
    // cancellation to rule on here: edi's fit entries take no cancel callback and pass none to
    // crysta, so no edi fit returns a cancelled result, and a fit stopped by an exception out of the
    // solve (a raising subscriber included) unwinds before
    // `detail::write_back` and writes neither half either. crysta owns its own rule for its own
    // callers' models, independently, and there a cancelled direct fit publishes its partial result
    // with both halves coherent; `edi.Analysis` is delegation only and owns neither.

    // Whole-fit refinement: delegate the entire LM loop to crysta's public minimizer
    // (crysta::fit_problem, ADR-0005) through the adapter, over the measured pattern (TOF
    // `grid`, `observed` intensity, `sigma`). The free set is the model's own bracket flags (each
    // Parameter.free), mirroring the crysta CLI `--free model`; the excluded regions mask the data
    // exactly as the CLI does, and the solver runs at the CLI defaults so the result is comparable
    // to the published path. The refined values + e.s.d.s are written back onto this project's model
    // Parameters and returned as a FitResultBase. Stateless: crysta objects are rebuilt per call (the
    // cached/incremental path is a later C09 slice; this method does not foreclose it). Fails closed
    // with std::invalid_argument (-> Python ValueError) on empty measured data or an unrefinable /
    // unresolvable model — never a partial or silent result (the model is written only after a
    // successful fit).
    // `on_iteration` is an OPTIONAL progress subscriber, called once per accepted
    // step. Passing none costs nothing: no subscriber means no host crossing at all (the internal
    // history collector runs either way — see FitResultBase::iterations_history).
    // `on_start` is an OPTIONAL one-shot preamble subscriber, fired exactly once after the
    // provider is built (so n_points_fitted/n_free/bank names are known) and after the pre-fit is
    // evaluated, BEFORE crysta::fit_problem — the seam a live surface prints its header + pre-fit
    // row from. This is a provider-building overload: it owns the single fire point. Passing none
    // costs nothing.
    FitResultBase fit(const std::vector<double>& grid, const std::vector<double>& observed,
                      const std::vector<double>& sigma, const IterationCallback& on_iteration = {},
                      const PreambleCallback& on_start = {},
                      const CancelCallback& should_cancel = {});

    // Joint multi-bank refinement: refine every loaded bank in ONE Levenberg-Marquardt problem,
    // delegating the whole loop to crysta's joint minimizer through the adapter. `patterns` carries
    // one measured pattern per entry of `experiments`, in that same order. The free set and its
    // column layout are crysta's own (one shared structural block followed by each bank's instrument
    // block); edi only marshals each Parameter's free flag, so the fit is comparable to the
    // published `crysta fit <project>` path.
    //
    // Results are keyed by edi-owned identity paths that name their bank —
    // `experiments[<bank>].sigma2`, `experiments[<bank>].background[3].intensity`,
    // `experiments[<bank>].abscor1` — while shared structural parameters keep their single
    // `structure....` path. Every engine label is translated BEFORE any write-back, so an unmapped
    // label leaves the model untouched; there is no bank-0 fallback anywhere. Fails closed with
    // std::invalid_argument (-> Python ValueError) on a pattern/bank count mismatch, an unusable
    // bank identity, empty or ragged data, a bank fully removed by its exclusions, or an
    // unrefinable model. Stateless: crysta objects are rebuilt per call, as Project::fit is.
    FitResultBase fit_joint(const std::vector<PdDataBase>& patterns,
                            const IterationCallback& on_iteration = {},
                            const PreambleCallback& on_start = {},
                            const CancelCallback& should_cancel = {});

    // The one-call forms: refine against the project's OWN embedded measured data, so a caller that
    // loaded a complete project performs no data assembly at all. Each is exactly the corresponding
    // overload above, sourced from `ExperimentBase::data` instead of an argument — same engine path,
    // same result. Fails closed with std::invalid_argument (-> Python ValueError) if a participating
    // bank carries no embedded data or is calculation-only — the residual guard for an entity
    // assembled by hand; a loaded fit-ready project cannot reach it by construction (the project's
    // own contents select calculate vs fit). The `on_start` overloads are pure delegators: they
    // source the embedded data and forward both callbacks to the provider-building overloads above,
    // which own the fire point.
    FitResultBase fit(const IterationCallback& on_iteration, const PreambleCallback& on_start = {},
                      const CancelCallback& should_cancel = {});
    FitResultBase fit_joint(const IterationCallback& on_iteration,
                            const PreambleCallback& on_start = {},
                            const CancelCallback& should_cancel = {});
    FitResultBase fit();
    FitResultBase fit_joint();

    // The sequential scan refinement — the ONE native entry point the `sequential` fitting mode
    // delegates to (the analysis facade routes exactly that mode here). The entire loop, the
    // carry-forward/resume state and the `analysis/results.csv` writer are crysta's
    // (`crysta::fit_project` on the converted project — criterion 6's one writer, literal); edi
    // converts the model across, hands over the declared `_sequential_fit.*` block and the
    // project directory, and translates the terminal result back. Fails closed with
    // std::invalid_argument (-> Python ValueError) when the fitting mode is not exactly
    // `sequential`, the project has no directory (never loaded or saved), or no scan block
    // is declared. The declared `_minimizer.*` conditions drive every inner fit, and crysta
    // records them per row in analysis/results-provenance.csv.
    // `on_start` is accepted for signature symmetry but never fired: the per-file preamble
    // belongs to the per-file fits inside crysta, and fabricating a whole-scan preamble would report numbers
    // no engine produced. The scan's own preamble is `on_scan_start`: a ScanPreamble carrying the walk total
    // and every already-committed resume ROW, fired once before the first file's fit; `on_file_complete`
    // fires once per file completed DURING this call, with the facts of its committed results.csv row. The
    // split is the seam's contract: prior rows arrive once, through the preamble, so a consumer that wants
    // scan-wide aggregates subscribes to it. `on_iteration` receives the scan-level renumbered records the
    // history collects — the FULL-verbosity diagnostic stream a surface suppresses by default — but ONLY
    // when this call delivered the ScanPreamble that anchors them: a caller subscribing on_iteration alone
    // gets what it always got (nothing), so review-1 F6's refusal of unanchored row streams still binds.
    FitResultBase fit_sequential(const IterationCallback& on_iteration = {},
                                    const PreambleCallback& on_start = {},
                                    const ScanStartCallback& on_scan_start = {},
                                    const FileCompleteCallback& on_file_complete = {},
                                    const CancelCallback& should_cancel = {});
    // The `independent` scan mode's native entry point, beside
    // `fit_sequential` — one named entry per declared scan mode, so a caller reaching for a
    // mode by name finds it instead of falling back to a single-bank refine. Same driver, same
    // refusals; the mode must be exactly `independent`.
    FitResultBase fit_independent(const IterationCallback& on_iteration = {},
                                     const PreambleCallback& on_start = {},
                                     const ScanStartCallback& on_scan_start = {},
                                     const FileCompleteCallback& on_file_complete = {},
                                     const CancelCallback& should_cancel = {});
    // The shared scan implementation both public scan entries delegate to AFTER each has
    // proved its own exact mode token. It is deliberately not bound to Python — making the
    // public entries aliases of one another is exactly what let an `independent` project
    // succeed through the explicitly sequential route.
    FitResultBase fit_scan(const IterationCallback& on_iteration = {},
                              const PreambleCallback& on_start = {},
                              const ScanStartCallback& on_scan_start = {},
                              const FileCompleteCallback& on_file_complete = {},
                              const CancelCallback& should_cancel = {});

    // PLURAL storage — a collection holding one element is honest, and the in-repo
    // `experiments` precedent now has its structures half. The singular accessors below are the
    // documented first-element shortcuts: they fail closed on an empty collection, and — unlike
    // the retired bank-0 MIRROR COPY of `experiment` — they are views, so a write through the
    // singular reaches the collection.
    ItemVec<Structure> structures;      // Shared items, deep-copied with the project
    ItemVec<BraggPdExperiment> experiments;
    std::string fitting_mode;
    // The directory this project was loaded from / last saved to:
    // `save()` writes here and fails closed when empty; load and save_as set it.
    std::string path;
    // Where a scan's `_sequential_fit.data_dir` resolves; empty = `path`. The CLI's --dry
    // points `path` at a scratch directory (what a fit writes) and this at the loaded project,
    // so scan data are read in place and never copied. Forwarded to crysta's
    // Project::scan_data_root; never persisted.
    std::string scan_data_root;
    // diffraction-lib `Project.metadata` / `Project.name`: plain data, mirrored on crysta.
    // `load_project` and the binding's `save_as` keep metadata.path in step.
    ProjectMetadata metadata;
    // The analysis block's declared `_minimizer.max_iterations`. 0 = not declared -> the
    // historical 50-iteration cap. Honored by fit()/fit_joint(); the
    int minimizer_max_iterations = 0;
    // The declared `_minimizer.chi_square_tolerance` (the LM relative chi-square stop).
    // 0 = not declared -> crysta's default. Honored by every fit path, like the bound above.
    double minimizer_chi_square_tolerance = 0.0;
    // The declared `_minimizer.type`, kept as written so a save round-trips it — an empty value
    // included (absent = not declared; a save does not add it). Only `crysta` is supported: any
    // other value warns at load and the fit runs with crysta.
    std::optional<std::string> minimizer_type;
    // The selected descent-flow registry id — MODEL STATE, like the iteration bound above,
    // never a fit-call argument (only genuine call-time options cross the fit seam, and a
    // strategy selection is a declared property of the analysis). Empty = no selection -> the
    // historical default path, byte-identical by construction. Validated fail-closed against
    // the linked crysta registry (descent_ids() below) at the surface setter, at load AND
    // before any fit work. Declared in analysis.edi as `_minimizer.descent`, loaded and saved
    // (written iff selected), and run by every fit path — single, joint and sequential.
    std::string descent;
    // The declared `_sequential_fit.*` block (see SequentialFitConfig above) — model state
    // like `fitting_mode`, consumed by fit_sequential's native delegation and round-tripped
    // by the delegated save.
    SequentialFitConfig sequential_fit;
    // The declared parameter aliases and constraints (analysis.edi `_alias`, `_constraint`).
    ItemVec<ParameterAlias> aliases;
    ItemVec<ParameterConstraint> constraints;
    // The last fit's result (`_fit_result`; see FitResultRecord).
    FitResultRecord fit_result;
    // ADR-0018: the row of this object's non-loop categories.
    detail::CategoryRow table_row;

    Structure& structure() {
        if (structures.empty()) {
            throw std::invalid_argument("edi Project: no structure (structures is empty)");
        }
        if (structures.size() > 1) {  // several phases are never read as the first one
            throw std::invalid_argument("edi Project: the project holds " + std::to_string(structures.size()) +
                                        " structures; name one through structures");
        }
        return *structures.front();
    }
    const Structure& structure() const {
        if (structures.empty()) {
            throw std::invalid_argument("edi Project: no structure (structures is empty)");
        }
        if (structures.size() > 1) {  // several phases are never read as the first one
            throw std::invalid_argument("edi Project: the project holds " + std::to_string(structures.size()) +
                                        " structures; name one through structures");
        }
        return *structures.front();
    }
    BraggPdExperiment& experiment() {
        if (experiments.empty()) {
            throw std::invalid_argument("edi Project: no experiment (experiments is empty)");
        }
        return *experiments.front();
    }
    const BraggPdExperiment& experiment() const {
        if (experiments.empty()) {
            throw std::invalid_argument("edi Project: no experiment (experiments is empty)");
        }
        return *experiments.front();
    }

    // Every structure's parameters, then every experiment's (diffraction-lib
    // `Project.parameters` / `Project.free_parameters`).
    std::vector<Parameter*> parameters();
    std::vector<Parameter*> free_parameters();

    // An admitted edit through an editor transaction. The app's one write door
    // (ProjectEditor::apply) calls it after every change it runs, so every GUI edit — any field,
    // equal value or not — stales every bank's computed categories until the recalculation the
    // editor then queues. Python writes renew the written object's own identity
    // instead (per-object precision).
    void note_edit() noexcept { edits_.renew(); }

    // A held experiment's value read reaches calculate() through its collection's link to this project
    // (ExperimentBase::ensure_computed). The links hold from construction and every assignment (edi
    // ADR-0024), so this only sets them again; it stays for the callers that ask for it.
    void adopt_experiments() noexcept { link_rows(); }

   private:
    // ADR-0020 §1: the transaction reads and compares the editor record.
    friend WorkStamps work_stamps(const Project& live);
    friend bool unchanged_since(const Project& live, const WorkStamps& stamps);
    friend PublishOutcome publish(Project& live, CalculationResult&& result);
    // calculate()'s body: converts, calculates and publishes every bank, or throws first.
    void publish_calculation();
    detail::EditLog edits_;
    // edi ADR-0024: every collection of the project, and every collection inside its structures and
    // experiments, holds the project's record. ProjectTail calls it after a build or an assignment.
    friend class detail::ProjectTail;
    void link_rows() noexcept {
        const std::shared_ptr<const detail::ProjectLink> own = link();
        for (detail::KeyedBase* collection : std::initializer_list<detail::KeyedBase*>{
                 &structures, &experiments, &aliases, &constraints}) {
            collection->host_link_ = own;
        }
        for (const auto& structure_item : structures) {
            detail::link_nested(*structure_item, own);
        }
        for (const auto& experiment_item : experiments) {
            detail::link_nested(*experiment_item, own);
        }
    }
    detail::ProjectTail tail_;  // the last member: see detail::ProjectTail
};

namespace detail {

inline void ProjectAnchor::open() {
    link_ = std::make_shared<ProjectLink>();
    link_->project = static_cast<Project*>(this);
    outer_ = project_being_built;
    project_being_built = link_->project;
}

inline ProjectAnchor::~ProjectAnchor() {
    if (project_being_built == link_->project) {  // a build that failed before its last member
        project_being_built = outer_;
    }
    link_->project = nullptr;
}

inline void ProjectTail::close() noexcept {
    owner_ = project_being_built;
    if (owner_ != nullptr) {
        project_being_built = static_cast<ProjectAnchor*>(owner_)->outer_;
        relink();
    }
}

inline void ProjectTail::relink() const noexcept {
    if (owner_ != nullptr) {
        owner_->link_rows();
    }
}

inline void link_nested(Structure& structure, const std::shared_ptr<const ProjectLink>& link) noexcept {
    static_cast<KeyedBase&>(structure.atom_sites).host_link_ = link;
}

inline void link_nested(ExperimentBase& experiment, const std::shared_ptr<const ProjectLink>& link) noexcept {
    for (KeyedBase* collection : std::initializer_list<KeyedBase*>{
             &experiment.background, &experiment.background_terms, &experiment.preferred_orientation}) {
        collection->host_link_ = link;
    }
}

}  // namespace detail

// ADR-0018: the schema of every non-loop category. Each names the category on file, the members
// that hold its columns, in column order, and the file item of each (an empty entry is a column
// no file item carries). A non-loop category is a table of one row, whose cells stand in its
// `Owner`; `OneRow<Category>` is its table view. A parameter block is a column per parameter.
// tools/checks/category_census.py reads these declarations.

// The structure datablock.
struct CellCategory {
    using Owner = Cell;
    static constexpr const char* name = "_cell";
    static constexpr auto columns = std::tuple{&Cell::length_a, &Cell::length_b, &Cell::length_c, &Cell::angle_alpha, &Cell::angle_beta, &Cell::angle_gamma};
    static constexpr std::array items{"length_a", "length_b", "length_c", "angle_alpha", "angle_beta", "angle_gamma"};
    static constexpr std::array cif{"_cell_length_a", "_cell_length_b", "_cell_length_c", "_cell_angle_alpha", "_cell_angle_beta", "_cell_angle_gamma"};
};
static_assert(detail::one_entry_per_column(CellCategory::columns, CellCategory::items));

struct SpaceGroupCategory {
    using Owner = SpaceGroup;
    static constexpr const char* name = "_space_group";
    static constexpr auto columns = std::tuple{&SpaceGroup::name_h_m, &SpaceGroup::coord_system_code, &SpaceGroup::it_number};
    static constexpr std::array items{"name_h_m", "coord_system_code", "it_number"};
    static constexpr std::array cif{"_space_group_name_H-M_alt", "_symmetry_space_group_name_H-M"};
};
static_assert(detail::one_entry_per_column(SpaceGroupCategory::columns, SpaceGroupCategory::items));

struct GeomCategory {
    using Owner = Geom;
    static constexpr const char* name = "_geom";
    static constexpr auto columns = std::tuple{&Geom::min_bond_distance_cutoff, &Geom::bond_distance_inc};
    static constexpr std::array items{"min_bond_distance_cutoff", "bond_distance_inc"};
    static constexpr std::array cif{"_geom_min_bond_distance_cutoff", "_geom_bond_distance_incr"};
};
static_assert(detail::one_entry_per_column(GeomCategory::columns, GeomCategory::items));

// The experiment datablock.
struct ExperimentTypeCategory {
    using Owner = ExperimentType;
    static constexpr const char* name = "_experiment_type";
    static constexpr auto columns = std::tuple{&ExperimentType::sample_form, &ExperimentType::beam_mode, &ExperimentType::radiation_probe, &ExperimentType::scattering_type};
    static constexpr std::array items{"sample_form", "beam_mode", "radiation_probe", "scattering_type"};
    static constexpr std::array legacy{"_easydiffraction_experiment_type", "_expt_type"};
};
static_assert(detail::one_entry_per_column(ExperimentTypeCategory::columns, ExperimentTypeCategory::items));

struct ScatteringSourceCategory {
    using Owner = ExperimentBase;
    static constexpr const char* name = "_scattering_source";
    static constexpr auto columns = std::tuple{&ExperimentBase::xray_form_factor, &ExperimentBase::xray_dispersion, &ExperimentBase::neutron_scattering_length};
    static constexpr std::array items{"xray_form_factor", "xray_dispersion", "neutron_scattering_length"};
};
static_assert(detail::one_entry_per_column(ScatteringSourceCategory::columns, ScatteringSourceCategory::items));

struct PeakCategory {
    using Owner = PeakBase;
    static constexpr const char* name = "_peak";
    static constexpr auto columns = std::tuple{&PeakBase::type, &PeakBase::cutoff_fwhm, &PeakBase::rise_alpha_0, &PeakBase::rise_alpha_1, &PeakBase::decay_beta_0, &PeakBase::decay_beta_1, &PeakBase::broad_gauss_sigma_0, &PeakBase::broad_gauss_sigma_1, &PeakBase::broad_gauss_sigma_2, &PeakBase::broad_gauss_size, &PeakBase::broad_gauss_strain, &PeakBase::broad_lorentz_gamma_0, &PeakBase::broad_lorentz_gamma_1, &PeakBase::broad_lorentz_gamma_2, &PeakBase::broad_lorentz_size, &PeakBase::broad_lorentz_strain, &PeakBase::broad_gauss_u, &PeakBase::broad_gauss_v, &PeakBase::broad_gauss_w, &PeakBase::broad_lorentz_x, &PeakBase::broad_lorentz_y, &PeakBase::asym_fcj_1, &PeakBase::asym_fcj_2, &PeakBase::asym_beba_a0, &PeakBase::asym_beba_b0, &PeakBase::asym_beba_a1, &PeakBase::asym_beba_b1, &PeakBase::asym_beba_limit};
    static constexpr std::array items{"type", "cutoff_fwhm", "rise_alpha_0", "rise_alpha_1", "decay_beta_0", "decay_beta_1", "broad_gauss_sigma_0", "broad_gauss_sigma_1", "broad_gauss_sigma_2", "broad_gauss_size", "broad_gauss_strain", "broad_lorentz_gamma_0", "broad_lorentz_gamma_1", "broad_lorentz_gamma_2", "broad_lorentz_size", "broad_lorentz_strain", "broad_gauss_u", "broad_gauss_v", "broad_gauss_w", "broad_lorentz_x", "broad_lorentz_y", "asym_fcj_1", "asym_fcj_2", "asym_beba_a0", "asym_beba_b0", "asym_beba_a1", "asym_beba_b1", "asym_beba_limit"};
    static constexpr std::array legacy{"_easydiffraction_peak"};
};
static_assert(detail::one_entry_per_column(PeakCategory::columns, PeakCategory::items));

struct InstrumentCategory {
    using Owner = InstrumentBase;
    static constexpr const char* name = "_instrument";
    static constexpr auto columns = std::tuple{&InstrumentBase::calib_d_to_tof_offset, &InstrumentBase::calib_d_to_tof_linear, &InstrumentBase::calib_d_to_tof_quadratic, &InstrumentBase::calib_d_to_tof_reciprocal, &InstrumentBase::setup_twotheta_bank, &InstrumentBase::setup_wavelength, &InstrumentBase::calib_twotheta_offset, &InstrumentBase::calib_sample_displacement, &InstrumentBase::calib_sample_transparency, &InstrumentBase::setup_polarization_coefficient, &InstrumentBase::setup_monochromator_twotheta};
    static constexpr std::array items{"calib_d_to_tof_offset", "calib_d_to_tof_linear", "calib_d_to_tof_quadratic", "calib_d_to_tof_reciprocal", "setup_twotheta_bank", "setup_wavelength", "calib_twotheta_offset", "calib_sample_displacement", "calib_sample_transparency", "setup_polarization_coefficient", "setup_monochromator_twotheta"};
    static constexpr std::array legacy{"_instr", "_diffrn_radiation_wavelength", "_pd_calib"};
};
static_assert(detail::one_entry_per_column(InstrumentCategory::columns, InstrumentCategory::items));

struct AbsorptionCategory {
    using Owner = AbsorptionBase;
    static constexpr const char* name = "_absorption";
    static constexpr auto columns = std::tuple{&AbsorptionBase::type, &AbsorptionBase::abscor1, &AbsorptionBase::abscor2, &AbsorptionBase::mu_r};
    static constexpr std::array items{"type", "abscor1", "abscor2", "mu_r"};
    static constexpr std::array legacy{"_easydiffraction_absorption"};
};
static_assert(detail::one_entry_per_column(AbsorptionCategory::columns, AbsorptionCategory::items));

// The selector and constants of the type-switched `_background` category. Its rows are the loop
// schema of the selected type.
struct BackgroundCategory {
    using Owner = ExperimentBase;
    static constexpr const char* name = "_background";
    static constexpr auto columns = std::tuple{&ExperimentBase::background_type, &ExperimentBase::background_origin, &ExperimentBase::background_x_min, &ExperimentBase::background_x_max};
    static constexpr std::array items{"type", "origin", "x_min", "x_max"};
};
static_assert(detail::one_entry_per_column(BackgroundCategory::columns, BackgroundCategory::items));

struct JointFitCategory {
    using Owner = ExperimentBase;
    static constexpr const char* name = "_joint_fit";
    static constexpr auto columns = std::tuple{&ExperimentBase::dataset_weight};
    static constexpr std::array items{"weight"};
};
static_assert(detail::one_entry_per_column(JointFitCategory::columns, JointFitCategory::items));

// How the pattern's axis was declared. The category's file items, `<axis>_min`, `_max` and
// `_step`, generate the axis column of `_data` at load and are not stored.
struct DataRangeCategory {
    using Owner = ExperimentBase;
    static constexpr const char* name = "_data_range";
    static constexpr auto columns = std::tuple{&ExperimentBase::calculation_only};
    static constexpr std::array items{""};
    static constexpr std::array legacy{"_pd_meas"};
};
static_assert(detail::one_entry_per_column(DataRangeCategory::columns, DataRangeCategory::items));

// The project.
struct FittingModeCategory {
    using Owner = Project;
    static constexpr const char* name = "_fitting_mode";
    static constexpr auto columns = std::tuple{&Project::fitting_mode};
    static constexpr std::array items{"type"};
};
static_assert(detail::one_entry_per_column(FittingModeCategory::columns, FittingModeCategory::items));

struct MinimizerCategory {
    using Owner = Project;
    static constexpr const char* name = "_minimizer";
    static constexpr auto columns = std::tuple{&Project::minimizer_type, &Project::minimizer_max_iterations, &Project::descent, &Project::minimizer_chi_square_tolerance};
    static constexpr std::array items{"type", "max_iterations", "descent", "chi_square_tolerance"};
};
static_assert(detail::one_entry_per_column(MinimizerCategory::columns, MinimizerCategory::items));

// The last fit's result (diffraction-lib's `_fit_result`) and each bank's share of a joint fit, one row per
// experiment like `_joint_fit` (crysta's FitResultCategory and FitResultBankCategory).
struct FitResultCategory {
    using Owner = FitResultRecord;
    static constexpr const char* name = "_fit_result";
    static constexpr auto columns = std::tuple{
        &FitResultRecord::result_kind, &FitResultRecord::success, &FitResultRecord::message,
        &FitResultRecord::iterations, &FitResultRecord::fitting_time, &FitResultRecord::reduced_chi_square,
        &FitResultRecord::objective_name, &FitResultRecord::objective_value, &FitResultRecord::n_data_points,
        &FitResultRecord::n_parameters, &FitResultRecord::n_free_parameters, &FitResultRecord::degrees_of_freedom,
        &FitResultRecord::covariance_available, &FitResultRecord::exit_reason, &FitResultRecord::prof_wr_factor,
        &FitResultRecord::profile_function, &FitResultRecord::background_function, &FitResultRecord::descent};
    static constexpr std::array items{"result_kind", "success", "message", "iterations", "fitting_time",
                                      "reduced_chi_square", "objective_name", "objective_value", "n_data_points",
                                      "n_parameters", "n_free_parameters", "degrees_of_freedom",
                                      "covariance_available", "exit_reason", "prof_wr_factor", "profile_function",
                                      "background_function", "descent"};
};
static_assert(detail::one_entry_per_column(FitResultCategory::columns, FitResultCategory::items));

struct FitResultBankCategory {
    using Owner = ExperimentBase;
    static constexpr const char* name = "_fit_result_bank";
    static constexpr auto columns = std::tuple{&ExperimentBase::fit_n_data_points, &ExperimentBase::fit_prof_wr_factor,
                                               &ExperimentBase::fit_chi_square};
    static constexpr std::array items{"n_data_points", "prof_wr_factor", "chi_square"};
};
static_assert(detail::one_entry_per_column(FitResultBankCategory::columns, FitResultBankCategory::items));

struct SequentialFitCategory {
    using Owner = SequentialFitConfig;
    static constexpr const char* name = "_sequential_fit";
    static constexpr auto columns = std::tuple{&SequentialFitConfig::data_dir, &SequentialFitConfig::file_pattern,
                                               &SequentialFitConfig::reverse, &SequentialFitConfig::template_file};
    static constexpr std::array items{"data_dir", "file_pattern", "reverse", "template_file"};
};
static_assert(detail::one_entry_per_column(SequentialFitCategory::columns, SequentialFitCategory::items));

struct MetadataCategory {
    using Owner = ProjectMetadata;
    static constexpr const char* name = "_metadata";
    static constexpr auto columns = std::tuple{&ProjectMetadata::name, &ProjectMetadata::title, &ProjectMetadata::description, &ProjectMetadata::path, &ProjectMetadata::created, &ProjectMetadata::last_modified, &ProjectMetadata::timestamp};
    static constexpr std::array items{"name", "title", "description", "path", "created", "last_modified", "timestamp"};
};
static_assert(detail::one_entry_per_column(MetadataCategory::columns, MetadataCategory::items));

// Engine bookkeeping, never on file.
struct ProjectStateCategory {
    using Owner = Project;
    static constexpr const char* name = "project";
    static constexpr auto columns = std::tuple{&Project::path, &Project::scan_data_root};
    static constexpr std::array items{"", ""};
};
static_assert(detail::one_entry_per_column(ProjectStateCategory::columns, ProjectStateCategory::items));

// The loop categories that one cell holds: a table behind the cell, written whole.
struct ScatteringLengthCategory {
    static constexpr const char* name = "_scattering_length";
    static constexpr auto columns = std::tuple{&Structure::scattering_lengths_fm};
    static constexpr std::array items{"type_symbol length_fm"};
};
static_assert(detail::one_entry_per_column(ScatteringLengthCategory::columns, ScatteringLengthCategory::items));

struct ExcludedRegionCategory {
    static constexpr const char* name = "_excluded_region";
    static constexpr auto columns = std::tuple{&ExperimentBase::excluded_regions};
    static constexpr std::array items{"start end"};
    static constexpr std::array legacy{"_easydiffraction_excluded_region"};
};
static_assert(detail::one_entry_per_column(ExcludedRegionCategory::columns, ExcludedRegionCategory::items));

// An imported file's own `_refln` loop, kept as read: the item names, and each row's cells as
// written. It is written back until a calculation publishes the computed `_refln` (ReflnCategory).
struct CarriedReflnCategory {
    static constexpr const char* name = "carried_refln";
    static constexpr auto columns = std::tuple{&CarriedLoop::columns, &CarriedLoop::rows};
    static constexpr std::array items{"", "*"};
};
static_assert(detail::one_entry_per_column(CarriedReflnCategory::columns, CarriedReflnCategory::items));

// The measured and the computed columns of the optional data node. The measured columns are the node's own;
// the computed ones are crysta's published buffers, shared. The residual is crysta's too: derived, and never
// saved.
struct DataCategory {
    static constexpr const char* name = "_data";
    static constexpr auto columns = std::tuple{&PdDataBase::two_theta, &PdDataBase::time_of_flight, &PdDataBase::intensity_meas, &PdDataBase::intensity_meas_su, &PdDataBase::d_spacing, &PdDataBase::intensity_calc, &PdDataBase::intensity_bkg, &PdDataBase::calc_status, &PdDataBase::residual};
    static constexpr std::array items{"two_theta", "time_of_flight", "intensity_meas", "intensity_meas_su", "d_spacing", "intensity_calc", "intensity_bkg", "calc_status", "residual"};
    static constexpr std::array legacy{"_pd_data", "_pd_meas", "_pd_proc"};
};
static_assert(detail::one_entry_per_column(DataCategory::columns, DataCategory::items));

// Categories on file that the model does not store.
struct FitParameterCategory {
    static constexpr const char* name = "_fit_parameter";
    static constexpr const char* derived =
        "composed at save from the parameters' fit-start cells; read back into them at load";
};
struct AtomSiteAnisoCategory {
    static constexpr const char* name = "_atom_site_aniso";
    static constexpr const char* derived =
        "read by the CIF import, which reduces it to each site's isotropic ADP; never stored";
    static constexpr std::array cif{"_atom_site_aniso_label", "_atom_site_aniso_U_11", "_atom_site_aniso_U_22", "_atom_site_aniso_U_33"};
};
struct EdiCategory {
    static constexpr const char* name = "_edi";
    static constexpr const char* derived =
        "the file's schema version: the writer's constant, checked by the loader";
};
// Two engine choices a file may declare and edi does not make. The loader warns on a value it does
// not use and keeps none.
struct CalculatorCategory {
    static constexpr const char* name = "_calculator";
    static constexpr const char* derived =
        "the calculator a file declares: crysta is the only one, so the loader checks it and keeps nothing";
};
struct RenderingPlotCategory {
    static constexpr const char* name = "_rendering_plot";
    static constexpr const char* derived =
        "the plot renderer a file declares: each host draws with its own, so the loader checks it and keeps nothing";
};

// The computed categories: columns crysta published, shared and read-only here, with ordinal ids.
struct SpaceGroupSymopCategory {
    static constexpr const char* name = "_space_group_symop";
    static constexpr auto columns = std::tuple{&SpaceGroupSymop::operation_xyz};
    static constexpr std::array items{"operation_xyz"};
};
static_assert(detail::one_entry_per_column(SpaceGroupSymopCategory::columns, SpaceGroupSymopCategory::items));

struct ExpandedAtomSiteCategory {
    static constexpr const char* name = "_expanded_atom_site";
    static constexpr auto columns = std::tuple{&ExpandedAtomSites::atom_site_id, &ExpandedAtomSites::site_symmetry, &ExpandedAtomSites::fract_x, &ExpandedAtomSites::fract_y, &ExpandedAtomSites::fract_z, &ExpandedAtomSites::cartn_x, &ExpandedAtomSites::cartn_y, &ExpandedAtomSites::cartn_z, &ExpandedAtomSites::occupancy, &ExpandedAtomSites::u_iso, &ExpandedAtomSites::cluster_id};
    static constexpr std::array items{"atom_site_id", "site_symmetry", "fract_x", "fract_y", "fract_z", "cartn_x", "cartn_y", "cartn_z", "occupancy", "u_iso", "cluster_id"};
};
static_assert(detail::one_entry_per_column(ExpandedAtomSiteCategory::columns, ExpandedAtomSiteCategory::items));

struct GeomBondCategory {
    static constexpr const char* name = "_geom_bond";
    static constexpr auto columns = std::tuple{&GeomBonds::expanded_atom_site_id_1, &GeomBonds::expanded_atom_site_id_2, &GeomBonds::atom_site_label_1, &GeomBonds::atom_site_label_2, &GeomBonds::site_symmetry_1, &GeomBonds::site_symmetry_2, &GeomBonds::distance};
    static constexpr std::array items{"expanded_atom_site_id_1", "expanded_atom_site_id_2", "atom_site_label_1", "atom_site_label_2", "site_symmetry_1", "site_symmetry_2", "distance"};
};
static_assert(detail::one_entry_per_column(GeomBondCategory::columns, GeomBondCategory::items));

// A computed value of one row, published whole with the structure's geometry.
struct CartnTransformCategory {
    static constexpr const char* name = "_atom_sites_cartn_transform";
    static constexpr auto columns = std::tuple{&CartnTransform::matrix, &CartnTransform::axes};
    static constexpr std::array items{"mat_11 mat_12 mat_13 mat_21 mat_22 mat_23 mat_31 mat_32 mat_33", "axes"};
};
static_assert(detail::one_entry_per_column(CartnTransformCategory::columns, CartnTransformCategory::items));

struct ReflnCategory {
    static constexpr const char* name = "_refln";
    static constexpr auto columns = std::tuple{&PowderReflnDataBase::structure_id, &PowderReflnDataBase::d_spacing, &PowderReflnDataBase::sin_theta_over_lambda, &PowderReflnDataBase::index_h, &PowderReflnDataBase::index_k, &PowderReflnDataBase::index_l, &PowderReflnDataBase::f_calc, &PowderReflnDataBase::f_squared_calc, &PowderReflnDataBase::position};
    static constexpr std::array items{"structure_id", "d_spacing", "sin_theta_over_lambda", "index_h", "index_k", "index_l", "f_calc", "f_squared_calc", "two_theta time_of_flight"};
};
static_assert(detail::one_entry_per_column(ReflnCategory::columns, ReflnCategory::items));

// Spec attachment. Inline so the hidden C++ probes' fixed TU lists link without a new
// source file; the spec storage itself lives in parameter_spec.cpp.
inline Cell::Cell() {
    length_a.spec = &spec::cell_length_a;
    length_b.spec = &spec::cell_length_b;
    length_c.spec = &spec::cell_length_c;
    angle_alpha.spec = &spec::cell_angle_alpha;
    angle_beta.spec = &spec::cell_angle_beta;
    angle_gamma.spec = &spec::cell_angle_gamma;
}

inline AtomSite::AtomSite() {
    fract_x.spec = &spec::atom_site_fract_x;
    fract_y.spec = &spec::atom_site_fract_y;
    fract_z.spec = &spec::atom_site_fract_z;
    occupancy.spec = &spec::atom_site_occupancy;
    adp_iso.spec = &spec::atom_site_adp_iso;
}

inline PeakBase::PeakBase() {
    rise_alpha_0.spec = &spec::peak_rise_alpha_0;
    rise_alpha_1.spec = &spec::peak_rise_alpha_1;
    decay_beta_0.spec = &spec::peak_decay_beta_0;
    decay_beta_1.spec = &spec::peak_decay_beta_1;
    broad_gauss_sigma_0.spec = &spec::peak_broad_gauss_sigma_0;
    broad_gauss_sigma_1.spec = &spec::peak_broad_gauss_sigma_1;
    broad_gauss_sigma_2.spec = &spec::peak_broad_gauss_sigma_2;
    broad_gauss_size.spec = &spec::peak_broad_gauss_size;
    broad_gauss_strain.spec = &spec::peak_broad_gauss_strain;
    broad_lorentz_gamma_0.spec = &spec::peak_broad_lorentz_gamma_0;
    broad_lorentz_gamma_1.spec = &spec::peak_broad_lorentz_gamma_1;
    broad_lorentz_gamma_2.spec = &spec::peak_broad_lorentz_gamma_2;
    broad_lorentz_size.spec = &spec::peak_broad_lorentz_size;
    broad_lorentz_strain.spec = &spec::peak_broad_lorentz_strain;
}

inline InstrumentBase::InstrumentBase() {
    calib_d_to_tof_offset.spec = &spec::instrument_d_to_tof_offset;
    calib_d_to_tof_linear.spec = &spec::instrument_d_to_tof_linear;
    calib_d_to_tof_quadratic.spec = &spec::instrument_d_to_tof_quadratic;
    calib_d_to_tof_reciprocal.spec = &spec::instrument_d_to_tof_reciprocal;
    setup_twotheta_bank.spec = &spec::instrument_twotheta_bank;
}

// The parameter walks. Inline for the same TU-list reason as the spec attachments.
namespace detail {
inline std::vector<Parameter*> free_of(std::vector<Parameter*> all) {
    std::vector<Parameter*> free;
    for (Parameter* parameter : all) {
        if (parameter->free) {
            free.push_back(parameter);
        }
    }
    return free;
}
inline void push_optional(std::vector<Parameter*>& out, std::optional<Parameter>& field) {
    if (field) {
        out.push_back(&*field);
    }
}
}  // namespace detail

inline std::vector<Parameter*> Cell::free_parameters() { return detail::free_of(parameters()); }
inline std::vector<Parameter*> AtomSite::free_parameters() { return detail::free_of(parameters()); }
inline std::vector<Parameter*> LineSegment::free_parameters() {
    return detail::free_of(parameters());
}
inline std::vector<Parameter*> PolynomialTerm::free_parameters() {
    return detail::free_of(parameters());
}
inline std::vector<Parameter*> Structure::parameters() {
    std::vector<Parameter*> out = cell.parameters();
    for (const std::shared_ptr<AtomSite>& site : atom_sites) {
        for (Parameter* parameter : site->parameters()) {
            out.push_back(parameter);
        }
    }
    return out;
}
inline std::vector<Parameter*> Structure::free_parameters() { return detail::free_of(parameters()); }
inline std::vector<Parameter*> PeakBase::parameters() {
    std::vector<Parameter*> out = {
        &rise_alpha_0,          &rise_alpha_1,          &decay_beta_0,       &decay_beta_1,
        &broad_gauss_sigma_0,   &broad_gauss_sigma_1,   &broad_gauss_sigma_2, &broad_gauss_size,
        &broad_gauss_strain,    &broad_lorentz_gamma_0, &broad_lorentz_gamma_1,
        &broad_lorentz_gamma_2, &broad_lorentz_size,    &broad_lorentz_strain};
    detail::push_optional(out, broad_gauss_u);
    detail::push_optional(out, broad_gauss_v);
    detail::push_optional(out, broad_gauss_w);
    detail::push_optional(out, broad_lorentz_x);
    detail::push_optional(out, broad_lorentz_y);
    detail::push_optional(out, asym_fcj_1);
    detail::push_optional(out, asym_fcj_2);
    detail::push_optional(out, asym_beba_a0);
    detail::push_optional(out, asym_beba_b0);
    detail::push_optional(out, asym_beba_a1);
    detail::push_optional(out, asym_beba_b1);
    detail::push_optional(out, asym_beba_limit);
    return out;
}
inline std::vector<Parameter*> InstrumentBase::parameters() {
    std::vector<Parameter*> out = {&calib_d_to_tof_offset, &calib_d_to_tof_linear,
                                   &calib_d_to_tof_quadratic, &calib_d_to_tof_reciprocal,
                                   &setup_twotheta_bank};
    detail::push_optional(out, setup_wavelength);
    detail::push_optional(out, calib_twotheta_offset);
    detail::push_optional(out, calib_sample_displacement);
    detail::push_optional(out, calib_sample_transparency);
    detail::push_optional(out, setup_polarization_coefficient);  // , X-ray only
    detail::push_optional(out, setup_monochromator_twotheta);
    return out;
}
inline std::vector<Parameter*> AbsorptionBase::parameters() {
    std::vector<Parameter*> out;
    detail::push_optional(out, abscor1);
    detail::push_optional(out, abscor2);
    detail::push_optional(out, mu_r);  // The CW body; never present beside the TOF pair
    return out;
}
// The blocks in category order (peak, instrument, linked_structure, absorption), then the
// background points — the same elements in the same order as before the blocks carried their own.
inline std::vector<Parameter*> ExperimentBase::parameters() {
    std::vector<Parameter*> out = peak.parameters();
    for (Parameter* parameter : instrument.parameters()) {
        out.push_back(parameter);
    }
    for (const std::shared_ptr<LinkedStructure>& link : linked_structures) {
        out.push_back(&link->scale);
    }
    for (Parameter* parameter : absorption.parameters()) {
        out.push_back(parameter);
    }
    for (const std::shared_ptr<PrefOrient>& row : preferred_orientation) {
        for (Parameter* parameter : row->parameters()) {
            out.push_back(parameter);
        }
    }
    for (const std::shared_ptr<LineSegment>& point : background) {
        out.push_back(&point->intensity);
    }
    for (const std::shared_ptr<PolynomialTerm>& term : background_terms) {
        out.push_back(&term->coef);
    }
    return out;
}
inline LinkedStructure& ExperimentBase::linked_structure() {
    if (linked_structures.empty()) {
        throw std::out_of_range("experiment '" + name.value() + "' links no structure");
    }
    if (linked_structures.size() > 1) {
        throw std::invalid_argument("experiment '" + name.value() + "' links " +
                                    std::to_string(linked_structures.size()) +
                                    " structures; name one through linked_structures");
    }
    return *linked_structures.front();
}
inline const LinkedStructure& ExperimentBase::linked_structure() const {
    if (linked_structures.empty()) {
        throw std::out_of_range("experiment '" + name.value() + "' links no structure");
    }
    if (linked_structures.size() > 1) {
        throw std::invalid_argument("experiment '" + name.value() + "' links " +
                                    std::to_string(linked_structures.size()) +
                                    " structures; name one through linked_structures");
    }
    return *linked_structures.front();
}
inline std::vector<Parameter*> ExperimentBase::free_parameters() {
    return detail::free_of(parameters());
}
inline std::vector<Parameter*> Project::parameters() {
    std::vector<Parameter*> out;
    for (const std::shared_ptr<Structure>& structure : structures) {
        for (Parameter* parameter : structure->parameters()) {
            out.push_back(parameter);
        }
    }
    for (const std::shared_ptr<BraggPdExperiment>& experiment : experiments) {
        for (Parameter* parameter : experiment->parameters()) {
            out.push_back(parameter);
        }
    }
    return out;
}
// The free parameters a fit refines: what no enabled phase reads is left out — a disabled link's
// scale and texture, and every parameter of a structure no enabled link names (crysta's rule).
inline std::vector<Parameter*> Project::free_parameters() {
    std::vector<const Parameter*> idle;
    std::vector<std::string> used;
    for (const std::shared_ptr<BraggPdExperiment>& experiment : experiments) {
        for (const std::shared_ptr<LinkedStructure>& link : experiment->linked_structures) {
            const std::string key = datablock_key(link->structure_id, "structure");
            if (link->enabled.get()) {
                used.push_back(structures.size() == 1 && experiment->linked_structures.size() == 1
                                   ? datablock_key(structures.front()->name, "structure")
                                   : key);
                continue;
            }
            idle.push_back(&link->scale);
            for (const std::shared_ptr<PrefOrient>& row : experiment->preferred_orientation) {
                if (datablock_key(row->structure_id, "structure") == key) {
                    idle.push_back(&row->march_r);
                    idle.push_back(&row->march_random_fract);
                }
            }
        }
    }
    if (!experiments.empty()) {
        for (const std::shared_ptr<Structure>& structure : structures) {
            if (std::find(used.begin(), used.end(), datablock_key(structure->name, "structure")) == used.end()) {
                for (Parameter* parameter : structure->parameters()) {
                    idle.push_back(parameter);
                }
            }
        }
    }
    std::vector<Parameter*> out;
    for (Parameter* parameter : detail::free_of(parameters())) {
        if (std::find(idle.begin(), idle.end(), parameter) == idle.end()) {
            out.push_back(parameter);
        }
    }
    return out;
}

// Point every parameter a node holds at its category's row link, so its Python handle answers
// `is_attached` and refuses writes once the row is removed. Each Python path that hands out a
// parameter calls this, or points the one it returns, first: a parameter engaged after its row was
// linked (a presence-created optional) is then covered too.
namespace detail {
template <typename Category>
inline void point_at_row(Category& category) {
    for (Parameter* parameter : category.parameters()) {
        parameter->category.point_at(category.row);
    }
}
inline void point_parameters(Cell& cell) { point_at_row(cell); }
inline void point_parameters(AtomSite& site) { point_at_row(site); }
inline void point_parameters(LineSegment& point) { point_at_row(point); }
inline void point_parameters(PolynomialTerm& term) { point_at_row(term); }
inline void point_parameters(PrefOrient& row) { point_at_row(row); }
inline void point_parameters(LinkedStructure& link) { point_at_row(link); }
inline void point_parameters(PeakBase& peak) { point_at_row(peak); }
inline void point_parameters(InstrumentBase& instrument) { point_at_row(instrument); }
inline void point_parameters(AbsorptionBase& absorption) { point_at_row(absorption); }
inline void point_parameters(Structure& structure) {
    point_parameters(structure.cell);
    for (const std::shared_ptr<AtomSite>& site : structure.atom_sites) {
        point_parameters(*site);
    }
}
inline void point_parameters(ExperimentBase& experiment) {
    point_parameters(experiment.peak);
    point_parameters(experiment.instrument);
    for (const std::shared_ptr<LinkedStructure>& link : experiment.linked_structures) {
        point_parameters(*link);
    }
    point_parameters(experiment.absorption);
    for (const std::shared_ptr<PrefOrient>& row : experiment.preferred_orientation) {
        point_parameters(*row);
    }
    for (const std::shared_ptr<LineSegment>& point : experiment.background) {
        point_parameters(*point);
    }
    for (const std::shared_ptr<PolynomialTerm>& term : experiment.background_terms) {
        point_parameters(*term);
    }
}
inline void point_parameters(Project& project) {
    for (const std::shared_ptr<Structure>& structure : project.structures) {
        point_parameters(*structure);
    }
    for (const std::shared_ptr<BraggPdExperiment>& experiment : project.experiments) {
        point_parameters(*experiment);
    }
}
}  // namespace detail

// Presence-created parameters (the CW scalars, the absorption pair) attach their spec at their
// creation boundary: io.cpp's require_spec_parameter/find_spec_parameter on `.edi` load, and
// the bindings' def_optional_parameter_field setter on Python assignment. An engaged optional
// is therefore never spec-less.

}  // namespace edi

#endif  // EDI_MODEL_HPP
