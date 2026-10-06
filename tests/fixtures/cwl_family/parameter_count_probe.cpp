// SPDX-License-Identifier: BSD-3-Clause
// A Qt-free metadata boundary vehicle. Production publish/refresh/setter bodies
// are inserted unchanged by the hidden gate; only notification plumbing is inert.
#include <iostream>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
namespace edi {
struct Parameter {
    double value;
    bool free;
};
struct CategoryField {
    const Parameter* parameter;
    bool refinable;
};
struct Category {
    std::vector<CategoryField> fields, asymmetry;
};
struct Block {
    std::vector<Category> categories;
};
struct Project {
    std::vector<std::shared_ptr<Block>> structures, experiments;
};
auto structure_categories(const Block& b) { return b.categories; }
auto experiment_categories(const Block& b) { return b.categories; }
}  // namespace edi
namespace edi_app {
struct ParameterItem {
    edi::Parameter* parameter_;
    bool refinable_;
    const edi::Parameter* parameter() const { return parameter_; }
    void setRefinable(bool);
    void refinableChanged() {}
    void publish() {}
};
struct ParameterRegistry {
    std::vector<ParameterItem*> items_;
    void refreshRefinable(edi::Project&);
    void refreshElements(const edi::Project&) {}
    void publish(edi::Project&);
};
#define emit
// INSERT_PRODUCTION_BODIES
#undef emit
}  // namespace edi_app
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const std::string vehicle = argv[1];
    edi::Parameter a{4.76, true}, coefficient{.031, true}, width{.047, false}, held{160., false};
    edi::Project project;
    project.structures = {std::make_shared<edi::Block>(), std::make_shared<edi::Block>()};
    project.experiments = {std::make_shared<edi::Block>()};
    project.structures[1]->categories.push_back({{{&a, true}}, {}});
    project.experiments[0]->categories.push_back({{{&coefficient, true}, {&width, true}}, {}});
    auto& owner = vehicle == "second-structure" ? *project.structures[1] : *project.experiments[0];
    auto& category = owner.categories[0];
    auto& fields = vehicle == "experiment-fields" ? category.fields : category.asymmetry;
    fields.push_back({&held, false});
    edi_app::ParameterItem first{&a, true}, second{&coefficient, true}, fixed_item{&width, true},
        excluded{&held, false};
    edi_app::ParameterRegistry registry{{&first, &second, &fixed_item, &excluded}};
    auto census = [&]() {
        std::vector<const edi::Parameter*> selected;
        for (auto* item : registry.items_)
            if (item->refinable_) selected.push_back(item->parameter());
        return selected;
    };
    const auto before = census();
    for (double value : {4.9, 4.81, 4.76}) {
        a.value = value;
        registry.publish(project);
        if (census() != before || excluded.refinable_ || !first.refinable_ || !second.refinable_ ||
            !fixed_item.refinable_) {
            std::cerr << "A live value publication must preserve parameter membership, free/fixed "
                         "counts and excluded metadata across every block and category field\n";
            return 1;
        }
        int free = 0, fixed = 0;
        for (auto* item : registry.items_)
            if (item->refinable_) {
                item->parameter_->free ? ++free : ++fixed;
            }
        if (free != 2 || fixed != 1 || registry.items_.size() != 4) return 1;
    }
    return 0;
}
