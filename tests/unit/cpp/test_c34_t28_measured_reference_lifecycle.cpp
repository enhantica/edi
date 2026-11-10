#include <doctest/doctest.h>

#include <string>
#include <utility>
#include <vector>

#include "edi/model.hpp"

namespace {
using Values = std::vector<double>;

void check_reads(const edi::PdDataBase& data, const Values& axis, const Values& measured,
                 const Values& sigma) {
    CHECK_MESSAGE(&axis == &data.axis(),
                  " R4 assignment preserves the still-engaged native axis vector object");
    CHECK_MESSAGE(&measured == &static_cast<const Values&>(data.intensity_meas),
                  " R4 assignment preserves the native measured vector object");
    CHECK_MESSAGE(&sigma == &static_cast<const Values&>(data.intensity_meas_su),
                  " R4 assignment preserves the native uncertainty vector object");
}
}  // namespace

TEST_CASE("C34-T28 both measured axes keep all held reads through native lifecycle routes") {
    for (const bool tof : {false, true}) {
        INFO((tof ? "TOF" : "CW"));
        edi::PdDataBase data;
        auto set_axis = [tof](auto& node, Values value) {
            if (tof)
                node.time_of_flight = std::move(value);
            else
                node.two_theta = std::move(value);
        };
        set_axis(data, {12.5, 21.75, 35.125});
        data.intensity_meas = Values{31.25, 52.5, 73.75};
        data.intensity_meas_su = Values{0.125, 0.25, 0.5};
        const Values& axis = data.axis();
        const Values& measured = data.intensity_meas;
        const Values& sigma = data.intensity_meas_su;
        auto donor = data;
        set_axis(donor, {44.25, 57.5});
        donor.intensity_meas = Values{11.25, 17.5};
        donor.intensity_meas_su = Values{0.75, 1.25};
        data = donor;
        check_reads(data, axis, measured, sigma);
        CHECK_MESSAGE((axis == Values{44.25, 57.5} && measured == Values{11.25, 17.5} &&
                       sigma == Values{0.75, 1.25}),
                      " R4 held copy-target reads follow all assigned vector values");
        const auto& alias = data;
        data = alias;
        check_reads(data, axis, measured, sigma);
        const Values& donor_axis = donor.axis();
        const Values& donor_measured = donor.intensity_meas;
        const Values& donor_sigma = donor.intensity_meas_su;
        data = std::move(donor);
        check_reads(data, axis, measured, sigma);
        check_reads(donor, donor_axis, donor_measured, donor_sigma);
        auto moved = std::move(data);
        check_reads(data, axis, measured, sigma);
        set_axis(data, {63.75});
        data.intensity_meas = Values{91.25};
        data.intensity_meas_su = Values{1.75};
        CHECK_MESSAGE(
            (axis == Values{63.75} && measured == Values{91.25} && sigma == Values{1.75}),
            " R4 moved-from held reads remain reusable on their original object");
        CHECK_MESSAGE((moved.axis() == Values{44.25, 57.5} &&
                       static_cast<const Values&>(moved.intensity_meas_su) == Values{0.75, 1.25}),
                      " R4 source reuse cannot overwrite moved destination columns");
        if (tof)
            data.two_theta = Values{10.25};
        else
            data.time_of_flight = Values{2500.5};
        CHECK_THROWS_AS_MESSAGE(data.axis(), std::invalid_argument,
                                " R4 simultaneous axis engagement still refuses");
        if (tof)
            data.two_theta.reset();
        else
            data.time_of_flight.reset();
        check_reads(data, axis, measured, sigma);
        CHECK_MESSAGE((axis == Values{63.75}),
                      " R4 engagement of another axis cannot replace the held axis object");
    }
}
