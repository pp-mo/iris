from iris.experimental.ncdata.netcdf4 import from_nc4, to_nc4
import iris.tests as itsts


def example_nc4_roundtrip():
    filepath = itsts.get_data_path(
        ["NetCDF", "stereographic", "toa_brightness_temperature.nc"]
    )
    ncdata = from_nc4(filepath)
    filepath2 = "./temp_nc_output.nc"
    to_nc4(ncdata, filepath2)

    # Convert to Iris + compare (a bit of a cheat, bit OK for now?)
    import iris

    cube1 = iris.load_cube(filepath)
    cube2 = iris.load_cube(filepath2)
    print("Round-tripped result, as iris cube:")
    print(cube2)
    print("\nold-file-cube == new-file-cube ? ", cube1 == cube2)


if __name__ == "__main__":
    example_nc4_roundtrip()
