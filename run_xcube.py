from __future__ import absolute_import

import xarray as xr

import iris.xcube as xcube
import iris


fname = iris.sample_data_path('E1_north_america.nc')
print(fname)
ds = xr.open_dataset(fname, decode_cf=True)

expected = iris.load_cube(fname)

print(ds)
print('-'*90)

cube = xcube.XCube(ds, 'air_temperature')

print(cube)

print(cube.coord('time')[:2])


ds['air_temperature'].attrs['standard_name'] = 'Really?'
print(cube.summary(shorten=True))

print(cube.coord('forecast_period')[:2])


