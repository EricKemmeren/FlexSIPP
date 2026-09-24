#pragma once
#include <vector>
#include <cstdint>
#include <functional>
#include <boost/math/constants/constants.hpp>
#include <boost/functional/hash.hpp>

// BOOST_ENABLE_ASSERT_DEBUG_HANDLER is defined for the whole project


constexpr double epsilon(){
    return 0.0001;
}

constexpr double sqrt2(){
    return boost::math::double_constants::root_two;
}

using gIndex_t = uint16_t;

class intervalTime_t {
    double interval_time;
    public:
    intervalTime_t() = default;
    intervalTime_t(double x) : interval_time(x) {}
    operator double() const { return interval_time; }

    inline friend std::ostream& operator<< (std::ostream& stream, const intervalTime_t& n)
    {
        intervalTime_t zero = 0;
        if (std::isinf(n) && n > zero)
        {
            stream << "Inf";
        }
        else if(std::isinf(n) && n < zero) {
            stream << "-Inf";
        }
        else
        {
            stream << n.interval_time;
        }
        return stream;
    }

    bool operator<(const intervalTime_t& other) const {
        return interval_time < static_cast<double>(other);
    }
    bool operator>(const intervalTime_t& other) const {
        return interval_time > static_cast<double>(other);
    }

    intervalTime_t operator+(intervalTime_t x) {
        return interval_time + x;
    }

    intervalTime_t operator-(intervalTime_t x) {
        return interval_time - x;
    }
};

template<>
struct std::hash<intervalTime_t> {
    std::size_t operator()(const intervalTime_t& t) const noexcept {
        return std::hash<double>{}(static_cast<double>(t));
    }
};

inline std::size_t hash_value(const intervalTime_t& t) {
    return boost::hash<double>{}(static_cast<double>(t));
}

struct incurred_delay_t;

struct incurred_delay_t {
    std::string location;
    intervalTime_t delay;

    incurred_delay_t() = default;
    incurred_delay_t(std::string loc, intervalTime_t d) : location(loc), delay(d) {}

    inline friend std::ostream & operator<< (std::ostream& stream, const incurred_delay_t& n)
    {
        stream << "{";
        stream << "\"location\": \"" << n.location << "\",";
        stream << "\"delay\": " << n.delay << ",";
        stream << "}";
        return stream;
    }
};

struct gam_item_t;

struct gam_item_t {
    intervalTime_t first;
    intervalTime_t second;
    intervalTime_t last_recovery;
    std::vector<incurred_delay_t> incurred_delays = {};

    gam_item_t() = default;
    gam_item_t(intervalTime_t min_gamma, intervalTime_t max_gamma, intervalTime_t _last_recovery,
               std::vector<incurred_delay_t> ids): first(min_gamma), second(max_gamma), last_recovery(_last_recovery), incurred_delays(ids) {}

    inline friend bool operator==(const gam_item_t &gam, const gam_item_t &other) {
        return gam.first == other.first && gam.second == other.second;
    }

    inline friend std::ostream& operator<< (std::ostream& stream, const gam_item_t& n){
        stream << "{";
        stream << "\"min_gamma\": " << n.first << ",";
        stream << "\"max_gamma\": " << n.second << ",";
        stream << "\"recovery_left\": " << n.last_recovery << ",";
        stream << "\"incurred_delays\": [";
        for (incurred_delay_t id: n.incurred_delays) {
            stream << id << ", ";
        }
        stream << "]}";
        return stream;
    }

    inline friend gam_item_t reduce(const gam_item_t &gam, intervalTime_t reduction) {
        intervalTime_t min_gamma = std::max(gam.first - reduction, 0.0);
        intervalTime_t max_gamma = std::max(gam.second - reduction, 0.0);
        intervalTime_t new_recovery = std::max(gam.last_recovery - reduction, 0.0);

        return gam_item_t(min_gamma, max_gamma, new_recovery, gam.incurred_delays);
    }

    inline friend bool valid_gamma(const gam_item_t &gam) {
        intervalTime_t eps = epsilon();
        if(abs(gam.second) < eps) {
            std::cerr << "Still zero" << std::endl;
            return true;
        }
        intervalTime_t diff = abs(gam.second - gam.first);
        std::cerr << "Difference " << diff << " of " << gam << std::endl;
        return diff > eps;
    }
};

using gamma_t = std::vector<gam_item_t>;

namespace std {
    template<>
    struct hash<gamma_t> {
        std::size_t operator()(gamma_t const &vec) const {
            std::size_t seed = vec.size();
            for (gam_item_t x: vec) {
                seed ^= std::hash<intervalTime_t>()(x.second);
            }
            return seed;
        }
    };
}
