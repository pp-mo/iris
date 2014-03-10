'''
Created on Mar 4, 2014

@author: itpp
'''
import cartopy.crs as ccrs
import iris
import iris.fileformats.pp
import iris.plot as iplt
from iris.experimental.regrid_conservative import regrid_conservative_via_esmpy
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


ndhf = iris.load_cube('/project/hadgem3/data/xexoc/ony/xexoc_1996_2005_grid_T.nc_nc3', 'Net Downward Heat Flux')
tgt_grid = iris.load_cube('/data/cr2/hadpd/southern_oc_heat_fluxes/net_heat_flux_edwards_method_ann.pp')
tgt_grid_original = tgt_grid.copy()
# throw away the data, so it doesn't plot
#tgt_grid.data[...] = np.ma.masked


#
# Problems now with destination grid, (it has screwy bounds)
# With that fixed, error now looks like spatial_dims mismatch between src+dst.
# So let's hack it here to have 2d lats+lons, and treat as a Mesh.
#
tgt_coord_orig_x = tgt_grid.coord('longitude')
tgt_coord_orig_y = tgt_grid.coord('latitude')
tgt_grid_coord_x = iris.coords.AuxCoord.from_coord(tgt_coord_orig_x)
tgt_grid_coord_y = iris.coords.AuxCoord.from_coord(tgt_coord_orig_y)
lats_limit = 89.9
tgt_grid_coord_y.bounds = np.clip(tgt_grid_coord_y.bounds,
                                  -lats_limit, lats_limit)
x_points_2d, y_points_2d = np.meshgrid(tgt_grid_coord_x.points,
                                       tgt_grid_coord_y.points)
x_contig_bounds_2d, y_contig_bounds_2d = np.meshgrid(
    tgt_grid_coord_x.contiguous_bounds(),
    tgt_grid_coord_y.contiguous_bounds())
shape_full_bounds_2d = list(x_points_2d.shape) + [4]
x_full_bounds_2d = np.zeros(shape_full_bounds_2d)
y_full_bounds_2d = np.zeros(shape_full_bounds_2d)
x_full_bounds_2d[..., 0] = x_contig_bounds_2d[:-1, :-1]
x_full_bounds_2d[..., 1] = x_contig_bounds_2d[:-1, 1:]
x_full_bounds_2d[..., 2] = x_contig_bounds_2d[1:, 1:]
x_full_bounds_2d[..., 3] = x_contig_bounds_2d[1:, :-1]
y_full_bounds_2d[..., 0] = y_contig_bounds_2d[:-1, :-1]
y_full_bounds_2d[..., 1] = y_contig_bounds_2d[:-1, 1:]
y_full_bounds_2d[..., 2] = y_contig_bounds_2d[1:, 1:]
y_full_bounds_2d[..., 3] = y_contig_bounds_2d[1:, :-1]
tgt_grid_coord_x = tgt_grid_coord_x.copy(points=x_points_2d, bounds=x_full_bounds_2d)
tgt_grid_coord_y = tgt_grid_coord_y.copy(points=y_points_2d, bounds=y_full_bounds_2d)
# remove + replace
x_dim, = tgt_grid.coord_dims(tgt_coord_orig_x)
y_dim, = tgt_grid.coord_dims(tgt_coord_orig_y)
tgt_grid.remove_coord(tgt_coord_orig_x)
tgt_grid.remove_coord(tgt_coord_orig_y)
tgt_grid.add_aux_coord(tgt_grid_coord_x, (y_dim, x_dim))
tgt_grid.add_aux_coord(tgt_grid_coord_y, (y_dim, x_dim))

# hack coord-system for now...
cs_pc = iris.coord_systems.GeogCS(iris.fileformats.pp.EARTH_RADIUS)
ndhf.coord('longitude').coord_system = cs_pc
ndhf.coord('latitude').coord_system = cs_pc
assert ndhf.shape[0] == 1
ndhf = ndhf[0]
#ndhf = ndhf[:990]
#ndhf = ndhf[100:104,100:104]

ndhf.data[ndhf.data > 1e6] = np.ma.masked

datarange_min, datarange_max = np.min(ndhf.data), np.max(ndhf.data)
#levels = mpl.ticker.MaxNLocator().tick_values(datarange_min, datarange_max)


#display_projection, lims = ccrs.NorthPolarStereo(), [-50e6, 50e6, -50e6, 50e6]
display_projection, lims = ccrs.PlateCarree(), [-180, 180, -90, 90]
#display_projection = ccrs.SouthPolarStereo()

plt.figure()
ax = plt.axes(projection=display_projection)
ax.coastlines()
ax.gridlines()
ax.set_xlim(lims[:2])
ax.set_ylim(lims[2:])
plt.pcolormesh(ndhf.coord('longitude').points,
               ndhf.coord('latitude').points,
               ndhf.data,
               vmin=datarange_min, vmax=datarange_max,
               transform=ccrs.PlateCarree())
#plt.show()


ndhf_regridded = regrid_conservative_via_esmpy(ndhf, tgt_grid)

plt.figure()
ax = plt.axes(projection=display_projection)
ax.coastlines()
ax.gridlines()
ax.set_xlim(lims[:2])
ax.set_ylim(lims[2:])
plt.pcolormesh(ndhf_regridded.coord('longitude').points,
               ndhf_regridded.coord('latitude').points,
               ndhf_regridded.data,
               vmin=datarange_min, vmax=datarange_max,
               transform=ccrs.PlateCarree())

plt.show()
