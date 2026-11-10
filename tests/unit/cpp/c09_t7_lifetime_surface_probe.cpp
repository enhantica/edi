#include <concepts>
#include <memory>

#include "edi/model.hpp"

template <typename T>
concept publicly_promotable_life_token = requires(const T& source) {
    { source.life_token() } -> std::same_as<std::weak_ptr<const void>>;
    { source.life_token().lock() } -> std::same_as<std::shared_ptr<const void>>;
};

template <typename T>
concept publicly_promotable_life_tag = requires(const T& source) {
    { source.life_tag() } -> std::same_as<std::weak_ptr<const void>>;
    { source.life_tag().lock() } -> std::same_as<std::shared_ptr<const void>>;
};

static_assert(!publicly_promotable_life_token<edi::Project>,
              "Project::life_token().lock() must not be reachable from user code");
static_assert(!publicly_promotable_life_tag<edi::Project>,
              "an equivalent Project::life_tag().lock() surface must not be reachable");

int main() { return 0; }
