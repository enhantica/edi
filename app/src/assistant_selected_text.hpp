// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "edi/assistant_files.hpp"
#include "edi/assistant_limits.hpp"
#include <QJsonObject>
#include <QStringView>
#include <QAnyStringView>
#include <type_traits>
#include "../../core/src/assistant_json.hpp"
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace edi_app {
// Exact existing input UTF-8 sizing, shared with the selected-text projection.
inline quint64 input_utf8_bytes(QStringView text) {
    quint64 bytes=0;
    for(qsizetype at=0;at<text.size();++at) {
        const auto c=text[at];char32_t value=c.unicode();
        if(c.isHighSurrogate()) {
            if(at+1>=text.size() || !text[at+1].isLowSurrogate())throw std::invalid_argument("Input path has invalid Unicode");
            value=QChar::surrogateToUcs4(c,text[++at]);
        } else if(c.isLowSurrogate())throw std::invalid_argument("Input path has invalid Unicode");
        bytes+=value<0x80?1:value<0x800?2:value<0x10000?3:4;
    }
    return bytes;
}
// A borrowed Qt JSON string may be UTF-16, UTF-8 or Latin-1. Inspect its
// actual view without QJsonValue::toString's independent decoded allocation.
inline quint64 selected_text_utf8_bytes(QAnyStringView text) {
    return text.visit([](auto view)->quint64 {
        using View=decltype(view);
        if constexpr (std::is_same_v<View,QStringView>) {
            if(view.contains(QChar(0)))throw std::invalid_argument("Selected text contains NUL");
            return input_utf8_bytes(view);
        } else if constexpr (std::is_same_v<View,QLatin1StringView>) {
            quint64 bytes=0;
            for(const auto c:view){const auto u=static_cast<unsigned char>(c);if(!u)throw std::invalid_argument("Selected text contains NUL");bytes+=u<0x80?1:2;}
            return bytes;
        } else {
            const std::string_view bytes(reinterpret_cast<const char*>(view.data()),static_cast<std::size_t>(view.size()));
            if(bytes.find('\0')!=std::string_view::npos || !edi::assistant::detail::utf8(bytes))throw std::invalid_argument("Selected text has invalid UTF-8");
            return bytes.size();
        }
    });
}
inline void validate_selected_text(const QJsonObject& value) {
    using B = edi::assistant::SelectedFileLimits;
    static constexpr std::array<const char*,11> fields{"file_id","collection_id","generation","encoding","text",
        "total_bytes","start","end","next_offset","eof","complete"};
    if (value.size() != static_cast<qsizetype>(fields.size())) throw std::invalid_argument("Selected text shape is unavailable");
    for (const auto* field : fields) if (!value.contains(QLatin1StringView(field)))
        throw std::invalid_argument("Selected text shape is unavailable");
    const auto text = [&](const char* key) {
        const auto member=value.value(QLatin1StringView(key));
        if (!member.isString()) throw std::invalid_argument("Selected text field has an invalid type");
        return member.toStringView();
    };
    for (const auto* key : {"file_id","collection_id"}) {
        const auto id=text(key);
        if (id.isEmpty() || selected_text_utf8_bytes(id)>edi::assistant::Limits::id_bytes)
            throw std::invalid_argument("Selected text identity is unavailable");
    }
    const auto generation=text("generation"); bool valid=false;
    if (generation.isEmpty() || generation.size()>std::numeric_limits<quint64>::digits10+1) throw std::invalid_argument("Selected text generation is unavailable");
    // This bounded identity token is at most the original decimal generation;
    // it is never a C-scaled selected-content conversion.
    const auto decimal=generation.toString();(void)decimal.toULongLong(&valid);
    if(!valid)throw std::invalid_argument("Selected text generation is unavailable");
    for (const auto c:decimal) if (c.unicode()<'0' || c.unicode()>'9') throw std::invalid_argument("Selected text generation is unavailable");
    if (!QAnyStringView::equal(text("encoding"),QLatin1StringView("utf-8"))) throw std::invalid_argument("Selected text encoding is unavailable");
    const auto bytes=[&](const char* key) {
        const auto n=value.value(QLatin1StringView(key));
        if (!n.isDouble() || !std::isfinite(n.toDouble()) || n.toDouble()<0 ||
            std::floor(n.toDouble())!=n.toDouble() || n.toDouble()>B::file_bytes)
            throw std::invalid_argument("Selected text range is unavailable");
        return static_cast<quint64>(n.toDouble());
    };
    const auto total=bytes("total_bytes"), first=bytes("start"), end=bytes("end"), next=bytes("next_offset");
    const auto literal=text("text");
    if (first>end || end>total || end-first>B::read_bytes || next!=end || selected_text_utf8_bytes(literal)!=end-first || !value.value("eof").isBool() || !value.value("complete").isBool() ||
        value.value("eof").toBool()!=(end==total) || value.value("complete").toBool()!=(first==0 && end==total))
        throw std::invalid_argument("Selected text facts are inconsistent");
}
} // namespace edi_app
