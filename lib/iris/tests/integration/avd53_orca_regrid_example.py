'''
Test code to demonstrate regridding of ORCA2_M0.25 field via ESMPy.

'''
import cartopy.crs as ccrs
import iris
import iris.fileformats.pp
import iris.plot as iplt
from iris.experimental.regrid_conservative import regrid_conservative_via_esmpy
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np



# Load provided data cube, and grid cube.
ndhf_filepath = ('/project/hadgem3/data/xexoc/ony/'
                 'xexoc_1996_2005_grid_T.nc_nc3')
grid_filepath = ('/data/cr2/hadpd/southern_oc_heat_fluxes/'
                 'net_heat_flux_edwards_method_ann.pp')
ndhf = iris.load_cube(ndhf_filepath, 'Net Downward Heat Flux')
tgt_grid = iris.load_cube(grid_filepath)

# Remove the *1 time dimension.
assert ndhf.shape[0] == 1
ndhf = ndhf[0]

# Attach a default geodesic coord-system (not provided on load).
cs_pc = iris.coord_systems.GeogCS(iris.fileformats.pp.EARTH_RADIUS)
ndhf.coord('longitude').coord_system = cs_pc
ndhf.coord('latitude').coord_system = cs_pc

#
# Mask out the unwanted ORCA2_M0.25 grid regions.
#
# TODO: how do we generalise this ???
#

# Mask areas with "problem" cell bounds (that ESMF will reject).
# These ones are near the grid poles...
ndhf.data[-6:,:6] = np.ma.masked
ndhf.data[-6:,-6:] = np.ma.masked
ndhf.data[-12:, 720-62:720+62] = np.ma.masked
# This is an odd point near the North pole (? could be a mistake in fact ?).
ndhf.data[-2, 1061] = np.ma.masked

# Mask areas that contain overlapping regions of the grid...
# The top row "row[-1]", overlaps row[-3]  (with a left-right reflection).
ndhf.data[-1, :] = np.ma.masked
# The left + right halves of row[-2] overlap.
ix_mid = ndhf.shape[-1] / 2
ndhf.data[-2, ix_mid:] = np.ma.masked
# There is a two-point overlap around the x-seam.
ndhf.data[:, :1] = np.ma.masked
ndhf.data[:, -1:] = np.ma.masked

# Blank out some very large values in the source (which stop it plotting well).
ndhf.data[ndhf.data > 1e6] = np.ma.masked

# Regrid onto the target grid.
ndhf_regridded = regrid_conservative_via_esmpy(ndhf, tgt_grid)

# Display results
plt.figure()
ax = plt.axes(projection=ccrs.PlateCarree())
ax.coastlines()
ax.gridlines()
ax.set_xlim((-5, 185))
ax.set_ylim((-90, 90))
iplt.pcolormesh(ndhf_regridded)
plt.savefig('avd53_orca_regrid_example.png')
plt.show()
