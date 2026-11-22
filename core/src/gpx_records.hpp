// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <bit>
#include <charconv>
#include <cstdint>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <variant>
#include <vector>

namespace edi::gpx {
using Id = std::size_t;
using Sequence = std::vector<Id>;
struct Dictionary {
    Sequence pairs;
};
struct Bytes {
    std::string value;
};
struct Dtype {
    char kind = 0;
    std::size_t width = 0;
    char endian = '<';
};
struct Array {
    Dtype dtype{};
    std::vector<std::size_t> shape;
    Id storage{};
    bool fortran_order = false;
    bool masked_layout = false;
    std::optional<Id> mask;
};
enum class Factory {
    Array,
    Reconstruct,
    MaskedArray,
    MaskedReconstruct,
    Dtype,
    Scalar,
    Encode,
    Variable,
    Expression,
    LegacyObject,
    LegacyReconstruct
};
struct ObjectState {
    Factory type = Factory::Array;
    std::optional<Id> state;
};
using Value = std::variant<std::monostate, bool, std::int64_t, double, std::string, Sequence,
                           Dictionary, Bytes, Dtype, Array, Factory, ObjectState>;

[[noreturn]] inline void refuse(const std::string& message) { throw std::runtime_error(message); }

inline void require(bool condition, const std::string& message) {
    if (!condition) refuse(message);
}

// This reader interprets a bounded data grammar. Factory tokens are names for
// the explicit storage layouts below. They never resolve or invoke callables.
class Records {
   public:
    explicit Records(std::string_view input) : input_(input) {}

    Sequence read();
    const Sequence& sequence(Id id) const { return as<Sequence>(id, "sequence"); }
    const Dictionary& dictionary(Id id) const { return as<Dictionary>(id, "dictionary"); }
    const std::string& text(Id id) const;
    const Value& value(Id id) const { return nodes_.at(id); }
    bool none(Id id) const { return std::holds_alternative<std::monostate>(value(id)); }
    bool truth(Id id) const;
    double number(Id id) const;
    const Array& array(Id id) const { return as<Array>(id, "NumPy array"); }
    double element(const Array& array, std::size_t index) const;
    bool masked(const Array& array, std::size_t index) const;
    Id field(Id id, std::string_view key) const;
    std::optional<Id> find(Id id, std::string_view key) const;

   private:
    static constexpr Id marker = std::numeric_limits<Id>::max();
    static constexpr std::size_t max_items = 300'000;
    std::string_view input_;
    std::size_t offset_{};
    std::size_t decoded_bytes_{};
    std::vector<Value> nodes_;
    Sequence stack_;
    std::unordered_map<std::uint32_t, Id> memo_;

    template <class T>
    const T& as(Id id, const char* expected) const {
        if (const auto* parsed = std::get_if<T>(&value(id))) return *parsed;
        refuse(std::string("expected ") + expected + " in GPX");
    }

    const std::string* string_value(Id id) const;
    std::string_view take(std::size_t count);
    std::string_view line();
    std::uint8_t byte() { return static_cast<std::uint8_t>(take(1)[0]); }
    std::uint32_t little(std::size_t width);
    Id pop();
    Id top() const;
    Sequence marked();
    void push(Id id);
    void add(Value value);
    void extend(Sequence items, bool dictionary);
    void set_memo(std::uint32_t slot);
    void get_memo(std::uint32_t slot);
    void read_global();
    void reduce();
    void build();
    void new_object();
};
}  // namespace edi::gpx
