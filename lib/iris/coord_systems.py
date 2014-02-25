# (C) British Crown Copyright 2010 - 2013, Met Office
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
Definitions of coordinate systems.

"""

from __future__ import division
from abc import ABCMeta, abstractmethod
import numpy as np
import warnings

import cartopy.crs


class CoordSystem(object):
    """
    Abstract base class for coordinate systems.

    """
    __metaclass__ = ABCMeta

    grid_mapping_name = None

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        # Must supply __ne__, Python does not defer to __eq__ for
        # negative equality.
        return not (self == other)

    def xml_element(self, doc, attrs=None):
        """Default behaviour for coord systems."""
        # attrs - optional list of (k,v) items, used for alternate output

        xml_element_name = type(self).__name__
        # lower case the first char
        first_char = xml_element_name[0]
        xml_element_name = xml_element_name.replace(first_char,
                                                    first_char.lower(),
                                                    1)

        coord_system_xml_element = doc.createElement(xml_element_name)

        if attrs is None:
            attrs = self.__dict__.items()
        attrs.sort(key=lambda attr: attr[0])

        for name, value in attrs:
            coord_system_xml_element.setAttribute(name, str(value))

        return coord_system_xml_element

    @abstractmethod
    def as_cartopy_crs(self):
        """
        Return a cartopy CRS representing our native coordinate
        system.

        """
        pass

    @abstractmethod
    def as_cartopy_projection(self):
        """
        Return a cartopy projection representing our native map.

        This will be the same as the :func:`~CoordSystem.as_cartopy_crs` for
        map projections but for spherical coord systems (which are not map
        projections) we use a map projection, such as PlateCarree.

        """
        pass


class GeogCS(CoordSystem):
    """
    A geographic (ellipsoidal) coordinate system, defined by the shape of
    the Earth and a prime meridian.

    """

    grid_mapping_name = "latitude_longitude"

    def __init__(self, semi_major_axis=None, semi_minor_axis=None,
                 inverse_flattening=None, longitude_of_prime_meridian=0):
        """
        Creates a new GeogCS.

        Kwargs:

            * semi_major_axis              -  of ellipsoid in metres
            * semi_minor_axis              -  of ellipsoid in metres
            * inverse_flattening           -  of ellipsoid
            * longitude_of_prime_meridian  -  Can be used to specify the
                                              prime meridian on the ellipsoid
                                              in degrees. Default = 0.

        If just semi_major_axis is set, with no semi_minor_axis or
        inverse_flattening, then a perfect sphere is created from the given
        radius.

        If just two of semi_major_axis, semi_minor_axis, and
        inverse_flattening are given the missing element is calulated from the
        formula:
        :math:`flattening = (major - minor) / major`

        Currently, Iris will not allow over-specification (all three ellipsoid
        paramaters).
        Examples::

            cs = GeogCS(6371229)
            pp_cs = GeogCS(iris.fileformats.pp.EARTH_RADIUS)
            airy1830 = GeogCS(semi_major_axis=6377563.396,
                              semi_minor_axis=6356256.909)
            airy1830 = GeogCS(semi_major_axis=6377563.396,
                              inverse_flattening=299.3249646)
            custom_cs = GeogCS(6400000, 6300000)

        """
        # No ellipsoid specified? (0 0 0)
        if ((semi_major_axis is None) and (semi_minor_axis is None) and
                (inverse_flattening is None)):
            raise ValueError("No ellipsoid specified")

        # Ellipsoid over-specified? (1 1 1)
        if ((semi_major_axis is not None) and (semi_minor_axis is not None) and
                (inverse_flattening is not None)):
            raise ValueError("Ellipsoid is overspecified")

        # Perfect sphere (semi_major_axis only)? (1 0 0)
        elif (semi_major_axis is not None and (semi_minor_axis is None and
                                               inverse_flattening is None)):
            semi_minor_axis = semi_major_axis
            inverse_flattening = 0.0

        # Calculate semi_major_axis? (0 1 1)
        elif semi_major_axis is None and (semi_minor_axis is not None and
                                          inverse_flattening is not None):
            semi_major_axis = -semi_minor_axis / ((1.0 - inverse_flattening) /
                                                  inverse_flattening)

        # Calculate semi_minor_axis? (1 0 1)
        elif semi_minor_axis is None and (semi_major_axis is not None and
                                          inverse_flattening is not None):
            semi_minor_axis = semi_major_axis - ((1.0 / inverse_flattening) *
                                                 semi_major_axis)

        # Calculate inverse_flattening? (1 1 0)
        elif inverse_flattening is None and (semi_major_axis is not None and
                                             semi_minor_axis is not None):
            if semi_major_axis == semi_minor_axis:
                inverse_flattening = 0.0
            else:
                inverse_flattening = 1.0 / (
                    (semi_major_axis - semi_minor_axis) / semi_major_axis)

        # We didn't get enough to specify an ellipse.
        else:
            raise ValueError("Insufficient ellipsoid specification")

        #: Major radius of the ellipsoid in metres.
        self.semi_major_axis = float(semi_major_axis)

        #: Minor radius of the ellipsoid in metres.
        self.semi_minor_axis = float(semi_minor_axis)

        #: :math:`1/f` where :math:`f = (a-b)/a`
        self.inverse_flattening = float(inverse_flattening)

        #: Describes 'zero' on the ellipsoid in degrees.
        self.longitude_of_prime_meridian = float(longitude_of_prime_meridian)

    def _pretty_attrs(self):
        attrs = [("semi_major_axis", self.semi_major_axis)]
        if self.semi_major_axis != self.semi_minor_axis:
            attrs.append(("semi_minor_axis", self.semi_minor_axis))
        if self.longitude_of_prime_meridian != 0.0:
            attrs.append(("longitude_of_prime_meridian",
                          self.longitude_of_prime_meridian))
        return attrs

    def __repr__(self):
        attrs = self._pretty_attrs()
        # Special case for 1 pretty attr
        if len(attrs) == 1 and attrs[0][0] == "semi_major_axis":
            return "GeogCS(%r)" % self.semi_major_axis
        else:
            return "GeogCS(%s)" % ", ".join(
                ["%s=%r" % (k, v) for k, v in attrs])

    def __str__(self):
        attrs = self._pretty_attrs()
        # Special case for 1 pretty attr
        if len(attrs) == 1 and attrs[0][0] == "semi_major_axis":
            return "GeogCS(%s)" % self.semi_major_axis
        else:
            return "GeogCS(%s)" % ", ".join(
                ["%s=%s" % (k, v) for k, v in attrs])

    def xml_element(self, doc):
        # Special output for spheres
        attrs = self._pretty_attrs()
        if len(attrs) == 1 and attrs[0][0] == "semi_major_axis":
            attrs = [("earth_radius", self.semi_major_axis)]

        return CoordSystem.xml_element(self, doc, attrs)

    def as_cartopy_crs(self):
        return cartopy.crs.Geodetic(self.as_cartopy_globe())

    def as_cartopy_projection(self):
        return cartopy.crs.PlateCarree()

    def as_cartopy_globe(self):
        # Explicitly set `ellipse` to None as a workaround for
        # Cartopy setting WGS84 as the default.
        return cartopy.crs.Globe(semimajor_axis=self.semi_major_axis,
                                 semiminor_axis=self.semi_minor_axis,
                                 ellipse=None)


class RotatedGeogCS(CoordSystem):
    """
    A coordinate system with rotated pole, on an optional :class:`GeogCS`.

    """

    grid_mapping_name = "rotated_latitude_longitude"

    def __init__(self, grid_north_pole_latitude, grid_north_pole_longitude,
                 north_pole_grid_longitude=0, ellipsoid=None):
        """
        Constructs a coordinate system with rotated pole, on an
        optional :class:`GeogCS`.

        Args:

            * grid_north_pole_latitude  - The true latitude of the rotated
                                          pole in degrees.
            * grid_north_pole_longitude - The true longitude of the rotated
                                          pole in degrees.

        Kwargs:

            * north_pole_grid_longitude - Longitude of true north pole in
                                          rotated grid in degrees. Default = 0.
            * ellipsoid                 - Optional :class:`GeogCS` defining
                                          the ellipsoid.

        Examples::

            rotated_cs = RotatedGeogCS(30, 30)
            another_cs = RotatedGeogCS(30, 30,
                                       ellipsoid=GeogCS(6400000, 6300000))

        """
        #: The true latitude of the rotated pole in degrees.
        self.grid_north_pole_latitude = float(grid_north_pole_latitude)

        #: The true longitude of the rotated pole in degrees.
        self.grid_north_pole_longitude = float(grid_north_pole_longitude)

        #: Longitude of true north pole in rotated grid in degrees.
        self.north_pole_grid_longitude = float(north_pole_grid_longitude)

        #: Ellipsoid definition.
        self.ellipsoid = ellipsoid

    def _pretty_attrs(self):
        attrs = [("grid_north_pole_latitude", self.grid_north_pole_latitude),
                 ("grid_north_pole_longitude", self.grid_north_pole_longitude)]
        if self.north_pole_grid_longitude != 0.0:
            attrs.append(("north_pole_grid_longitude",
                          self.north_pole_grid_longitude))
        if self.ellipsoid is not None:
            attrs.append(("ellipsoid", self.ellipsoid))
        return attrs

    def __repr__(self):
        attrs = self._pretty_attrs()
        result = "RotatedGeogCS(%s)" % ", ".join(
            ["%s=%r" % (k, v) for k, v in attrs])
        # Extra prettiness
        result = result.replace("grid_north_pole_latitude=", "")
        result = result.replace("grid_north_pole_longitude=", "")
        return result

    def __str__(self):
        attrs = self._pretty_attrs()
        result = "RotatedGeogCS(%s)" % ", ".join(
            ["%s=%s" % (k, v) for k, v in attrs])
        # Extra prettiness
        result = result.replace("grid_north_pole_latitude=", "")
        result = result.replace("grid_north_pole_longitude=", "")
        return result

    def xml_element(self, doc):
        return CoordSystem.xml_element(self, doc, self._pretty_attrs())

    def as_cartopy_crs(self):
        return cartopy.crs.RotatedGeodetic(self.grid_north_pole_longitude,
                                           self.grid_north_pole_latitude)

    def as_cartopy_projection(self):
        return cartopy.crs.RotatedPole(self.grid_north_pole_longitude,
                                       self.grid_north_pole_latitude)


class TransverseMercator(CoordSystem):
    """
    A cylindrical map projection, with XY coordinates measured in metres.

    """

    grid_mapping_name = "transverse_mercator"

    def __init__(self, latitude_of_projection_origin,
                 longitude_of_central_meridian, false_easting, false_northing,
                 scale_factor_at_central_meridian, ellipsoid=None):
        """
        Constructs a TransverseMercator object.

        Args:

            * latitude_of_projection_origin
                    True latitude of planar origin in degrees.

            * longitude_of_central_meridian
                    True longitude of planar origin in degrees.

            * false_easting
                    X offset from planar origin in metres.

            * false_northing
                    Y offset from planar origin in metres.

            * scale_factor_at_central_meridian
                    Reduces the cylinder to slice through the ellipsoid
                    (secant form). Used to provide TWO longitudes of zero
                    distortion in the area of interest.

        Kwargs:

            * ellipsoid
                    Optional :class:`GeogCS` defining the ellipsoid.

        Example::

            airy1830 = GeogCS(6377563.396, 6356256.909)
            osgb = TransverseMercator(49, -2, 400000, -100000, 0.9996012717,
                                      ellipsoid=airy1830)

        """
        #: True latitude of planar origin in degrees.
        self.latitude_of_projection_origin = float(
            latitude_of_projection_origin)

        #: True longitude of planar origin in degrees.
        self.longitude_of_central_meridian = float(
            longitude_of_central_meridian)

        #: X offset from planar origin in metres.
        self.false_easting = float(false_easting)

        #: Y offset from planar origin in metres.
        self.false_northing = float(false_northing)

        #: Reduces the cylinder to slice through the ellipsoid (secant form).
        self.scale_factor_at_central_meridian = float(
            scale_factor_at_central_meridian)

        #: Ellipsoid definition.
        self.ellipsoid = ellipsoid

    def __repr__(self):
        return "TransverseMercator(latitude_of_projection_origin={!r}, "\
               "longitude_of_central_meridian={!r}, false_easting={!r}, "\
               "false_northing={!r}, scale_factor_at_central_meridian={!r}, "\
               "ellipsoid={!r})".format(self.latitude_of_projection_origin,
                                        self.longitude_of_central_meridian,
                                        self.false_easting,
                                        self.false_northing,
                                        self.scale_factor_at_central_meridian,
                                        self.ellipsoid)

    def as_cartopy_crs(self):
        if self.ellipsoid is not None:
            globe = self.ellipsoid.as_cartopy_globe()
        else:
            globe = None

        return cartopy.crs.TransverseMercator(
            central_longitude=self.longitude_of_central_meridian,
            central_latitude=self.latitude_of_projection_origin,
            false_easting=self.false_easting,
            false_northing=self.false_northing,
            scale_factor=self.scale_factor_at_central_meridian,
            globe=globe)

    def as_cartopy_projection(self):
        return self.as_cartopy_crs()


class OSGB(TransverseMercator):
    """A Specific transverse mercator projection on a specific ellipsoid."""
    def __init__(self):
        TransverseMercator.__init__(self, 49, -2, 400000, -100000,
                                    0.9996012717,
                                    GeogCS(6377563.396, 6356256.909))

    def as_cartopy_crs(self):
        return cartopy.crs.OSGB()

    def as_cartopy_projection(self):
        return cartopy.crs.OSGB()


class Stereographic(CoordSystem):
    """
    A stereographic map projection.

    """

    grid_mapping_name = "stereographic"

    def __init__(self, central_lat, central_lon,
                 false_easting=0.0, false_northing=0.0,
                 true_scale_lat=None, ellipsoid=None):
        """
        Constructs a Stereographic coord system.

        Args:

            * central_lat
                    The latitude of the pole.

            * central_lon
                    The central longitude, which aligns with the y axis.

            * false_easting
                    X offset from planar origin in metres. Defaults to 0.

            * false_northing
                    Y offset from planar origin in metres. Defaults to 0.

        Kwargs:

            * true_scale_lat
                    Latitude of true scale.

            * ellipsoid
                    :class:`GeogCS` defining the ellipsoid.

        """

        #: True latitude of planar origin in degrees.
        self.central_lat = float(central_lat)

        #: True longitude of planar origin in degrees.
        self.central_lon = float(central_lon)

        #: X offset from planar origin in metres.
        self.false_easting = float(false_easting)

        #: Y offset from planar origin in metres.
        self.false_northing = float(false_northing)

        #: Latitude of true scale.
        self.true_scale_lat = float(true_scale_lat) if true_scale_lat else None

        #: Ellipsoid definition.
        self.ellipsoid = ellipsoid

    def __repr__(self):
        return "Stereographic(central_lat={!r}, central_lon={!r}, "\
               "false_easting={!r}, false_northing={!r}, "\
               "true_scale_lat={!r}, "\
               "ellipsoid={!r})".format(self.central_lat, self.central_lon,
                                        self.false_easting,
                                        self.false_northing,
                                        self.true_scale_lat,
                                        self.ellipsoid)

    def as_cartopy_crs(self):
        if self.ellipsoid is not None:
            globe = self.ellipsoid.as_cartopy_globe()
        else:
            globe = cartopy.crs.Globe()
        return cartopy.crs.Stereographic(
            self.central_lat, self.central_lon,
            self.false_easting, self.false_northing,
            self.true_scale_lat, globe)

    def as_cartopy_projection(self):
        return self.as_cartopy_crs()


class LambertConformal(CoordSystem):
    """
    A coordinate system in the Lambert Conformal conic projection.

    """

    grid_mapping_name = "lambert_conformal"

    def __init__(self, central_lat=39.0, central_lon=-96.0,
                 false_easting=0.0, false_northing=0.0,
                 secant_latitudes=(33, 45), ellipsoid=None):
        """
        Constructs a LambertConformal coord system.

        Args:

            * central_lat
                    The latitude of "unitary scale".

            * central_lon
                    The central longitude.

            * false_easting
                    X offset from planar origin in metres.

            * false_northing
                    Y offset from planar origin in metres.

        Kwargs:

            * secant_latitudes
                    Latitudes of secant intersection.  One or two values.

            * ellipsoid
                    :class:`GeogCS` defining the ellipsoid.

        .. note:

            Default arguments are for the familiar USA map:
            central_lon=-96.0, central_lat=39.0,
            false_easting=0.0, false_northing=0.0,
            secant_latitudes=(33, 45)

        """
        # Convert standard parallels to a tuple-pair (from length 0, 1 or 2).
        # Produces a 2SP equivalent of 1SP form : Cartopy requires 2SP form.
        lats = np.array(secant_latitudes)
        if lats.ndim < 1:
            lats = (lats, lats)
        elif len(lats) < 2:
            lats = (lats[0], lats[0])
        secant_latitudes = (float(lats[0]), float(lats[1]))

        #: True latitude of planar origin in degrees.
        self.central_lat = central_lat
        #: True longitude of planar origin in degrees.
        self.central_lon = central_lon
        #: X offset from planar origin in metres.
        self.false_easting = false_easting
        #: Y offset from planar origin in metres.
        self.false_northing = false_northing
        #: Latitudes of secant intersection.
        self.secant_latitudes = secant_latitudes
        #: Ellipsoid definition.
        self.ellipsoid = ellipsoid

    def __repr__(self):
        return "LambertConformal(central_lat={!r}, central_lon={!r}, "\
               "false_easting={!r}, false_northing={!r}, "\
               "secant_latitudes={!r}, ellipsoid={!r})".format(
                   self.central_lat, self.central_lon,
                   self.false_easting, self.false_northing,
                   self.secant_latitudes, self.ellipsoid)

    def as_cartopy_crs(self):
        # We're either north or south polar. Set a cutoff accordingly.
        if self.secant_latitudes is not None:
            lats = self.secant_latitudes
            max_lat = lats[0] if abs(lats[0]) > abs(lats[1]) else lats[1]
            cutoff = -30 if max_lat > 0 else 30
        else:
            cutoff = None

        if self.ellipsoid is not None:
            globe = self.ellipsoid.as_cartopy_globe()
        else:
            globe = cartopy.crs.Globe()

        return cartopy.crs.LambertConformal(
            self.central_lon, self.central_lat,
            self.false_easting, self.false_northing,
            self.secant_latitudes, globe, cutoff)

    def as_cartopy_projection(self):
        return self.as_cartopy_crs()
