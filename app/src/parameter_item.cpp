// SPDX-License-Identifier: BSD-3-Clause
#include "parameter_item.hpp"

#include <QRegularExpression>
#include <algorithm>
#include <cmath>

#include "category_list_model.hpp"
#include "project_editor.hpp"

namespace edi_app {
namespace {

// A spec's LaTeX name as plain text (`$\sigma_1$` -> "σ₁", `$B_{\mathrm{iso}}$` -> "B iso"), or empty
// when it uses anything this does not spell.
QString plain_symbol(const char* latex) {
    if (latex == nullptr) {
        return {};
    }
    QString text = QString::fromUtf8(latex);
    text.remove(QLatin1Char('$'));
    text.replace(QRegularExpression(QStringLiteral(R"(\\mathrm\{([^{}]*)\})")), QStringLiteral("\\1"));
    const std::pair<const char*, const char*> symbols[] = {
        {"\\alpha", "α"}, {"\\beta", "β"}, {"\\gamma", "γ"}, {"\\sigma", "σ"},
        {"\\theta", "θ"}, {"\\mu", "μ"},   {"\\AA", "Å"},    {"\\,", " "}};
    for (const auto& [from, to] : symbols) {
        text.replace(QString::fromUtf8(from), QString::fromUtf8(to));
    }
    // A subscript: digits become subscript digits, anything else follows after a space.
    static const QRegularExpression subscript(QStringLiteral(R"(_\{?([0-9A-Za-z]+)\}?)"));
    QRegularExpressionMatch match;
    while ((match = subscript.match(text)).hasMatch()) {
        QString tail = match.captured(1);
        bool digits = true;
        for (const QChar c : tail) {
            digits = digits && c.isDigit();
        }
        if (digits) {
            for (QChar& c : tail) {
                c = QChar(0x2080 + c.digitValue());
            }
        } else {
            tail.prepend(QLatin1Char(' '));
        }
        text.replace(match.capturedStart(), match.capturedLength(), tail);
    }
    return text.contains(QLatin1Char('\\')) || text.contains(QLatin1Char('{')) || text.contains(QLatin1Char('^'))
               ? QString()
               : text;
}

}  // namespace

ParameterItem::ParameterItem(const edi::ParameterEntry& entry, ProjectEditor& editor, QObject* parent)
    : QObject(parent),
      editor_(editor),
      parameter_(entry.parameter),
      value_(entry.parameter->value),
      uncertainty_(entry.parameter->uncertainty),
      free_(entry.parameter->free),
      refinable_(entry.refinable),
      path_(QString::fromStdString(entry.path)),
      block_kind_(QString::fromStdString(entry.block_kind)),
      block_name_(QString::fromStdString(entry.block_name)),
      category_(QString::fromStdString(entry.category)),
      row_label_(QString::fromStdString(entry.row_label)),
      name_(QString::fromStdString(entry.name)) {
    const edi::ParameterSpec* spec = entry.parameter->spec;
    uid_ = spec != nullptr ? QStringLiteral("%1.%2").arg(QString::fromUtf8(spec->category), QString::fromUtf8(spec->name))
                           : category_ + QLatin1Char('.') + name_;
    display_name_ = spec != nullptr ? QString::fromUtf8(spec->display_name) : name_;
    display_units_ = spec != nullptr ? QString::fromUtf8(spec->display_units) : QString();
    short_name_ = spec != nullptr ? plain_symbol(spec->latex_name) : QString();
    if (short_name_.isEmpty()) {
        short_name_ = display_name_;
    }
    minimum_ = spec != nullptr ? spec->range.min : -std::numeric_limits<double>::infinity();
    maximum_ = spec != nullptr ? spec->range.max : std::numeric_limits<double>::infinity();
    category_icon_ = QString::fromUtf8(category_presentation(category_).icon);
}

void ParameterItem::setBlockIndex(int index) {
    if (block_index_ != index) {
        block_index_ = index;
        emit blockIndexChanged();
    }
}

void ParameterItem::setElementSymbol(const QString& symbol) {
    if (element_symbol_ != symbol) {
        element_symbol_ = symbol;
        emit elementSymbolChanged();
    }
}

void ParameterItem::setPhaseIndex(int index) {
    if (phase_index_ != index) {
        phase_index_ = index;
        emit phaseIndexChanged();
    }
}

void ParameterItem::setRefinable(bool refinable) {
    if (refinable_ != refinable) {
        refinable_ = refinable;
        emit refinableChanged();
    }
}

namespace {
// The refusal of a write to a parameter symmetry holds (edi ADR-0019). The pages disable such a field, so
// this answers only a caller that writes anyway.
QString symmetry_refusal() { return QObject::tr("the space group fixes this parameter or ties it to another"); }
}  // namespace

void ParameterItem::setValue(double value) {
    if (!refinable_) {
        setLastError(symmetry_refusal());
        return;
    }
    edi::Parameter* parameter = parameter_;
    setLastError(editor_.apply(edi::Edit::value(*parameter, value), false));
}

void ParameterItem::setFree(bool free) {
    if (!refinable_) {
        setLastError(symmetry_refusal());
        return;
    }
    edi::Parameter* parameter = parameter_;
    setLastError(editor_.apply(edi::Edit::assign(parameter->free, free), false));
}

int ParameterItem::publish() {
    int changed = 0;
    const bool was_outside = outsideRange();
    if (parameter_->value != value_) {
        value_ = parameter_->value;
        changed |= ValueField;
    }
    const bool had_uncertainty = uncertainty_.has_value();
    if (parameter_->uncertainty != uncertainty_) {
        uncertainty_ = parameter_->uncertainty;
        changed |= UncertaintyField;
    }
    if (parameter_->free != free_) {
        free_ = parameter_->free;
        changed |= FreeField;
    }
    if ((changed & ValueField) != 0) {
        emit valueChanged();
        if (outsideRange() != was_outside) {
            emit outsideRangeChanged();
        }
    }
    if ((changed & UncertaintyField) != 0) {
        emit uncertaintyChanged();
        if (had_uncertainty != uncertainty_.has_value()) {
            emit hasUncertaintyChanged();
        }
    }
    if ((changed & FreeField) != 0) {
        emit freeChanged();
    }
    return changed;
}

void ParameterItem::setLastError(const QString& error) {
    if (error != last_error_) {
        last_error_ = error;
        emit lastErrorChanged();
    }
}

namespace {
// The Analysis slider's half width around a lattice constant's value, in Å (the owner, 2026-10-04).
constexpr double kLatticeConstantSliderHalfWidth = 0.05;
}  // namespace

double ParameterItem::sliderHalfWidth() const {
    if (category_ == QLatin1String("cell") && name_.startsWith(QLatin1String("length_"))) {
        return kLatticeConstantSliderHalfWidth;
    }
    return std::max(std::abs(value_) * 0.5, 1e-3);
}

}  // namespace edi_app
