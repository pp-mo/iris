'''
Created on May 8, 2013

@author: itpp
'''
from iris import tests

import math

import numpy as np

import iris.util

import iris.experimental.spherical_geometry as sph


def spt(*args, **kwargs):
    # wrap sph.sph_point, but default to in_degrees=True
    in_degrees = kwargs.pop('in_degrees', True)
    kwargs['in_degrees'] = in_degrees
    return sph.sph_point(*args, **kwargs)


def d2r(degrees):
    return degrees / 180.0 * math.pi


def r2d(radians):
    return radians * 180.0 / math.pi


class TestConverts(tests.IrisTest):
    def test_convert_xyz_to_latlon(self):
        def _test_xyz_latlon(test_xyz, expect_latlon):
            result_latlon = sph.convert_xyz_to_latlon(*test_xyz)
            self.assertArrayAllClose(result_latlon, expect_latlon)

        _test_xyz_latlon((0, 0, 1), (d2r(90), 0.0))
        _test_xyz_latlon((0, 0, 0.01), (d2r(90), 0.0))
        _test_xyz_latlon((1, 0, 1.0), (d2r(45), 0.0))
        _test_xyz_latlon((-1, 0, 1.0), (d2r(45), d2r(180)))
        _test_xyz_latlon((1.0, 0, 0), (0.0, 0.0))
        _test_xyz_latlon((1.0, 1.0, 0), (0.0, d2r(45)))
        _test_xyz_latlon((1.0, -1.0, 0), (0.0, -d2r(45)))
        _test_xyz_latlon((-1.0, -1.0, 0), (0.0, -d2r(180 - 45)))
        _test_xyz_latlon((0.0, -1.0, 0), (0.0, -d2r(90)))
        _test_xyz_latlon((1, 1, -math.sqrt(2)), (-d2r(45), d2r(45)))
        _test_xyz_latlon((math.sqrt(1.5), math.sqrt(0.5), math.sqrt(2.0)),
                         (d2r(45), d2r(30)))

    def test_convert_latlon_to_xyz(self):
        def _test_latlon_xyz(test_latlon, expect_xyz):
            result_xyz = sph.convert_latlon_to_xyz(*test_latlon)
            self.assertArrayAllClose(result_xyz, expect_xyz, atol=1e-7)

        rv2 = 1.0 / math.sqrt(2)
        _test_latlon_xyz((d2r(90), 0.0), (0, 0, 1.0))
        _test_latlon_xyz((d2r(45), 0.0), (rv2, 0, rv2))
        _test_latlon_xyz((d2r(45), d2r(180)), (-rv2, 0, rv2))
        _test_latlon_xyz((0.0, 0.0), (1.0, 0, 0))
        _test_latlon_xyz((0.0, d2r(45)), (rv2, rv2, 0))
        _test_latlon_xyz((0.0, -d2r(45)), (rv2, -rv2, 0))
        _test_latlon_xyz((0.0, -d2r(180 - 45)), (-rv2, -rv2, 0))
        _test_latlon_xyz((0.0, -d2r(90)), (0.0, -1.0, 0))
        _test_latlon_xyz((-d2r(45), d2r(45)), (0.5, 0.5, -rv2))


class TestSphPoint(tests.IrisTest):
    def test_point_basic(self):
        pv4 = d2r(45)
        pv6 = d2r(180) / 6
        pt = sph.SphPoint(-pv4, pv6)
        self.assertEqual(pt.lat, -pv4)
        self.assertEqual(pt.lon, pv6)

        latlon = pt.as_latlon()
        self.assertArrayAllClose(latlon, (-pv4, pv6))

        xyz = pt.as_xyz()
        self.assertArrayAllClose(xyz, sph.convert_latlon_to_xyz(-pv4, pv6))

        pt2 = pt.copy()
        self.assertEqual(pt2, pt)
        self.assertIsNot(pt2, pt)

    def test_point_maker(self):
        pt = spt((45, 45))
        pv4 = d2r(45)
        self.assertArrayAllClose((pt.lat, pt.lon), (pv4, pv4))

    def test_point_antipode(self):
        pt2 = spt((45, 45))
        x1, y1, z1 = pt2.as_xyz()
        pt2a = pt2.antipode()
        x2, y2, z2 = pt2a.as_xyz()
        self.assertArrayAllClose((x2, y2, z2), (-x1, -y1, -z1))

    def test_points_dot_product(self):
        pt1 = spt((0, 60))
        pt2 = spt((0, 30))
        self.assertAlmostEqual(pt1.dot_product(pt2), math.sqrt(3.0/4))

        pt1 = spt((0, 60))
        pt2 = spt((90, 30))
        self.assertAlmostEqual(pt1.dot_product(pt2), 0.0)

        pt1 = spt((45, 60))
        pt2 = spt((-45, 60))
        self.assertAlmostEqual(pt1.dot_product(pt2), 0.0)

        pt1 = spt((45, 60))
        pt2 = spt((45, 60))
        self.assertAlmostEqual(pt1.dot_product(pt2), 1.0)

        pt1 = spt((45, 60))
        pt2 = spt((-45, 240))
        self.assertAlmostEqual(pt1.dot_product(pt2), -1.0)

    def test_points_cross_product(self):
        pt1 = spt((0, 30))
        pt2 = spt((0, 60))
        pt = pt1.cross_product(pt2)
        self.assertArrayAllClose(pt.as_latlon(), (d2r(90), 0))
        pt = pt2.cross_product(pt1)
        self.assertArrayAllClose(pt.as_latlon(), (-d2r(90), 0))

        pt1 = spt((0, 30))
        pt2 = spt((90, 60))
        pt = pt1.cross_product(pt2)
        px = spt((0, -60))
        self.assertArrayAllClose(pt.as_latlon(), px.as_latlon(), atol=1e-7)
        pt = pt2.cross_product(pt1)
        px = spt((0, 120))
        self.assertArrayAllClose(pt.as_latlon(), px.as_latlon(), atol=1e-7)

        pt1 = spt((45, 60))
        pt2 = spt((-45, 60))
        pt = pt1.cross_product(pt2)
        px = spt((0, 150))
        self.assertArrayAllClose(pt.as_latlon(), px.as_latlon(), atol=1e-7)
        pt = pt2.cross_product(pt1)
        px = spt((0, -30))
        self.assertArrayAllClose(pt.as_latlon(), px.as_latlon(), atol=1e-7)

        pt1 = spt((45, 60))
        pt2 = spt((45, 60))
        with self.assertRaises(ValueError):
            pt = pt1.cross_product(pt2)
        with self.assertRaises(ValueError):
            pt = pt2.cross_product(pt1)


class TestSphGcSeg(tests.IrisTest):
    def test_seg_basic(self):
        p1 = spt((0, 30))
        p2 = spt((0, 50))
        seg = sph.SphGcSeg(p1, p2)
        px = p2.cross_product(p1)
        self.assertArrayAllClose(seg.pole.as_xyz(), px.as_xyz())

    def test_seg_has_point_on_left(self):
        seg = sph.SphGcSeg(spt((0, 30)), spt((0, 50)))
        p3 = spt((-10, 70))
        self.assertFalse(seg.has_point_on_left_side(p3) > 0.0)
        p3 = spt((10, 70))
        self.assertTrue(seg.has_point_on_left_side(p3) > 0.0)

        # check _near_ co-linear
        p3 = spt((0.01, 70))
        self.assertTrue(seg.has_point_on_left_side(p3) > 0.0)

        # check points on the segment itself, and co-linear
        p3 = spt((0, 70))
        self.assertTrue(seg.has_point_on_left_side(p3) == 0.0)
        p3 = spt((0, 10))
        self.assertTrue(seg.has_point_on_left_side(p3) == 0.0)
        p3 = spt((0, 30))
        self.assertTrue(seg.has_point_on_left_side(p3) == 0.0)
        p3 = spt((0, 50))
        self.assertTrue(seg.has_point_on_left_side(p3) == 0.0)

        seg = sph.SphGcSeg(spt((45, 30)), spt((0, 50)))
        p3 = spt((0, 0))
        self.assertFalse(seg.has_point_on_left_side(p3) > 0.0)
        p3 = spt((0, 40))
        self.assertFalse(seg.has_point_on_left_side(p3) > 0.0)
        p3 = spt((50, 50))
        self.assertTrue(seg.has_point_on_left_side(p3) > 0.0)
        p3 = spt((90, 0))
        self.assertTrue(seg.has_point_on_left_side(p3) > 0.0)

    def test_seg_angle_to_other(self):
        seg1 = sph.SphGcSeg(spt((0, 30)), spt((0, 50)))
        seg2 = sph.SphGcSeg(spt((0, 30)), spt((90, 713)))
        a = seg1.angle_to_other(seg2)
        self.assertAlmostEqual(a, d2r(90))

        seg1 = sph.SphGcSeg(spt((20, 30)), spt((40, 50)))
        seg2 = sph.SphGcSeg(spt((20, 30)), spt((40, 50)))
        a = seg1.angle_to_other(seg2)
        self.assertAlmostEqual(a, 0.0)

        seg1 = sph.SphGcSeg(spt((20, 30)), spt((40, 50)))
        seg2 = sph.SphGcSeg(spt((40, 50)), spt((20, 30)))
        a = seg1.angle_to_other(seg2)
        self.assertAlmostEqual(a, d2r(180))

        show_relangle_debug = False
        if show_relangle_debug:
            print

        def _test_relangle(from_latlon=(0.0, 0.0), atol_degrees=1.0):
            # Test segments constructed at multiple angles to a base-point.
            # Very rough testing of relative angles
            # Basically, just test that results vary 'reasonably'.
            y0 = from_latlon[0]
            x0 = from_latlon[1]
            d_ang = 1.0
            seg1 = sph.SphGcSeg(spt((y0, x0)), spt((y0, x0 + d_ang)))
            results = []
            if show_relangle_debug:
                print
                print 'Test at={} tol={:5.1f}'.format(from_latlon,
                                                      atol_degrees)
            # NOTE: at present, does *not* work properly for 'negative' angles
            # so just test 0..180 for now
            for ang in np.linspace(0.0, +180.0, 9, endpoint=True):
                x = x0 + d_ang * math.cos(d2r(ang))
                y = y0 + d_ang * math.sin(d2r(ang))
                seg2 = sph.SphGcSeg(spt((y0, x0)), spt((y, x)))
                a = r2d(seg1.angle_to_other(seg2))
                if show_relangle_debug:
                    print 'at={} ang={:7.1f} --> {:7.1f}'.format(from_latlon,
                                                                 ang, a)
                if abs(abs(ang) - 180.0) > 0.1:
                    # Normal checks
                    results += [a]
                    ang_err = abs(a - ang)
                else:
                    # Special checks, not to fret about +/- 180
                    ang_err = abs(ang) - abs(a)
                self.assertLess(ang_err, atol_degrees)
            self.assertTrue(iris.util.monotonic(np.array(results),
                                                strict=True))

        # Do multiple angles test with different basepoints.
        _test_relangle((0, 0))
        _test_relangle((0, 70))
        _test_relangle((45, 45), atol_degrees=15.0)
        _test_relangle((80, 0), atol_degrees=55)
        _test_relangle((-65, 30), atol_degrees=25)

    def test_seg_angle_to_point(self):
        seg = sph.SphGcSeg(spt((0, 30)), spt((0, 50)))

        a = seg.angle_to_point(spt((0, 70)))
        self.assertAlmostEqual(a, 0.0)

        a = seg.angle_to_point(spt((90, 20)))
        self.assertAlmostEqual(a, d2r(90))

        a = seg.angle_to_point(spt((-90, 20)))
        self.assertAlmostEqual(a, d2r(-90))

        # check colinear 'behind' start point
        a = seg.angle_to_point(spt((0, -20)))
        self.assertAlmostEqual(a, d2r(180))

        # check same as far end
        a = seg.angle_to_point(spt((0, 50)))
        self.assertAlmostEqual(a, 0.0)

        # check same as near end
        a = seg.angle_to_point(spt((0, 30)))
        self.assertAlmostEqual(a, 0.0)

        a = seg.angle_to_point(spt((1, -20)))
        self.assertAlmostEqual(a, d2r(178.695), delta=d2r(0.005))
        a = seg.angle_to_point(spt((-1, -20)))
        self.assertAlmostEqual(a, d2r(-178.695), delta=d2r(0.005))

        a = seg.angle_to_point(spt((-20, 30)))
        self.assertAlmostEqual(a, d2r(-90))
        a = seg.angle_to_point(spt((1, 31)))
        self.assertAlmostEqual(a, d2r(45), delta=d2r(0.1))
        a = seg.angle_to_point(spt((-1, 31)))
        self.assertAlmostEqual(a, d2r(-45), delta=d2r(0.1))
        a = seg.angle_to_point(spt((-20, 50)))
        self.assertAlmostEqual(a, d2r(-46.7808), delta=d2r(0.005))
            # NOTE: this one not exact, because of cos scaling

        show_relangle_debug = False
        if show_relangle_debug:
            print

        def _test_relangle(from_latlon=(0.0, 0.0), atol_degrees=1.0):
            # Test with points offset at multiple angles from a segment base.
            # Very rough testing of relative angles
            # Basically, just test that results vary 'reasonably'.
            y0 = from_latlon[0]
            x0 = from_latlon[1]
            d_ang = 1.0
            seg1 = sph.SphGcSeg(spt((y0, x0)), spt((y0, x0 + d_ang)))
            results = []
            if show_relangle_debug:
                print
                print 'Test at={} tol={:5.1f}'.format(from_latlon,
                                                      atol_degrees)
            # NOTE: the point-angle function *does* work for negative angles
            for ang in np.linspace(-180.0, +180.0, 17, endpoint=True):
                x = x0 + d_ang * math.cos(d2r(ang))
                y = y0 + d_ang * math.sin(d2r(ang))
                point = spt((y, x))
                a = r2d(seg1.angle_to_point(point))
                if show_relangle_debug:
                    print 'at={} ang={:7.1f} --> {:7.1f}'.format(from_latlon,
                                                                 ang, a)
                if abs(abs(ang) - 180.0) > 0.1:
                    # Normal checks
                    results += [a]
                    ang_err = abs(a - ang)
                else:
                    # Special checks, not to fret about +/- 180
                    ang_err = abs(ang) - abs(a)
                self.assertLess(ang_err, atol_degrees)
            self.assertTrue(iris.util.monotonic(np.array(results),
                                                strict=True))

        # Test with point at various lat-lon offsets to a segment base point.
        _test_relangle((0, 0))
        _test_relangle((0, 70))
        _test_relangle((45, 45), atol_degrees=12.0)
        _test_relangle((80, 0), atol_degrees=55)
        _test_relangle((-65, 30), atol_degrees=25)

    def test_seg_intersection(self):
        seg1 = sph.SphGcSeg(spt((0, 30)), spt((0, 50)))
        seg2 = sph.SphGcSeg(spt((0, 30)), spt((60, 30)))
        pts = seg1.intersection_points_with_other(seg2)
        p1 = spt((0, 30))
        self.assertArrayAllClose(pts[0].as_latlon(), p1.as_latlon(),
                                 atol=1e-7)
        self.assertArrayAllClose(pts[1].as_latlon(), p1.antipode().as_latlon(),
                                 atol=1e-7)

        seg1 = sph.SphGcSeg(spt((0, 45)), spt((0, 50)))
        seg2 = sph.SphGcSeg(spt((50, 30)), spt((60, 30)))
        pts = seg1.intersection_points_with_other(seg2)
        p1 = spt((0, 30))
        self.assertArrayAllClose(pts[0].as_latlon(), p1.as_latlon(),
                                 atol=1e-7)
        self.assertArrayAllClose(pts[1].as_latlon(), p1.antipode().as_latlon(),
                                 atol=1e-7)

        seg1 = sph.SphGcSeg(spt((-30, 0)), spt((30, 100)))
        seg2 = sph.SphGcSeg(spt((20, -30)), spt((-20, 130)))
        pts = seg1.intersection_points_with_other(seg2)
        p1 = spt((0, 50))
        self.assertArrayAllClose(pts[1].as_latlon(), p1.as_latlon(),
                                 atol=1e-7)
        self.assertArrayAllClose(pts[0].as_latlon(), p1.antipode().as_latlon(),
                                 atol=1e-7)

        # intersect with self (or colinear) yields 'None'
        seg1 = sph.SphGcSeg(spt((0, 30)), spt((0, 50)))
        seg2 = sph.SphGcSeg(spt((0, 70)), spt((0, 80)))
        self.assertIsNone(seg1.intersection_points_with_other(seg1))
        self.assertIsNone(seg1.intersection_points_with_other(seg2))


class TestSphPolygon(tests.IrisTest):
    def test_polygon_create(self):
        points = [(0, 0), (0, 50), (50, 50)]
        poly = sph.SphAcwConvexPolygon(points, in_degrees=True)
        pts = [spt(p) for p in points]
        for i in range(len(pts)):
            self.assertEqual(poly.points[i], pts[i])

        # make it reversed : this forces it to correct the order
        poly = sph.SphAcwConvexPolygon(points[::-1], in_degrees=True)
        self.assertEqual(poly.points[0], pts[2])
        self.assertEqual(poly.points[1], pts[0])
        self.assertEqual(poly.points[2], pts[1])

        # check fails on two points
        points = [(0, 0), (0, 50)]
        with self.assertRaises(ValueError):
            poly = sph.SphAcwConvexPolygon(points, in_degrees=True)

        # make a square-ish one
        points = [(0, 0), (0, 50), (40, 50), (60, -10)]
        poly = sph.SphAcwConvexPolygon(points, in_degrees=True)
        pts = [spt(p) for p in points]
        for i in range(len(pts)):
            self.assertEqual(poly.points[i], pts[i])

        # check it is ok to have the odd point out of order
        points = [(0, 0), (0, 50), (40, 50), (60, -10), (15, 55)]
        poly = sph.SphAcwConvexPolygon(points, in_degrees=True)
        pts = [spt(p) for p in points]
        self.assertEqual(poly.points[0], pts[0])
        self.assertEqual(poly.points[1], pts[1])
        self.assertEqual(poly.points[2], pts[4])
        self.assertEqual(poly.points[3], pts[2])
        self.assertEqual(poly.points[4], pts[3])

        # check still ok if the first two points will no longer be adjacent
        points = [(0, 0), (0, 50), (40, 50), (70, -10), (-20, 30)]
        pts = [spt(p) for p in points]
        poly = sph.SphAcwConvexPolygon(points, in_degrees=True)
        self.assertEqual(poly.points[0], pts[0])
        self.assertEqual(poly.points[1], pts[4])
        self.assertEqual(poly.points[2], pts[1])
        self.assertEqual(poly.points[3], pts[2])
        self.assertEqual(poly.points[4], pts[3])

        # testcase for unsuitable points (non-convex)
        # Whereas this is ok..
        points = [(0, 0), (-5, 20), (0, 50), (40, 50), (70, -10)]
        poly = sph.SphAcwConvexPolygon(points, in_degrees=True)
        pts = [spt(p) for p in points]
        for i in range(len(pts)):
            self.assertEqual(poly.points[i], pts[i])

        # ..a slightly adjusted point#1 (concave between 0+2) means it is not
        points[1] = (5, 20)
        with self.assertRaises(ValueError):
            poly = sph.SphAcwConvexPolygon(points, in_degrees=True)

    def test_polygon_contains_point(self):
        # make a square-ish one
        points = [(0, 0), (0, 50), (40, 50), (60, -10)]
        poly = sph.SphAcwConvexPolygon(points, in_degrees=True)

        # test against all own points...
        pts = [spt(p) for p in points]
        for test_pt in pts:
            self.assertTrue(poly.contains_point(test_pt))

        # test others, within and without..
        self.assertEqual(poly.contains_point(spt((20, 20))), True)
        self.assertEqual(poly.contains_point(spt((1, 1))), True)
        self.assertEqual(poly.contains_point(spt((1, -1))), False)
        self.assertEqual(poly.contains_point(spt((-1, 1))), False)
        self.assertEqual(poly.contains_point(spt((1, 30))), True)
        self.assertEqual(poly.contains_point(spt((-1, 30))), False)
        self.assertEqual(poly.contains_point(spt((1, 49))), True)
        self.assertEqual(poly.contains_point(spt((-1, 49))), False)
        self.assertEqual(poly.contains_point(spt((39, 49))), True)
        self.assertEqual(poly.contains_point(spt((50, 25))), True)
        self.assertEqual(poly.contains_point(spt((60, 25))), False)

        self.assertEqual(poly.contains_point(spt((50, -5))), True)
        self.assertEqual(poly.contains_point(spt((5, -5))), False)

        # test others, that should be outside
        for lon in [-180, -20, 0, 25, 50, 100, 180]:
            self.assertEqual(poly.contains_point(spt((-80, lon))), False)
            self.assertEqual(poly.contains_point(spt((80, lon))), False)

        for lat in [-90, -20, 0, 25, 50, 65, 90]:
            self.assertEqual(poly.contains_point(spt((lat, -100))), False)
            self.assertEqual(poly.contains_point(spt((lat, 100))), False)

    def test_polygon_area(self):
        # basic quarter-hemisphere = pi/2
        points = [(0, 0), (0, 90), (90, 0)]
        poly = sph.SphAcwConvexPolygon(points, in_degrees=True)
        self.assertAlmostEqual(poly.area(), math.pi / 2)

        # half of quarter-hemisphere = pi/4
        points = [(0, 0), (0, 45), (90, 0)]
        poly = sph.SphAcwConvexPolygon(points, in_degrees=True)
        a = poly.area()
        self.assertAlmostEqual(poly.area(), math.pi / 4)

        # other half of quarter-hemisphere = pi/4
        points = [(0, 45), (0, 90), (90, 0)]
        poly = sph.SphAcwConvexPolygon(points, in_degrees=True)
        a = poly.area()
        self.assertAlmostEqual(poly.area(), math.pi / 4)

        # small square approximations
        def _test_small_square(y0, x0, d=1.0, rtol=1e-7):
            points = [(y0, x0),
                      (y0, x0 + d),
                      (y0 + d, x0 + d),
                      (y0 + d, x0)]
            a_expect = d2r(d) * d2r(d) * math.cos(d2r(y0 + 0.5 * d))
            delta = a_expect * rtol
            poly = sph.SphAcwConvexPolygon(points, in_degrees=True)
            a = poly.area()
            if abs(a - a_expect) > delta:
                str = ('\nTolerance failure: '
                       '_test_small_square(y={},x={},d={},rtol={}):'
                       '\n  -> rdiff = {:3.2e}'.format(
                           y0, x0, d, rtol, abs(a - a_expect) / a_expect))
                print str
            self.assertAlmostEqual(poly.area(), a_expect, delta=delta)

        _test_small_square(0, 0, rtol=2e-5)
        _test_small_square(20, 20, rtol=5e-6)
        _test_small_square(70, -50, rtol=1e-4)
        _test_small_square(-85, 50, rtol=1e-4)
        _test_small_square(20, 20, 15, rtol=1e-3)
        _test_small_square(20, 20, 35, rtol=0.02)

    def test_polygon_intersection(self):
        # test intersect with self = self
        # make a square-ish one
        points = [(0, 0), (0, 50), (40, 50), (60, -10)]
        poly = sph.SphAcwConvexPolygon(points, in_degrees=True)
        poly2 = poly.intersection_with_polygon(poly)
        self.assertTrue(all([p1 == p2 for p1, p2 in zip(poly.points,
                                                        poly2.points)]))

        # check on a misses-altogether case
        points1 = [(0, 0), (0, 40), (20, 20)]
        points2 = [(20, 21), (0, 41), (10, 50)]
        poly1 = sph.SphAcwConvexPolygon(points1, in_degrees=True)
        poly2 = sph.SphAcwConvexPolygon(points2, in_degrees=True)
        poly3 = poly1.intersection_with_polygon(poly2)
        self.assertIsNone(poly3)

        # what happens when 2 touch at an edge ?
        points1 = [(0, 0), (0, 40), (40, 40)]
        points2 = [(0, 40), (40, 40), (10, 50)]
        poly1 = sph.SphAcwConvexPolygon(points1, in_degrees=True)
        poly2 = sph.SphAcwConvexPolygon(points2, in_degrees=True)
        poly3 = poly1.intersection_with_polygon(poly2)
        self.assertIsNone(poly3)

        def poly_has_point_near(poly, latlon, tolerance_degrees=0.5):
            y, x = latlon
            d = tolerance_degrees / 2
            points = [(y - d, x - d),
                      (y - d, x + d),
                      (y + d, x + d),
                      (y + d, x - d)]
            box = sph.SphAcwConvexPolygon(points, in_degrees=True)
            hits = [box.contains_point(p) for p in poly.points]
            result = any(hits)
            if not result:
                print 'FAIL:'
                print 'poly = ', ', '.join([p._ll_str() for p in poly.points])
                print 'box = ', ', '.join([p._ll_str() for p in box.points])
            return result

        # test a simple intersection case
        points1 = [(10, 0), (10, 30), (20, 30), (20, 0)]
        points2 = [(0, 10), (0, 20), (30, 20), (30, 10)]
        poly1 = sph.SphAcwConvexPolygon(points1, in_degrees=True)
        poly2 = sph.SphAcwConvexPolygon(points2, in_degrees=True)
        poly3 = poly1.intersection_with_polygon(poly2)
        self.assertEqual(poly3.n_points, 4)
        tol_d = 1.5
        self.assertTrue(poly_has_point_near(poly3, (10, 10), tol_d))
        self.assertTrue(poly_has_point_near(poly3, (10, 20), tol_d))
        self.assertTrue(poly_has_point_near(poly3, (20, 20), tol_d))
        self.assertTrue(poly_has_point_near(poly3, (20, 10), tol_d))

        # more complex case : diamond X square --> octagon...
        points1 = [(-15, -15), (-15, 15), (15, 15), (15, -15)]
        points2 = [(-20, 0), (0, 20), (20, 0), (0, -20)]
        poly1 = sph.SphAcwConvexPolygon(points1, in_degrees=True)
        poly2 = sph.SphAcwConvexPolygon(points2, in_degrees=True)
        poly3 = poly1.intersection_with_polygon(poly2)
        self.assertEqual(poly3.n_points, 8)
        tol_d = 1.5
        self.assertTrue(poly_has_point_near(poly3, (-5, 15), tol_d))
        self.assertTrue(poly_has_point_near(poly3, (5, 15), tol_d))
        self.assertTrue(poly_has_point_near(poly3, (15, 5), tol_d))
        self.assertTrue(poly_has_point_near(poly3, (15, -5), tol_d))
        self.assertTrue(poly_has_point_near(poly3, (5, -15), tol_d))
        self.assertTrue(poly_has_point_near(poly3, (-5, -15), tol_d))
        self.assertTrue(poly_has_point_near(poly3, (-15, -5), tol_d))
        self.assertTrue(poly_has_point_near(poly3, (-15, 5), tol_d))


if __name__ == '__main__':
    tests.main()
