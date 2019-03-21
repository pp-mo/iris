
import iris
import iris.fileformats.cf

import xarray_filelike_wrapper as xrfile
import xarray as xr

from netCDF4 import Dataset

import mock

fp = iris.sample_data_path('hybrid_height.nc')

xds = xr.open_dataset(fp)
wrapped = xrfile.fake_nc4python_dataset(xds)

# Test wrapper alone...
attrs = wrapped.ncattrs()
print('\n'.join('{}: {}'.format(name, wrapped.getncattr(name))
                for name in attrs))


# Do a hacked load.
iris.fileformats.cf._WRAP_LOADS_WITH_XARRAY_FILELIKE = True
cube_xr = iris.load_cube(fp, 'air_potential_temperature')
print('')
print('Cube loaded via Xarray:')
print(cube_xr)
test_fmt = "   cube.attributes.get('Xarray_dataset') : {!r}"
print(test_fmt.format(cube_xr.attributes.get('Xarray_dataset')))

# Do a "normal" load.
iris.fileformats.cf._WRAP_LOADS_WITH_XARRAY_FILELIKE = False
cube_nc = iris.load_cube(fp, 'air_potential_temperature')
print('')
print('Cube loaded direct from netcdf:')
print(cube_nc)
print(test_fmt.format(cube_nc.attributes.get('Xarray_dataset')))

print('')
del cube_xr.attributes['Xarray_dataset']
same = (cube_xr == cube_nc)
print('Same? : {}'.format(same))