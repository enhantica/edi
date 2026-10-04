// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_VALIDATION_HPP
#define EDI_VALIDATION_HPP

#include <cstdint>
#include <map>
#include <string>
#include <vector>

#include "edi/io.hpp"

// edi's validation taxonomy: a structured load-time failure is a `ValidationError` carrying the
// diagnostics that describe it, and its concrete class names the TIER the loader failed at —
// `SyntaxValidationError` (the STAR/CIF text itself: unterminated fields, stray tokens, a missing
// `data_` block), `SchemaValidationError` (the `.edi` schema: an unknown or missing tag, a loop
// column, an unreadable number, the schema version) or `DomainValidationError` (a cross-field invariant:
// the peak-type / beam-mode matrix, a family's tag registry, a value outside its declared range, an
// ambiguous measured axis). The classes are edi's own core types (ADR-0003 pt 5: no engine type crosses
// the public surface) and refine `IoError`, so every existing `catch (const IoError&)` keeps catching
// them; `IoError` itself stays what it was — a file or directory that cannot be read, or a
// complete-project postcondition. The diagnostic CODES are edi's (`edi.<tier>.<kind>`) until the engine's
// validator is reachable through the fetched crysta main; the class means the same thing on both products
// — a tiered validation failure with diagnostics.

namespace edi {

enum class Severity : std::uint8_t { Error, Warning, Info };

const char* severity_name(Severity severity);

// One structured finding: a stable code, its severity, the path (file / block) it was found at, the
// human message, optional parameters and the source that produced it.
struct Diagnostic {
    std::string code;
    Severity severity = Severity::Error;
    std::string path;
    std::string message;
    std::map<std::string, std::string> params;
    std::string source = "edi_core";
};

class ValidationError : public IoError {
   public:
    explicit ValidationError(std::vector<Diagnostic> diagnostics);
    const std::vector<Diagnostic>& diagnostics() const noexcept { return diagnostics_; }
    // 1 syntax, 2 schema, 3 domain; 0 for the base class.
    virtual int tier() const noexcept { return 0; }

   private:
    std::vector<Diagnostic> diagnostics_;
};

class SyntaxValidationError : public ValidationError {
   public:
    using ValidationError::ValidationError;
    int tier() const noexcept override { return 1; }
};

class SchemaValidationError : public ValidationError {
   public:
    using ValidationError::ValidationError;
    int tier() const noexcept override { return 2; }
};

class DomainValidationError : public ValidationError {
   public:
    using ValidationError::ValidationError;
    int tier() const noexcept override { return 3; }
};

// Raise one error-severity diagnostic of the given tier. `where` is the diagnostic's path (the file
// and block the loader was reading), `kind` the code leaf (`edi.<tier>.<kind>`).
[[noreturn]] void fail_syntax(const std::string& where, const std::string& kind,
                              const std::string& message);
[[noreturn]] void fail_schema(const std::string& where, const std::string& kind,
                              const std::string& message);
[[noreturn]] void fail_domain(const std::string& where, const std::string& kind,
                              const std::string& message);

}  // namespace edi

#endif  // EDI_VALIDATION_HPP
