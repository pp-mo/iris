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

ndhf = iris.load_cube('/project/hadgem3/data/xexoc/ony/xexoc_1996_2005_grid_T.nc_nc3', 'Net Downward Heat Flux')
tgt_grid = iris.load_cube('/data/cr2/hadpd/southern_oc_heat_fluxes/net_heat_flux_edwards_method_ann.pp')
# throw away the data, so it doesn't plot
#tgt_grid.data[...] = np.ma.masked

# hack coord-system for now...
cs_pc = iris.coord_systems.GeogCS(iris.fileformats.pp.EARTH_RADIUS)
ndhf.coord('longitude').coord_system = cs_pc
ndhf.coord('latitude').coord_system = cs_pc
assert ndhf.shape[0] == 1
ndhf = ndhf[0]
#ndhf = ndhf[10:410,10:410]
ndhf = ndhf[100:104,100:104]
ndhf_regridded = regrid_conservative_via_esmpy(ndhf, tgt_grid)