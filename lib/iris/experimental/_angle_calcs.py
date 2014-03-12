# (C) British Crown Copyright 2014, Met Office
#
# This file is part of Iris.
#
# Iris is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Iris is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Iris.  If not, see <http://www.gnu.org/licenses/>.
"""
Calculations for processing angle and polygon concepts

TODO: which bits are still needed ?

"""
import numpy as np


def _calc_angles_abc(a, b, c):
    """
    Calculate internal angles "abc" from 3 arrays of 2d point locations.

    Args:

    * a, b, c (float array-like):
        Arrays of point coordinates.
        All must have same shape, with shape[-1] == 2.
        [..., 0] and [..., 1] are X and Y values.

    Returns:
        An array of floats without the last (XY) dimension.
        Results are in radians.

    """
    a, b, c = [np.array(x, dtype=float) for x in (a, b, c)]
    assert a.shape == b.shape == c.shape
    assert a.shape[-1] == 2  #  Last dimension holds X+Y components
    ab = b - a
    bc = c - b
    ang_ab = np.arctan2(ab[..., 1], ab[..., 0])
    ang_bc = np.arctan2(bc[..., 1], bc[..., 0])
    # calculate difference angle from one to next == exterior
    ang_diff = ang_bc - ang_ab
    # convert to range +/-180
    ang_diff = np.where(ang_diff < np.pi, ang_diff, ang_diff - 2*np.pi)
    ang_diff = np.where(ang_diff > -np.pi, ang_diff, ang_diff + 2*np.pi)
    # subtract from 180 to get interior angle
    result = np.pi - ang_diff
    return result


def valid_bounds_shapes(x_bounds, y_bounds):
    """
    Calculate which 2d bounds coordinates represent "valid" bounded regions.

    This means they describe an anticlockwise convex quadrilateral.

    Args:

    * x_bounds, y_bounds (float arrays):
        Numpy arrays of X and Y coordinates.
        Both must have same shape, and shape[-1] == 4.

    Returns:
        a boolean array (same shape as arguments).

    .. note::

        The validity concept matches that required by ESMF.

    """
    assert x_bounds.shape == y_bounds.shape
    assert x_bounds.shape[-1] == 4
    pt_0, pt_1, pt_2, pt_3 = [
        np.concatenate((x_bounds[..., i_point:i_point+1],
                        y_bounds[..., i_point:i_point+1]),
                       axis=-1)
        for i_point in range(4)]

    # Flag input locations where any of the 4 points are indistinguishable.
    # TODO: this really needs a valid magnitude concept, not a magic number (!)
    eps = 1e-5
    valids = ((np.max(np.abs(pt_0 - pt_1), axis=-1) > eps) &
              (np.max(np.abs(pt_0 - pt_2), axis=-1) > eps) &
              (np.max(np.abs(pt_0 - pt_3), axis=-1) > eps) &
              (np.max(np.abs(pt_1 - pt_2), axis=-1) > eps) &
              (np.max(np.abs(pt_1 - pt_3), axis=-1) > eps) &
              (np.max(np.abs(pt_2 - pt_3), axis=-1) > eps))

    # Define a tolerance to exclude angles too close to 0 or 180.
    eps = np.deg2rad(0.01)
    eps_from_180 = np.pi - eps

    # Valid internal angles are >=(0+eps) and <(180-eps).
    def deg_in_180(ang):
        return (eps <= ang) & (ang < eps_from_180)

    a012 = _calc_angles_abc(pt_0, pt_1, pt_2)
    a123 = _calc_angles_abc(pt_1, pt_2, pt_3)
    a230 = _calc_angles_abc(pt_2, pt_3, pt_0)
    a301 = _calc_angles_abc(pt_3, pt_0, pt_1)

    valids &= (deg_in_180(a012) & deg_in_180(a123) &
               deg_in_180(a230) & deg_in_180(a301))

    return valids


def _lon_degrees_wrap_to_reference(x, y):
    # Wrap x (in degrees) into the range y-180 .. y+180.
    # x and y can be scalars or compatible array objects.
    # TODO: Modify array in-place
    result = x + 5*180 - y
    result -= 360.0 * np.fix(result / 360.0)
    result += y - 180.0
    return result


def fix_longitude_bounds(lons):
    """
    Wrap longitudes within each cell of 2d longitude bounds arrays.

    The longitude values within each cell are wrapped to +/-180 degrees
    relative to the first bound-value in each set of 4.
    The array is modified in-place.

    Args:
    * lons (float array):
        The longitude bounds values, in degrees.
        Must have shape[-1] == 4.

    .. note::

        This calculation is much like that in
        :meth:`~iris.analysis.cartography.wrap_lons`, except that each set of 4
        bound points is wrapped to its own private 'base' value.

    """
    if lons.shape[-1] != 4:
        raise ValueError('2d longitudes array must have shape[-1] == 4.')

    # TODO: Modify array in-place
    lons[:] = _lon_degrees_wrap_to_reference(lons, lons[..., 0:1])


if __name__ == '__main__':
    bad_case_pts = np.array([
                             (-154.300000,  78.963636),
                             (-89.153541,  69.835216),
                             (-42.562722,  74.711569),
                             (-334.300000,  86.490909)])
    xx = bad_case_pts[..., 0].reshape((1,4))
    yy = bad_case_pts[..., 1].reshape((1,4))
    assert ~valid_bounds_shapes(xx, yy)
