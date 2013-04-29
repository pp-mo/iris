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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Iris. If not, see <http://www.gnu.org/licenses/>.

# DO NOT EDIT: AUTO-GENERATED TRANSLATIONS


import collections

#
# PP OUTSTANDING PROBLEMS, CHANGES + NOTES ....
#   * CAPE had 'Kg', which udunits rejects (wants lowercase "kg")
#   * dewpoint was missing from both Grib1 and Grib2
#   * "grib_physical _atmosphere_albedo" name had a space in it
#   * ALBEDO in Grib2 should be a *percentage* (though fraction in Grib1 cases)
#   * why air_temperature is in "kelvin" not "K" ?
#   * Why do G1Lparam and G2param contain an "edition" attribute ?
#     -- surely this is already implied in the name?
#
# NOTE: have only edited the parts *used* for the climate-means project
# i.e. GRIB1Local_TO_CF  and  CF_TO_GRIB2
# other parts are now inconsistent
#

G2param = collections.namedtuple('G2param', ['edition', 'discipline',
                                             'category', 'number'])
G1Lparam = collections.namedtuple('G1Lparam', ['edition', 't2version', 'centre',
                                               'iParam'])
DimensionCoordinate = collections.namedtuple('DimensionCoordinate',
                                            ['standard_name', 'units', 'points'])

CFname = collections.namedtuple('CFname', ['standard_name', 'long_name',
                                           'unit'])

GRIB1Local_TO_CF = {
	G1Lparam(1, 128, 98, 129): CFname("geopotential", None, "m2 s-2"),
	G1Lparam(1, 128, 98, 130): CFname("air_temperature", None, "K"),
	G1Lparam(1, 128, 98, 131): CFname("x_wind", None, "m s-1"),
	G1Lparam(1, 128, 98, 132): CFname("y_wind", None, "m s-1"),
	G1Lparam(1, 128, 98, 135): CFname("lagrangian_tendency_of_air_pressure", None, "Pa s-1"),
	G1Lparam(1, 128, 98, 141): CFname("thickness_of_snowfall_amount", None, "m"),
	G1Lparam(1, 128, 98, 151): CFname("air_pressure_at_sea_level", None, "Pa"),
	G1Lparam(1, 128, 98, 157): CFname("relative_humidity", None, "%"),
	G1Lparam(1, 128, 98, 164): CFname("cloud_area_fraction", None, 1),
	G1Lparam(1, 128, 98, 173): CFname("surface_roughness_length", None, "m"),
	G1Lparam(1, 128, 98, 174): CFname(None, "grib_physical_atmosphere_albedo", 1),
	G1Lparam(1, 128, 98, 186): CFname("low_type_cloud_area_fraction", None, 1),
	G1Lparam(1, 128, 98, 187): CFname("medium_type_cloud_area_fraction", None, 1),
	G1Lparam(1, 128, 98, 188): CFname("high_type_cloud_area_fraction", None, 1),
	G1Lparam(1, 128, 98, 235): CFname(None, "grib_skin_temperature", "K"),
	G1Lparam(1, 128, 98, 31): CFname("sea_ice_area_fraction", None, 1),
	G1Lparam(1, 128, 98, 34): CFname("sea_surface_temperature", None, "K"),
	G1Lparam(1, 128, 98, 59): CFname("atmosphere_specific_convective_available_potential_energy", None, "J kg-1"),
	}

GRIB1LocalConstrained_TO_CF = {
	G1Lparam(1, 128, 98, 165): (CFname("x_wind", None, "m s-1"), DimensionCoordinate("height", "m", (10,))),
	G1Lparam(1, 128, 98, 166): (CFname("y_wind", None, "m s-1"), DimensionCoordinate("height", "m", (10,))),
    G1Lparam(1, 128, 98, 167): (CFname("air_temperature", None, "K"), DimensionCoordinate("height", "m", (2,))),
    G1Lparam(1, 128, 98, 168): (CFname("dew_point_temperature", None, "K"), DimensionCoordinate("height", "m", (2,))),
	}

GRIB2_TO_CF = {
	G2param(2, 0, 0, 0): CFname("air_temperature", None, "K"),
	G2param(2, 0, 0, 17): CFname(None, "grib_skin_temperature", "K"),
	G2param(2, 0, 0, 2): CFname("air_potential_temperature", None, "K"),
	G2param(2, 0, 1, 0): CFname("specific_humidity", None, "kg kg-1"),
	G2param(2, 0, 1, 1): CFname("relative_humidity", None, "%"),
	G2param(2, 0, 1, 11): CFname("thickness_of_snowfall_amount", None, "m"),
	G2param(2, 0, 1, 13): CFname("liquid_water_content_of_surface_snow", None, "kg m-2"),
	G2param(2, 0, 1, 22): CFname(None, "cloud_mixing_ratio", "kg kg-1"),
	G2param(2, 0, 1, 3): CFname(None, "precipitable_water", "kg m-2"),
	G2param(2, 0, 14, 0): CFname("atmosphere_mole_content_of_ozone", None, "Dobson"),
	G2param(2, 0, 19, 1): CFname(None, "grib_physical_atmosphere_albedo", 1),
	G2param(2, 0, 2, 1): CFname("wind_speed", None, "m s-1"),
	G2param(2, 0, 2, 10): CFname("atmosphere_absolute_vorticity", None, "s-1"),
	G2param(2, 0, 2, 2): CFname("x_wind", None, "m s-1"),
	G2param(2, 0, 2, 3): CFname("y_wind", None, "m s-1"),
	G2param(2, 0, 2, 8): CFname("lagrangian_tendency_of_air_pressure", None, "Pa s-1"),
	G2param(2, 0, 3, 0): CFname("air_pressure", None, "Pa"),
	G2param(2, 0, 3, 1): CFname("air_pressure_at_sea_level", None, "Pa"),
	G2param(2, 0, 3, 3): CFname(None, "icao_standard_atmosphere_reference_height", "m"),
	G2param(2, 0, 3, 4): CFname("geopotential", None, "m2 s-2"),
	G2param(2, 0, 3, 5): CFname("geopotential_height", None, "m"),
	G2param(2, 0, 3, 9): CFname("geopotential_height_anomaly", None, "m"),
	G2param(2, 0, 6, 1): CFname("cloud_area_fraction", None, "%"),
	G2param(2, 0, 6, 3): CFname("low_type_cloud_area_fraction", None, "%"),
	G2param(2, 0, 6, 4): CFname("medium_type_cloud_area_fraction", None, "%"),
	G2param(2, 0, 6, 5): CFname("high_type_cloud_area_fraction", None, "%"),
	G2param(2, 0, 6, 6): CFname("atmosphere_mass_content_of_cloud_liquid_water", None, "kg m-2"),
	G2param(2, 0, 6, 7): CFname("cloud_area_fraction_in_atmosphere_layer", None, "%"),
	G2param(2, 0, 7, 6): CFname("atmosphere_specific_convective_available_potential_energy", None, "J kg-1"),
	G2param(2, 0, 7, 7): CFname(None, "convective_inhibition", "J kg-1"),
	G2param(2, 0, 7, 8): CFname(None, "storm_relative_helicity", "J kg-1"),
	G2param(2, 10, 2, 0): CFname("sea_ice_area_fraction", None, 1),
	G2param(2, 10, 3, 0): CFname("sea_surface_temperature", None, "K"),
	G2param(2, 2, 0, 0): CFname("land_area_fraction", None, 1),
	G2param(2, 2, 0, 1): CFname("surface_roughness_length", None, "m"),
	}

CF_TO_GRIB1Local = {
	CFname("air_pressure_at_sea_level", None, "Pa"):G1Lparam(1, 128, 98, 151),
	CFname("air_temperature", None, "K"):G1Lparam(1, 128, 98, 130),
	CFname("atmosphere_specific_convective_available_potential_energy", None, "J Kg-1"):G1Lparam(1, 128, 98, 59),
	CFname("cloud_area_fraction", None, 1):G1Lparam(1, 128, 98, 164),
	CFname("geopotential", None, "m2 s-2"):G1Lparam(1, 128, 98, 129),
	CFname("high_type_cloud_area_fraction", None, 1):G1Lparam(1, 128, 98, 188),
	CFname("lagrangian_tendency_of_air_pressure", None, "Pa s-1"):G1Lparam(1, 128, 98, 135),
	CFname("low_type_cloud_area_fraction", None, 1):G1Lparam(1, 128, 98, 186),
	CFname("medium_type_cloud_area_fraction", None, 1):G1Lparam(1, 128, 98, 187),
	CFname("relative_humidity", None, "%"):G1Lparam(1, 128, 98, 157),
	CFname("sea_ice_area_fraction", None, 1):G1Lparam(1, 128, 98, 31),
	CFname("sea_surface_temperature", None, "K"):G1Lparam(1, 128, 98, 34),
	CFname("surface_roughness_length", None, "m"):G1Lparam(1, 128, 98, 173),
	CFname("thickness_of_snowfall_amount", None, "m"):G1Lparam(1, 128, 98, 141),
	CFname("x_wind", None, "m s-1"):G1Lparam(1, 128, 98, 131),
	CFname("y_wind", None, "m s-1"):G1Lparam(1, 128, 98, 132),
	CFname(None, "grib_physical_atmosphere_albedo", 1):G1Lparam(1, 128, 98, 174),
	CFname(None, "grib_skin_temperature", "K"):G1Lparam(1, 128, 98, 235),
	}

CFConstrained_TO_GRIB1Local = {
(CFname("air_temperature", None, "K"), DimensionCoordinate("height", "m", (2,))): G1Lparam(1, 128, 98, 167),
(CFname("x_wind", None, "m s-1"), DimensionCoordinate("height", "m", (10,))): G1Lparam(1, 128, 98, 165),
(CFname("y_wind", None, "m s-1"), DimensionCoordinate("height", "m", (10,))): G1Lparam(1, 128, 98, 166),
	}

CF_TO_GRIB2 = {	CFname("x_wind", None, "m s-1"):G2param(2, 0, 2, 2),
 
 	CFname("air_potential_temperature", None, "K"):G2param(2, 0, 0, 2),
 	CFname("air_pressure", None, "Pa"):G2param(2, 0, 3, 0),
 	CFname("air_pressure_at_sea_level", None, "Pa"):G2param(2, 0, 3, 1),
 	CFname("air_temperature", None, "K"):G2param(2, 0, 0, 0),
 	CFname("atmosphere_absolute_vorticity", None, "s-1"):G2param(2, 0, 2, 10),
 	CFname("atmosphere_mass_content_of_cloud_liquid_water", None, "kg m-2"):G2param(2, 0, 6, 6),
 	CFname("atmosphere_mole_content_of_ozone", None, "Dobson"):G2param(2, 0, 14, 0),
 	CFname("atmosphere_specific_convective_available_potential_energy", None, "J kg-1"):G2param(2, 0, 7, 6),
 	CFname("cloud_area_fraction", None, "%"):G2param(2, 0, 6, 1),
 	CFname("cloud_area_fraction_in_atmosphere_layer", None, "%"):G2param(2, 0, 6, 7),
 	CFname("geopotential", None, "m2 s-2"):G2param(2, 0, 3, 4),
 	CFname("geopotential_height", None, "m"):G2param(2, 0, 3, 5),
 	CFname("geopotential_height_anomaly", None, "m"):G2param(2, 0, 3, 9),
 	CFname("high_type_cloud_area_fraction", None, "%"):G2param(2, 0, 6, 5),
 	CFname("lagrangian_tendency_of_air_pressure", None, "Pa s-1"):G2param(2, 0, 2, 8),
 	CFname("land_area_fraction", None, 1):G2param(2, 2, 0, 0),
 	CFname("liquid_water_content_of_surface_snow", None, "kg m-2"):G2param(2, 0, 1, 13),
 	CFname("low_type_cloud_area_fraction", None, "%"):G2param(2, 0, 6, 3),
 	CFname("medium_type_cloud_area_fraction", None, "%"):G2param(2, 0, 6, 4),
 	CFname("relative_humidity", None, "%"):G2param(2, 0, 1, 1),
 	CFname("sea_ice_area_fraction", None, 1):G2param(2, 10, 2, 0),
 	CFname("sea_surface_temperature", None, "K"):G2param(2, 10, 3, 0),
 	CFname("specific_humidity", None, "kg kg-1"):G2param(2, 0, 1, 0),
 	CFname("surface_roughness_length", None, "m"):G2param(2, 2, 0, 1),
 	CFname("thickness_of_snowfall_amount", None, "m"):G2param(2, 0, 1, 11),
 	CFname("wind_speed", None, "m s-1"):G2param(2, 0, 2, 1),
 	CFname("y_wind", None, "m s-1"):G2param(2, 0, 2, 3),
 	CFname(None, "cloud_mixing_ratio", "kg kg-1"):G2param(2, 0, 1, 22),
 	CFname(None, "convective_inhibition", "J kg-1"):G2param(2, 0, 7, 7),
 	CFname(None, "grib_physical_atmosphere_albedo", "%"):G2param(2, 0, 19, 1),
 	CFname(None, "grib_skin_temperature", "K"):G2param(2, 0, 0, 17),
 	CFname(None, "icao_standard_atmosphere_reference_height", "m"):G2param(2, 0, 3, 3),
 	CFname(None, "precipitable_water", "kg m-2"):G2param(2, 0, 1, 3),
 	CFname(None, "storm_relative_helicity", "J kg-1"):G2param(2, 0, 7, 8),
    CFname("dew_point_temperature", None, "K"):G2param(2, 0, 0, 6),
	}
