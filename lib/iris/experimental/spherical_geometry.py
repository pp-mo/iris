'''
Created on May 7, 2013

@author: itpp

Spherical gridcell area-overlap calculations.
'''

import itertools
import math
import numpy as np


def convert_latlon_to_xyz(lat, lon):
    z = math.sin(lat)
    cos_lat = math.cos(lat)
    x = cos_lat * math.cos(lon)
    y = cos_lat * math.sin(lon)
    return (x, y, z)


class ZeroPointLatlonError(ValueError):
    def __init__(self, *args, **kwargs):
        if not args:
            args = ['Point too close to zero for lat-lon conversion.']
        super(ZeroPointLatlonError, self).__init__(*args, **kwargs)


def convert_xyz_to_latlon(x, y, z):
    mod_sq = (x * x + y * y + z * z)
    if abs(mod_sq) < 1e-15:
        raise ZeroPointLatlonError()
    lat = math.asin(z / math.sqrt(mod_sq))
    lon = math.atan2(y, x)
    return (lat, lon)


class SphPoint(object):
    """ A 2d point on the unit sphere. """
    def __init__(self, lat_or_point, lon=None):
        if lon is None:
            lat, lon = lat_or_point.lat, lat_or_point.lon
        else:
            lat = lat_or_point
        self.lat = lat
        self.lon = lon
        self._p3d = None

    def as_xyz(self):
        if self._p3d is None:
            self._p3d = convert_latlon_to_xyz(self.lat, self.lon)
        return self._p3d

    def as_latlon(self):
        return (self.lat, self.lon)

    def copy(self):
        return SphPoint(self)

    def antipode(self):
        x, y, z = self.as_xyz()
        return SphPoint(*convert_xyz_to_latlon(-x, -y, -z))

    def __eq__(self, other):
        return np.allclose(self.as_xyz(), other.as_xyz(), rtol=1e-6, atol=1e-6)

    def __ne__(self, other):
        return not self.__eq__(other)

    def dot_product(self, other):
        other = sph_point(other)
        result = sum([a * b for a, b in zip(self.as_xyz(), other.as_xyz())])
        # Clip to valid range, so small errors don't break inverse-trig usage
        return max(-1.0, min(1.0, result))

    def cross_product(self, other):
        ax, ay, az = self.as_xyz()
        bx, by, bz = sph_point(other).as_xyz()
        x, y, z = ((ay * bz - az * by),
                   (az * bx - ax * bz),
                   (ax * by - ay * bx))
        return sph_point(convert_xyz_to_latlon(x, y, z))

    def __str__(self):
        def r2d(radians):
            return radians * 180.0 / math.pi
        return 'SphPoint({})'.format(self._ll_str())

    def __repr__(self):
        return '{}({!r}, {!r})'.format(self.__class__.__name__,
                                       self.lat, self.lon)

    def _ll_str(self):
        def r2d(radians):
            return radians * 180.0 / math.pi
        return '({:+06.1f}d, {:+06.1f}d)'.format(r2d(self.lat), r2d(self.lon))


def sph_point(point, in_degrees=False):
    """ Make (lat,lon) into SphPoint, or return SphPoint unchanged. """
    if hasattr(point, 'lat'):
        return point
    if len(point) != 2:
        raise ValueError('sph_point argument not a SphPoint. '
                         'Expected (lat, lon), got : {!r}'.format(point))
    if in_degrees:
        point = [x * math.pi/180.0 for x in point]
    return SphPoint(*point)


class SphGcSeg(object):
    """ A great circle line segment, from 'A' to 'B' on the unit sphere. """
    def __init__(self, point_a, point_b):
        self.point_a = sph_point(point_a)
        self.point_b = sph_point(point_b)
        self.pole = self.point_b.cross_product(self.point_a)
        self.colinear_tolerance = 1e-7

    def reverse(self):
        return SphGcSeg(self.point_b, self.point_a)

    def has_point_on_left_side(self, point):
        """
        Returns >0 (left), <1 (right) or =0.0 (close to the line).

        'self.colinear_tolerance' defines a tolerance zone near the line
        (i.e. 'nearly colinear'), where 0.0 is always returned.
        So the caller can use, for example. '>' or '>=' as required, which will
        automatically ignore 'small' values of the wrong sign.

        """
        dot = self.pole.dot_product(point)
        if abs(dot) < self.colinear_tolerance:
            return 0.0
        return -dot

    def _cos_angle_to_other(self, other):
        # Cosine of angle between self + other
        return self.pole.dot_product(other.pole)

    def _cos_angle_to_point(self, point):
        # cosine(angle from AB to AP), where P = given point
        if point == self.point_a:
            return 1.0
        seg2 = SphGcSeg(self.point_a, point)
        result = self._cos_angle_to_other(seg2)
        return result

    def angle_to_other(self, other):
        # Angle between self and another segment
        # NOTE: at present relies on dot product, so cannot resolve -ve angles.
        # As these are segments, not just GCs, this could be fixed.
        # The existing is sufficient for the area calculations, which is all
        # it's currently used for.
        return math.acos(self._cos_angle_to_other(other))

    def angle_to_point(self, point):
        # Angle from AB to AP
        result = math.acos(self._cos_angle_to_point(point))
        if abs(result) > 1e-7 and self.has_point_on_left_side(point) < 0.0:
            result = -result
        return result

    def intersection_points_with_other(self, other):
        # Return the (two) intersection points with the other segment.
        # N.B. returns None if the two are parallel
        try:
            point_a = self.pole.cross_product(other.pole)
        except ZeroPointLatlonError:
            return None
        point_b = point_a.antipode()
        return (point_a, point_b)

    def __repr__(self):
        return '{}({}, {})'.format(self.__class__.__name__,
                                   repr(self.point_a),
                                   repr(self.point_b))

    def __str__(self):
        return 'SphSeg({!s} -> {!s}, pole={!s}>'.format(
            self.point_a._ll_str(),
            self.point_b._ll_str(),
            self.pole._ll_str())


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


class SphAcwConvexPolygon(object):
    def __init__(self, points=[], in_degrees=False):
        self._set_points([sph_point(point, in_degrees=in_degrees)
                          for point in points])
        # Remove any initial duplicate points to allow initial AcwConvex check
        self._remove_duplicate_points()
        # Rationalise points as required to make them anticlockwise-convex
        self._make_anticlockwise_convex()

    def _set_points(self, points):
        # Assign to our points, check length and uncache edges
        self.points = points
        self._edges = None
        self.n_points = len(points)
        if self.n_points < 3:
            raise TooFewPointsForPolygonError()

    def _remove_duplicate_points(self):
        # Remove duplicate adjacent points so all angles can be calculated.
        # Only within current ordering: can still have duplicates elsewhere.
        points = self.points
        prev_points = [None] + points[:-1]
        points = [this for this, prev in zip(points, prev_points)
                  if prev is None or this != prev]
        self._set_points(points)

    def _is_anticlockwise_convex(self):
        # Check if our points are arranged in a convex anticlockwise chain.
        # To call this, must be able to calculate edges --> must have no
        # adjacent duplicated points.
        edges = self.edge_gcs()
        previous_edges = edges[-1:] + edges[:-1]
        return all([prev.has_point_on_left_side(this.point_b) >= 0.0
                    for this, prev in zip(edges, previous_edges)])

    def _make_anticlockwise_convex(self):
        # Reorder points if required to give anticlockwise convex.
        # Raise error if not possible.
        retrying = False
        while True:
            if self._is_anticlockwise_convex():
                return
            # Choose any-old edge as a reference for ordering the points
            edge0 = self.edge_gcs()[0]
            points = self.points
            # Calculate angles from reference edge to all other points
            angles = [edge0.angle_to_point(p) for p in points]
            # Find "rightmost" point of the rest and move it to [1] position
            ind_rightmost = 1 + np.argmin(angles[1:])
            points = [points[0], points[ind_rightmost]] + \
                points[1:ind_rightmost] + points[ind_rightmost+1:]
            # Make a new reference segment from new [0:1]
            if points[0] == points[1]:
                raise NonConvexPolygonError()
            edge0 = SphGcSeg(points[0], points[1])
            # Recalculate all angles relative to this
            angles = [edge0.angle_to_point(p) for p in points]
            eps = 1.0e-7
            max_valid_angle = math.pi + eps
            min_valid_angle = -eps
            # Check for all valid angles
            if any([a > max_valid_angle or a < min_valid_angle
                    for a in angles]):
                raise NonConvexPolygonError()
            # Sort all points into correct order
            points_and_angles = zip(points, angles)
            points_and_angles_sorted = sorted(points_and_angles,
                                              key=lambda p_and_a: p_and_a[1])
            new_points = [p_and_a[0] for p_and_a in points_and_angles_sorted]
            # Remove duplicates + repeat if there were any...
            self._set_points(new_points)
            self._remove_duplicate_points()
            if self.points == new_points:
                # No duplicates : should now be ok
                break
            # Reordering produced duplicate points -> retry whole thing.
            if retrying:
                # Should only ever happen once !
                raise Exception('Unexpected loop in polygon reordering.')
            retrying = True
        if not self._is_anticlockwise_convex():
            # Reordered, but still not in desired state
            raise NonConvexPolygonError()

    def edge_gcs(self):
        if self._edges is None:
            self._edges = [SphGcSeg(self.points[i], self.points[i+1])
                           for i in range(self.n_points - 1)]
            self._edges += [SphGcSeg(self.points[-1], self.points[0])]
        return self._edges

    def contains_point(self, point, in_degrees=False):
        point = sph_point(point, in_degrees=in_degrees)
        return all(gc.has_point_on_left_side(point) >= 0.0
                   for gc in self.edge_gcs())

    def area(self):
        angle_total = 0.0
        edges = self.edge_gcs()
        previous_edge = edges[-1]
        for this_edge in edges:
            a = previous_edge.reverse().angle_to_other(this_edge)
            angle_total += a
            previous_edge = this_edge
        angle_total -= math.pi * (self.n_points - 2)
        return angle_total

    def intersection_with_polygon(self, other):
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
