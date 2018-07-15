import iris.xcube as xcube
import iris
import xarray as xr


fname = iris.sample_data_path('E1_north_america.nc')
ds = xr.open_dataset(fname)

print(ds)
cube = xcube.XCube(ds, 'air_temperature')

print(cube)
