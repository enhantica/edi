#include <doctest/doctest.h>

#include <optional>
#include <type_traits>
#include <utility>
#include <vector>

#include "edi/model.hpp"

namespace {
using Values = std::vector<double>;

void same_object(const Values& held, const Values& current) {
    REQUIRE_MESSAGE(&held == &current,
                    " R4 a held measured read keeps its vector object through writes");
    CHECK_MESSAGE(held == current,
                  " R4 a held measured read observes the current vector contents");
}
}  // namespace

TEST_CASE("C34-T28 measured references survive writes copies and moves") {
    edi::PdDataBase data;
    data.two_theta = Values{12.5, 13.75, 17.0};
    data.intensity_meas = Values{4.25, 9.5, 16.75};
    data.intensity_meas_su = Values{0.5, 0.75, 1.25};
    const Values& axis = data.axis();
    const Values& measured = data.intensity_meas;
    const Values& sigma = data.intensity_meas_su;
    data.write_column(&edi::PdDataBase::intensity_meas, Values{2.75, 6.25});
    data.write_column(&edi::PdDataBase::intensity_meas_su, Values{0.25, 0.5});
    data.write_axis(&edi::PdDataBase::two_theta, Values{19.5, 25.75});
    same_object(axis, data.axis());
    same_object(measured, data.intensity_meas);
    same_object(sigma, data.intensity_meas_su);
    CHECK_MESSAGE((axis == Values{19.5, 25.75}), " R4 axis writes update a held read");
    CHECK_MESSAGE((measured == Values{2.75, 6.25}),
                  " R4 measured writes update a held read");

    edi::PdDataBase donor(data);
    donor.intensity_meas = Values{31.5, 47.25};
    donor.two_theta = Values{33.5, 44.75};
    data = donor;
    same_object(axis, data.axis());
    same_object(measured, data.intensity_meas);
    CHECK_MESSAGE((measured == Values{31.5, 47.25}),
                  " R4 copy assignment updates held target reads");
    donor.intensity_meas = Values{55.25};
    data = std::move(donor);
    same_object(axis, data.axis());
    same_object(measured, data.intensity_meas);
    CHECK_MESSAGE((measured == Values{55.25}),
                  " R4 move assignment updates held target reads");
    edi::PdDataBase moved(std::move(data));
    same_object(measured, data.intensity_meas);
    data.intensity_meas = Values{71.75};
    CHECK_MESSAGE((measured == Values{71.75}),
                  " R4 a moved-from measured vector is reusable through a held read");
    CHECK_MESSAGE((static_cast<const Values&>(moved.intensity_meas) == Values{55.25}),
                  " R4 source reuse cannot change the move destination");
}

TEST_CASE("C34-T28 axis engagement preserves the still-engaged axis object") {
    edi::PdDataBase data;
    CHECK_THROWS_AS_MESSAGE(data.axis(), std::invalid_argument,
                            " R4 no engaged axis remains a named refusal");
    data.time_of_flight = Values{2100.5, 3300.75};
    const Values& held = data.axis();
    data.two_theta = Values{17.25, 19.5};
    CHECK_THROWS_AS_MESSAGE(data.axis(), std::invalid_argument,
                            " R4 two engaged axes remain a named refusal");
    data.two_theta.reset();
    same_object(held, data.axis());
    data.write_axis(&edi::PdDataBase::time_of_flight, Values{4200.25, 5700.5});
    same_object(held, data.axis());
    CHECK_MESSAGE((held == Values{4200.25, 5700.5}),
                  " R4 writes keep a still-engaged axis read current");
}

TEST_CASE("C34-T28 plain non-loop native writes keep their prior epoch boundary") {
    static_assert(std::is_same_v<decltype(&edi::PeakBase::cutoff_fwhm), double edi::PeakBase::*>,
                  " R5 the preserved plain native member keeps its member-pointer type");
    edi::PeakBase peak;
    double& retained = peak.cutoff_fwhm;
    const auto before = peak.epoch.value();
    retained = 27.5;
    CHECK_MESSAGE(peak.cutoff_fwhm == 27.5,
                  " R5 a preserved native reference still writes its plain member");
    CHECK_MESSAGE(peak.epoch.value() == before,
                  " R5 plain native writes acquire no stronger epoch identity");
    retained = 27.5;
    CHECK_MESSAGE(peak.epoch.value() == before,
                  " R5 equal plain writes are not inferred from value encoding");
    auto copied = peak;
    CHECK_MESSAGE(copied.epoch.value() != peak.epoch.value(),
                  " I23 edi copies keep their prior fresh-epoch policy");
}
