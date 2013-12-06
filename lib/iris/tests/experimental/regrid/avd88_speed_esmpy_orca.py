#
#    Original ticket notes...
#
#    User Story:
#        As a scientific programmer I would like to resample my high resolution ORCA
#        data to a low resolution Atmosphere grid (on the same CRS).
#        The result for each atmosphere cell will be the area weighted mean of all the
#        ORCA cells partially or fully contained within an atmosphere cell,
#        each weighted by the partial area of that ORCA cell contained
#        within the relevant atmosphere cell.
#
#    Rationale:
#        This will enable simplified comparison analysis of Ocean data sets to suitable
#        atmosphere data sets: an important type of analysis for coupling models.
#
#    Acceptance Criteria:
#        Given the sample data:
#            """
#            ORCA 1/4 NEMO grid:
#            source_cube=iris.load_cube('/project/hadgem3/data/xexoc/ony/xexoc_1996_2005_grid_T.nc_nc3','Net Downward Heat Flux')
#
#            atm N96 grid:
#            tot_ed=iris.load_cube('/data/cr2/hadpd/southern_oc_heat_fluxes/net_heat_flux_edwards_method_ann.pp')
#            """
#        a Cube will be created using the atmosphere horizontal spatial domain
#        with data calculated from the ORCA data set.
#

import numpy as np

import cartopy.crs as ccrs

import iris
import iris.fileformats.pp

from iris.experimental.regrid_conservative import regrid_conservative_via_esmpy

from timed_block import TimedBlock

#with TimedBlock() as timer:
#    q = np.random.normal(size=1e4)
#
#print 'took : ', timer.seconds()

import iris

do_real_data = True
if do_real_data:
    source_cube = iris.load_cube('/project/hadgem3/data/xexoc/ony/xexoc_1996_2005_grid_T.nc_nc3','Net Downward Heat Flux')
    # Convert Time*1 vector dim to scalar, as regrid requires 2d field...
    source_cube = source_cube[0]

    cs_ll = iris.coord_systems.GeogCS(iris.fileformats.pp.EARTH_RADIUS)
    source_cube.coord('latitude').coord_system = cs_ll
    source_cube.coord('longitude').coord_system = cs_ll

    grid_cube = iris.load_cube('/data/cr2/hadpd/southern_oc_heat_fluxes/net_heat_flux_edwards_method_ann.pp')

#
# ?not working?
# gives ESMF error
# can't work out why not
#
#    do_little_part = False
#    if do_little_part:
#        source_cube = source_cube[40:43, 40:44]
#        grid_cube = grid_cube[20:22, 20:23]
else:
    # make some fake testing data
    cs_llrot_ellipse = iris.coord_systems.GeogCS(iris.fileformats.pp.EARTH_RADIUS)
    cs_llrot = iris.coord_systems.RotatedGeogCS(grid_north_pole_latitude=45.0,
                                                grid_north_pole_longitude=45.0,
                                                ellipsoid=cs_llrot_ellipse)
    nx_src, ny_src = 4, 3
    data = np.arange(12, dtype=float).reshape((3,4))
    source_cube = iris.cube.Cube(data)
    rx_coord = iris.coords.DimCoord.from_regular(zeroth=20.0,
                                                 step=2.0,
                                                 count=nx_src,
                                                 standard_name='grid_longitude',
                                                 units='degrees',
                                                 coord_system=cs_llrot)
    ry_coord = iris.coords.DimCoord.from_regular(zeroth=10.0,
                                                 step=3.0,
                                                 count=ny_src,
                                                 standard_name='grid_latitude',
                                                 units='degrees',
                                                 coord_system=cs_llrot)
    source_cube.add_dim_coord(ry_coord, 0)
    source_cube.add_dim_coord(rx_coord, 1)

    # work out true-latlon extent that this covers + construct a containing box
    crs_pc = ccrs.PlateCarree()
    x_rot = rx_coord.points
    y_rot = ry_coord.points
    x_rot, y_rot = np.broadcast_arrays(x_rot[None, :], y_rot[:, None])
    ll_values = crs_pc.transform_points(cs_llrot.as_cartopy_crs(), x_rot, y_rot)
    x_truelon, y_truelat = ll_values[..., 0], ll_values[..., 1]
    lon_min, lon_max = np.floor(np.min(x_truelon)), np.ceil(np.max(x_truelon))
    lat_min, lat_max = np.floor(np.min(y_truelat)), np.ceil(np.max(y_truelat))

    # construct an appropriate target grid that covers the rotated data
    nx_dst, ny_dst = 6, 5
    d_lon = (lon_max - lon_min) / (nx_dst - 1)
    d_lat = (lat_max - lat_min) / (ny_dst - 1)
    lon_0 = lon_min
    lat_0 = lat_min
    grid_cube

gridded_result = regrid_conservative_via_esmpy(source_cube, grid_cube)

print source_cube
print
print grid_cube

t_dbg = 0


