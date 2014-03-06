import numpy as np


def _calc_angles_abc(a, b, c):
    """
    Calculate internal angles "abc" from 3 arrays of 2d point locations.

    Args:

    * a, b, c (float array-like, last dimension == 2):
        Arrays of point coordinates.  [..., 0] and [..., 1] are X and Y values.
        All must have same shape.

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
    # ALSO explicitly invalidate any angles where two of the points coincide.
    # TODO: this really needs a valid magnitude concept, not a magic number (!)
    eps = 1e-5
    # Flag input locations where any of the 3 points are indistinguishable.
    sames = ((np.max(np.abs(a - b), axis=-1) < eps) |
             (np.max(np.abs(b - c), axis=-1) < eps) |
             (np.max(np.abs(c - a), axis=-1) < eps))
    # Invalidate those locations by returning an out-of-range value.
    result[sames] = 2.0 * np.pi
    return result


def valid_bounds_shapes(lon_bounds, lat_bounds):
    """
    Calculate which 2d bounds values represent "valid" shapes (in ESMF terms).

    This means they describe an anticlockwise convex quadrilateral.

    Args:

    * lon_bounds, lat_bounds (float arrays):
        Numpy arrays of longitude and latitudes, in degrees.
        Both must have same shape.

    Returns:
        a boolean array (same shape as arguments).

    """
    assert lon_bounds.shape == lat_bounds.shape
    assert lon_bounds.shape[-1] == 4
    points = [np.concatenate((lon_bounds[..., i_point:i_point+1],
                              lat_bounds[..., i_point:i_point+1]),
                             axis=-1)
              for i_point in range(4)]

    def deg_in_180(ang):
        # Check that an internal angle is >= 0 and < 180.
        return (0.0 <= ang) & (ang < np.pi)

    a012 = _calc_angles_abc(points[0], points[1], points[2])
    a123 = _calc_angles_abc(points[1], points[2], points[3])
    a230 = _calc_angles_abc(points[2], points[3], points[0])
    valids = deg_in_180(a012) & deg_in_180(a123) & deg_in_180(a230)
    return valids


def _lon_degrees_wrap_to_reference(x, y):
    # Wrap x (in degrees) into the range y-180 .. y+180.
    # x and y can be scalars or compatible array objects.
    x += 5*180 - y
    x -= 360.0 * np.fix(x / 360.0)
    x += y - 180.0
    return x


def fix_longitude_bounds(lons):
    # Wrap an array of bounds values.
    # Each set of 4 bounds points is wrapped individually, to be compatible
    # with bounds[0] in each case.
    assert lons.shape[-1] == 4
    lons = _lon_degrees_wrap_to_reference(lons, lons[..., 0:1])

#lons = np.array([[ 180.,    180.25,  180.25,  180.  ], [0, 1, 1, 0]])
#lats = np.array([[-77.03860474, -77.03860474, -76.98234558, -76.98234558], [0, 0, 1, 1]])
#valid_bounds_shapes(lons, lats)
