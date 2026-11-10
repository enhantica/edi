// SPDX-License-Identifier: BSD-3-Clause
#include "edi/validation.hpp"

#include <utility>

namespace edi {

namespace {

std::string first_message(const std::vector<Diagnostic>& diagnostics) {
    for (const Diagnostic& diagnostic : diagnostics) {
        if (diagnostic.severity == Severity::Error) {
            return diagnostic.path.empty() ? diagnostic.message
                                           : diagnostic.path + ": " + diagnostic.message;
        }
    }
    return diagnostics.empty() ? std::string("validation failed") : diagnostics.front().message;
}

Diagnostic one(const std::string& tier, const std::string& where, const std::string& kind,
               const std::string& message) {
    Diagnostic diagnostic;
    diagnostic.code = "edi." + tier + "." + kind;
    diagnostic.severity = Severity::Error;
    diagnostic.path = where;
    diagnostic.message = message;
    return diagnostic;
}

}  // namespace

const char* severity_name(Severity severity) {
    switch (severity) {
        case Severity::Error:
            return "error";
        case Severity::Warning:
            return "warning";
        case Severity::Info:
            return "info";
    }
    return "error";
}

ValidationError::ValidationError(std::vector<Diagnostic> diagnostics)
    : IoError(first_message(diagnostics)), diagnostics_(std::move(diagnostics)) {}

void fail_syntax(const std::string& where, const std::string& kind, const std::string& message) {
    throw SyntaxValidationError({one("syntax", where, kind, message)});
}

void fail_schema(const std::string& where, const std::string& kind, const std::string& message) {
    throw SchemaValidationError({one("schema", where, kind, message)});
}

void fail_domain(const std::string& where, const std::string& kind, const std::string& message) {
    throw DomainValidationError({one("domain", where, kind, message)});
}

}  // namespace edi
