"""

"""
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import linregress

import iris
from iris.analysis import Aggregator
import iris.quickplot as qplt
from iris.util import rolling_window


def _linfit_coeffs(a_x, a_y, axis):
    collapsed_data_shape = list(a_x.shape)
    collapsed_data_shape[axis] = 1
    x_means = np.average(a_x, axis=axis)
    x_bar = x_means.reshape(collapsed_data_shape)
    y_means = np.average(a_y, axis=axis)
    y_bar = y_means.reshape(collapsed_data_shape)
    slope_numerator = np.average(a_x * a_y - x_bar * y_bar, axis=axis)
    slope_denominator = np.average(a_x * a_x - x_bar * x_bar, axis=axis)
    slopes = slope_numerator / slope_denominator
    offsets = y_means - slopes * x_means
    return slopes, offsets


# Define a function to perform the custom statistical operation.
# Note: in order to meet the requirements of iris.analysis.Aggregator, it must
# do the calculation over an arbitrary (given) data axis.
def time_correlation_slope(data, times, axis=-1):
    """
    Function to calculate the number of points in a sequence where the value
    has exceeded a threshold value for at least a certain number of timepoints.

    Generalised to operate on multiple time sequences arranged on a specific
    axis of a multidimensional array.

    Args:

    * data (array):
        raw data.

    * times (array):
        axis values for 'data' points.

    """
    if axis < 0:
        # just cope with negative axis numbers
        axis += data.ndim

#    # THIS WAY will need to be repeated over all the points ...
#    slope, intercept, r_coeff, p_value, std_err = linregress(x=times, y=data)
    slope, offset = _linfit_coeffs(a_x=times, a_y=data, axis=axis)
    return slope


def main():
    # Load the whole time-sequence as a single cube.
    file_path = iris.sample_data_path('E1_north_america.nc')
    cube = iris.load_cube(file_path)

    # Make an aggregator from the user function.
    time_unit = cube.coord('time').units
    SLOPE = Aggregator('time_slope',
                       time_correlation_slope,
                       units_func=lambda units: units / time_unit,
                       aux_data_keys='times')

    # Calculate the statistic.
    warm_periods = cube.collapsed('time', SLOPE, times='time')
    warm_periods.rename('Time correlation slopes')
    warm_periods.convert_units('1e-9 K s-1')

    # Plot the results.
    qplt.contourf(warm_periods, cmap='RdYlBu_r')
    plt.gca().coastlines()
    plt.show()


if __name__ == '__main__':
    main()
