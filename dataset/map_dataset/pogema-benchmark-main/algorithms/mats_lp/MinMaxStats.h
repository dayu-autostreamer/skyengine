#pragma once
#include <cmath>
#include <limits>

class MinMaxStats
{
public:
    double maximum;
    double minimum;
    explicit MinMaxStats():maximum(std::numeric_limits<double>::lowest()), minimum(std::numeric_limits<double>::max()){}
    void update(double value)
    {
        maximum = std::fmax(maximum, value);
        minimum = std::fmin(minimum, value);
    }
    double normalize(double value)
    {
        if (value < minimum)
            value = minimum;
        if(maximum > minimum)
            return (value - minimum)/(maximum - minimum);
        return value;
    }
};