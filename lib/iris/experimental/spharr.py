'''
Created on May 7, 2013

@author: itpp

Spherical gridcell area-overlap calculations.
Array calculation version.

'''

import copy
import itertools

import numpy as np

# Control validity checking (turn off for speed)
ENABLE_CHECKING = False

class ArraysObject(object):
    """
    An abstract class containing a group of coupled array-like properties.
 
    Provides a structure for array-specific operations, so that operations can
    be vectorized over the array object, instead of looped over an array of
    objects.
 
    Provides group of array attributes, of known names, which share a common
    shape prefix which is the 'shape' of the object.
    Supports operations (distributed over components):
       __getitem__, reshape, concatenate, copy 
    operating over all component arrays to define a new object.
    Derived objects' components may be views on the original (as normal numpy).
    Additional generic array operations can be defined via a helper method.

    FOR NOW: assume masked arrays everywhere.  Otherwise concatenate etc. are
    awkward...

    """
    # Define the array properties for this type (set in subclasses).
    # N.B. *no* names is not actually valid
    array_names = ()

    def __init__(self):
        # Start empty
        self.set_arrays({key: np.array([], dtype=float)
                             for key in self.array_names})

    def set_arrays(self, arrays_dict, shape=None):
        """
        Set array properties from a name-keyed dictionary.

        If shape is given, this overrides the automatic choice, which is the
        longest common to all arrays.
        Note: need set *all* of them, but results must be consistent.

        """
        if ENABLE_CHECKING:
            # Check that all the arrays are in our recognised list
            assert all(key in self.array_names for key in arrays_dict)
        # Assign arrays from given list
        self.__dict__.update(arrays_dict)
        if shape == None:
            # Recalculate the longest-common-prefix shape
            arrays = [self.__dict__.get(key, None) for key in array_names]
            shapes_bylen = sorted([a.shape for a in arrays if a], key=len)
            shape = shapes_bylen[0]
        self.shape = shape
        if ENABLE_CHECKING:
            self._check()

    def _check(self):
        """Check that arrays match the common base shape."""
        arrays = [self.__dict__.get(key, None) for key in array_names]
        shape_size = len(self.shape)
        assert all(a.shape[:shape_size] == self.shape
                   for a in arrays if a)

    def array_or_none(self, name):
        """
        Fetch a named component array by name.

        If missing, return None instead of raising an error.

        """
        if ENABLE_CHECKS:
            if not name in self.array_names:
                raise ValueError(
                    'unrecognised array component name "{}"'.format(name))
        return self.__dict__.get(name, None)

    def copy(self):
        """
        Make a copy with copies of all the object arrays.

        Includes all existing properties (unlike new_from_arrays etc).

        """
        new_obj = super(self, ArraysObject).copy()
        arrays = {key: self.__dict__.get(key, None)
                  for key in self.array_names}
        arrays = {key: array.copy()
                  for key, array in arrays.iteritems() if array}
        new_obj.set_arrays(arrays, shape=self.shape)
        return new_obj

    @classmethod
    def new_from_arrays(cls, arrays_dict, shape=None):
        """Make a new instance from a name-keyed dictionary of arrays."""
        new_obj = cls()
        new_obj.set_arrays(arrays_dict, shape=shape)
        return new_obj

    def new_by_function(self, function, new_shape=None,
                          *op_args, **op_kwargs):
        """Make new result by applying a common function to all the arrays."""
        arrays = {key: self.__dict__.get(key, None)
                  for key in self.array_names}
        new_arrays = {key: function(a, *op_args, **op_kwargs)
                      for key, a in arrays if a is not None}
        return self.new_from_arrays(new_arrays, shape=new_shape)

    def __getitem__(self, index):
        arrays = {key: self.__dict__.get(key, None)
                  for key in self.array_names}
        new_arrays = {key: a.__getitem__(index)
                      for key, a in arrays.iteritems() if a}
        return self.new_from_arrays(new_arrays)
#
# NOTE: following will *not* work, as some may need the masked version
# --i.e. "np.ma.MaskedArray.__getitem__" in place of "np.ndarray.__getitem__"
# (YUCK!!)
#        return self.new_by_function(np.ndarray.__getitem__, new_shape=None, 
#                                    index)
 
    def reshape(self, dims):
        arrays = {key: self.__dict__.get(key, None)
                  for key in self.array_names}
        new_arrays = {key: a.reshape(dims)
                      for key, a in arrays.iteritems() if a}
        return self.new_from_arrays(new_arrays)
#
# NOTE: this probably *would* work, as reshape *does* preserve masks
#        return self.new_by_function(np.ndarray.reshape, new_shape=dims, dims)

    ALL_MASKED = True
    if all_masked:
        @classmethod
        def concatenate(cls, objects, axis=None):
            if ENABLE_CHECKS:
                for obj in objects:
                    assert isintance(obj, cls)
                obj0 = objects[0]
                for key in cls.array_names:
                    none0 = obj0.array_or_none(key)
                    assert all((obj.array_or_none(key) is None) == none0
                               for obj in objects)
            array_tuples = {key: tuple([getattr(obj, key)
                                         for obj in objects])
                            for key in cls.array_names
                            if obj[0].array_or_none(key)}
            new_arrays = {key: np.ma.concatenate(arrays_tuple, axis=axis)
                          for key, arrays_tuple in array_tuples.iteritems()}
            return self.new_from_arrays(new_arrays)
    else:
        # Version of concatenate that tries to optimise masking
        # Isn't this nasty ?!?
        @classmethod
        def concatenate(cls, objects, axis=None):
            if ENABLE_CHECKS:
                for obj in objects:
                    assert isintance(obj, cls)
                obj0 = objects[0]
                for key in cls.array_names:
                    none0 = obj0.array_or_none(key)
                    assert all((obj.array_or_none(key) is None) == none0
                               for obj in objects)

            key_arrays = {key: [obj.array_or_none(key) for obj in objects]
                          for key in cls.array_names}
            valid_key_classes = {key: [a.__class__ for a in arrays]
                                 for key, arrays in key_arrays.iteritems()
                                 if arrays[0] is not None}
            key_ops = {key: np.concatenate
                            if all(cls == np.ndarray
                                   for cls in classes)
                            else np.ma.concatenate
                       for key, classes in valid_key_classes.iteritems()}
            array_tuples = {key: tuple([getattr(obj, key)
                                         for obj in objects])
                            for key in valid_key_classes}
            new_arrays = {key: key_ops[key](arrays_tuple, axis=axis)
                          for key, arrays_tuple in array_tuples.iteritems()}
            return self.new_from_arrays(new_arrays)
#
# NOTE: following will not work, as concatenate does not preserve masks
# --i.e. "np.ma.concatenate" in place of "np.concatenate"
# (YUCK!!)
#        return self.new_by_function(np.concatenate, new_shape=None,
#                                    axis=axis)


def convert_latlons_to_xyzs(lats, lons):
    zs = np.sin(lats)
    cos_lats = np.cos(lats)
    xs = cos_lats * np.cos(lons)
    ys = cos_lats * np.sin(lons)
    return (x, y, z)


class ZeroPointLatlonError(ValueError):
    def __init__(self, *args, **kwargs):
        if not args:
            args = ['Point too close to zero for lat-lon conversion.']
        super(ZeroPointLatlonError, self).__init__(*args, **kwargs)

POINT_ZERO_MAGNITUDE = 1e-15
ANGLE_ZERO_MAGNITUDE = 1e-8
COS_ANGLE_ZERO_MAGNITUDE = 1e-8

def convert_xyzs_to_latlons(xs, ys, zs, error_any_zeros=False):
    """
    Convert arrays of XYZ to LAT,LON.

    Returns masked arrays (lats, lons).
    Underflows are avoided, but return values are not specified.

    """
    mod_sqs = xs * xs + ys * ys + zs * zs
    zero_points = np.abs(mod_sqs) < POINT_ZERO_MAGNITUDE
    if error_any_zeros and np.any(zero_points):
        raise ZeroPointLatLonError()
    # Fake zero points to avoid overflow warnings
    mod_sqs[zero_points] = POINT_ZERO_MAGNITUDE
    # Calculate by inverse trig, and mask any zero points
    lats = np.arcsin(zs / np.sqrt(mod_sqs))
    lons = np.arctan2(ys, xs)
    return (lats, lons)


class SphPointZ(ArraysObject):
    """An array of 2d points on the unit sphere."""
    array_names = ('lats', 'lons', 'xs', 'ys', 'zs')

    def __init__(self, latlons=None, xyzs=None, in_degrees=False):
        """Initialise PointsZ, setting zero points to all-0s."""
        super(self, SphPointZ).__init__()
        if latlons is not None:
            self.lats, self.lons = latlons
        if xyzs is not None:
            self.xs, self.ys, self.zs = xyzs
        match_error = False
        if xyzs is not None and (latlons is None or ENABLE_CHECKING):
            lats, lons = convert_xyzs_to_latlons(*xyzs)
            if latlons is None:
                self.lats, self.lons = lats, lons
            elif ENABLE_CHECKING:
                if not np.allclose([lats, lons], [self.lats, self.lons]):
                    match_error = True
        if latlons is not None and (xyzs is None or ENABLE_CHECKING):
            xs, ys, zs = convert_latlons_to_xyzs(*latlons)
            if xyzs is None:
                self.xs, self.ys, self.zs = xyzs
            elif ENABLE_CHECKING:
                if not np.allclose([xs, ys, zs], [self.xs, self.ys, self.zs]):
                    match_error = True
        if match_error:
            raise ValueError('inconsistent latlons and xyzs args.')
        self.shape = self.xs.shape

    def antipodes(self):
        return SphPointZ(xyzs=(-self.xs, -self.ys, -self.zs))

    def __eq__(self, others):
        return ((abs(self.xs - others.xs) < POINT_ZERO_MAGNITUDE) &
                (abs(self.ys - others.ys) < POINT_ZERO_MAGNITUDE) & 
                (abs(self.zs - others.zs) < POINT_ZERO_MAGNITUDE))

    def __ne__(self, others):
        return ~self.__eq__(others)

    def dot_products(self, other):
        results = (self.xs * other.xs + 
                   self.ys * other.ys +
                   self.zs * other.zs)
        # Clip to valid range, so small errors don't break inverse-trig usage
        return np.max(-1.0, np.min(1.0, results))

    def cross_products(self, other):
        ax, ay, az = self.xs, self.ys, self.zs
        bx, by, bz = other.xs, other.ys, other.zs
        x, y, z = ((ay * bz - az * by),
                   (az * bx - ax * bz),
                   (ax * by - ay * bx))
        return SphPointZ(xyzs=(x, y, z))

    def distances_to(self, other):
        return np.acos(self.dot_product(other))

#    def __str__(self):
#        def r2d(radians):
#            return radians * 180.0 / math.pi
#        return 'SphPoint({})'.format(self._ll_str())
#
#    def __repr__(self):
#        return '{}({!r}, {!r})'.format(self.__class__.__name__,
#                                       self.lat, self.lon)
#
#    def _ll_str(self):
#        def r2d(radians):
#            return radians * 180.0 / math.pi
#        return '({:+06.1f}d, {:+06.1f}d)'.format(r2d(self.lat), r2d(self.lon))


def sph_points(points_or_latlons, in_degrees=False):
    """Make (lats,lons) into SphPointZ, or return a SphPointZ unchanged."""
    if hasattr(points_or_latlons, 'lats'):
        return points_or_latlons
    if len(points_or_latlons) != 2:
        raise ValueError('sph_points argument not a SphPointZ. '
                         'Expected (lats, lons), got : {!r}'.format(
                             points_or_latlons))
    return SphPointZ(latlons=points_or_latlons, in_degrees=in_degrees)

ZERO_POINT = sph_points(xyzs=(0.0,0,0))

class SphGcSegZ(ArraysObject):
    """ An array of great circle segments, from 'A' to 'B' on unit sphere. """

    array_names = ('start_points', 'end_points', 'poles')

    def __init__(self, start_points, end_points):
        self.start_points = sph_points(start_points)
        self.end_points = sph_points(end_points)
        if ENABLE_CHECKING:
            assert start_points.shape == end_points.shape
        self.poles = self.end_points.cross_products(self.start_points)

    def reverses(self):
        return SphGcSegZ(self.end_points, self.start_points)

    def have_points_on_left_side(self, points):
        """
        Returns >0 (left), <1 (right) or =0.0 (close to the line).

        'COS_ANGLE_ZERO_MAGNITUDE' defines a tolerance zone near the line
        (i.e. 'nearly colinear'), where 0.0 is always returned.
        So the caller can use, for example. '>' or '>=' as required, which will
        automatically ignore 'small' values of the wrong sign.

        Note: this calculation is much faster than the angles_to_points one.

        """
        dots = self.poles.dot_products(points)
        dots[abs(dots) < COS_ANGLE_ZERO_MAGNITUDE] = 0.0
        return -dots

    def _cos_angles_to_others(self, others):
        # Cosines of angles between self + others
        return self.poles.dot_products(others.poles)

    def _cos_angles_to_points(self, points):
        """Cosines of (angles from AB to AP), where P = given point."""
        # Perform basic calculation
        seg2s = SphGcSegZ(self.start_points, points)
        results = self._cos_angles_to_others(seg2s)
        # Fix result=1.0 wherever testpoints == startpoints
        results[self.start_points == points] = 1.0
        return results

    def angles_to_others(self, others):
        """
        Angles between self and other SphGcSegZ
        
        At present this simply works on dot products, so cannot resolve
        negative angles.  As these are segments, not just GCs, this could be
        fixed.  However, this is adequate for the area calculations, which is
        all it is currently used for.

        Note: angles_to_points does give signed results, but is slow.
        
        """
        return np.arccos(self._cos_angles_to_others(others))

    def angles_to_points(self, points):
        """
        Angles from AB to AP.

        Result from -180 to +180 (unlike angles_to_others).

        """
        results = np.arccos(self._cos_angles_to_points(points))
        not_on_lefts = abs(results) > ANGLE_ZERO_MAGNITUDE
        not_on_lefts &= (self.have_points_on_left_side(points) < 0.0)
        results *= np.where(not_on_lefts, -1.0, 1.0)
        return results

#    def pseudoangle_to_point(self, point):
#        # Angle from AB to AP
#        result = 1.0 - self._cos_angle_to_point(point)
#        if abs(result) > COS_ANGLE_ZERO_MAGNITUDE \
#                and self.has_point_on_left_side(point) < 0.0:
#            result = -result
#        return result

    def intersection_points_with_others(self, others):
        """
        Calculate the intersection points with the other segments.

        For arguments of given shape, returns SphPointZ[2, <shape>]
        Returns masked points where the two originals are parallel.

        """
        # Perform basic calculation
        a_points = self.poles.cross_products(others.poles)
        # Construct results, with shape (2, *self.shape)
        b_points = a_points.antipodes()
        arrays = {key: ([a_points.array_or_none(key),
                          b_points.array_or_none(key)])
                  for key in SphPointZ.array_names}
        arrays = {key: np.array(val)
                  for key, val in arrays.iteritems()
                  if val[0] is not None and val[1] is not None}
        return SphPointZ.new_from_arrays(arrays)

#    def __repr__(self):
#        return '{}({}, {})'.format(self.__class__.__name__,
#                                   repr(self.point_a),
#                                   repr(self.point_b))
#
#    def __str__(self):
#        return 'SphSeg({!s} -> {!s}, pole={!s}>'.format(
#            self.point_a._ll_str(),
#            self.point_b._ll_str(),
#            self.pole._ll_str())


class TooFewPointsForPolygonError(ValueError):
    def __init__(self, *args, **kwargs):
        if not args:
            args = ['Polygon must have at least 3 points.']
        super(TooFewPointsForPolygonError, self).__init__(*args, **kwargs)


class NonConvexPolygonError(ValueError):
    def __init__(self, *args, **kwargs):
        if not args:
            args = ['Polygon points cannot be reordered to make it convex.']
        super(NonConvexPolygonError, self).__init__(*args, **kwargs)


class SphAcwConvexPolygonZ(ArraysObject):
    def __init__(self, points=[], in_degrees=False):
        """
        Make an array of polygons of equal numbers of points.
        The last dimension is the points.

        """
        self._set_points([sph_point(point, in_degrees=in_degrees)
                          for point in points])
        self._make_anticlockwise_convex()

    def _set_points(self, points):
        # Assign to our points, check length and uncache edges
        self.points = points
        self.max_points = points.shape[-1]
        if self.max_points < 3:
            raise TooFewPointsForPolygonError()
        self.shape = points.shape[:-1]
        # Calculate edges
        next_points = points[1:] + points[:1]
        self._edges = SphGcSegZ(points, next_points)
        # Calculate centres
        xyzs_centres = np.mean([points.xs, points.ys, points.zs], axis=-1)
        self._centre_points = SphPointZ(xyzs=xyz_centres)
        radius_cosines = [self._centre_points.dot_products(self.points)]
        self._max_radii = np.acos(np.min(radius_cosines, axis=-1))

    def _remove_duplicate_points(self):
        # Remove duplicate adjacent points so all angles can be calculated.
        # Only within current ordering: can still have duplicates elsewhere.
        removes = self.points == ZERO_POINT
        # first remove masked points
        prev_points = SphPointZ.concatenate(([ZERO_POINT], points[:-1]))
        removes = removes | (points == prev_points)
        self._set_points(points)

    def _is_anticlockwise_convex(self):
        # Check if our points are arranged in a convex anticlockwise chain.
        # To use this, must be able to calculate edges --> must have no
        # adjacent duplicated points.
        points = ArraysObject.concatenate(
            (self.points[..., 2:] + self.points[..., :2]),
            axis=-1)
        oks = self.edges.has_point_on_left_side(points)
        # Return True for all polys that have all points ok.
        return np.logical_and.reduce(oks, axis=-1)

    def _make_anticlockwise_convex(self):
        # Reorder points as required, or raise an error if not possible.
        # Make reference edges from the centres to all zeroth-points
        edge0s = SphGcSegZ(self._centre_points, self.points[...,0])
        # Calculate angles from reference edge to all points
        angles = edge0s.angles_to_points(self.points)
        # Sort points into this order, with original [0] at start
        angles = (angles + 360.0) % 360.0
        angles_sortorder = np.argsort(angles, axis=-1)
        new_points = self.points[angles_sortorder]
        # Set new points, and remove any duplicates
        self._set_points(new_points)
        self._remove_duplicate_points()
        # Should now be as required
        if not self._is_anticlockwise_convex():
            raise NonConvexPolygonError()

    def contain_points(self, points, in_degrees=False):
        if points.shape != self.shape:
            raise ValueError('Test points shape differs from PolygonZ shape...'
                             '\n points/polys shapes = {} / {}'.format(
                                 points.shape, self.shape))
        points = sph_points(points, in_degrees=in_degrees)
        #make edges*points shapes for comparisons
        polys_shape = list(self.shape)
        edges = self._edges
        points = points.reshape(polys_shape + [1])
        points = points[..., [0]*self.max_points]
        oks = edges.have_points_on_left(points)
        return np.logical_and.reduce(oks, axis=-1)

    def area(self):
        edges = self.edge_gcs()
        preceding_edges = edges[-1:] + edges[:-1]
        angle_total = sum([prev.reverses().angle_to_other(this)
                           for prev, this in zip(preceding_edges, edges)])
        angle_total -= math.pi * (self.max_points - 2)
        return angle_total

    def intersection_with_polygon(self, other):
        # Do fast check to exclude ones which are well separated
        centre_this, radius_this = self.centre_and_max_radius()
        centre_other, radius_other = other.centre_and_max_radius()
        spacing = centre_this.distance_to(centre_other)
        if spacing - radius_this - radius_other > 0:
            return None
        # Add output candidates: points from A that are in B, and vice versa
        result_points = [p for p in self.points
                         if other.contains_point(p) and p not in other.points]
        result_points += [p for p in other.points
                          if self.contains_point(p) and p not in result_points]
        # Calculate all intersections of (extended) edges between A and B
        inters_ab = [gc_a.intersection_points_with_other(gc_b)
                     for gc_a in self.edge_gcs() for gc_b in other.edge_gcs()]
        # remove 'None' cases, leaving a list of antipode pairs
        inters_ab = [x for x in inters_ab if x is not None]
        # flatten the pairs to a single list of points
        inters_ab = [x for x in itertools.chain.from_iterable(inters_ab)]
        # Add any intersections which are: inside both, not already seen
        result_points += [p for p in inters_ab
                          if (p not in result_points
                              and self.contains_point(p)
                              and other.contains_point(p))]
        if len(result_points) < 3:
            return None
        else:
            # Convert this bundle of points into a new SphAcwConvexPolygon
            return SphAcwConvexPolygon(points=result_points)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__,
                               ', '.join([repr(p) for p in self.points]))

    def __str__(self):
        return 'SphPoly({})'.format(
            ', '.join([str(p) for p in self.points]))
