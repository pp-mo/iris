import numpy as np
from iris.xcube import XCube
import xarray as xr
import pytest


import pytest

@pytest.fixture
def t_cube():
    ds = xr.Dataset(
        {'air_temp': xr.Variable(['longitude', 'latitude'],
            np.arange(12).reshape(3, 4),
            attrs={'units': 'K', 'standard_name': 'air_temperature', 'long_name': 'foobar'},
            )},
        coords={'longitude': xr.Variable('longitude', np.arange(3), attrs={'standard_name': 'longitude'}),
                'latitude': xr.Variable('latitude', np.arange(4), attrs={'standard_name': 'latitude',})},
        )
    return XCube(ds, 'air_temp')

def test_std_name(t_cube):
    assert t_cube.standard_name == 'air_temperature'

def test_long_name(t_cube):
    assert t_cube.long_name == 'foobar'

def test_var_name(t_cube):
    assert t_cube.var_name == 'air_temp'

def test_data(t_cube):
    assert isinstance(t_cube.data, np.ndarray)

def test_add_aux_coord(t_cube):
    import iris.coords
    coord = iris.coords.DimCoord([1, 4, 6], long_name='foobar', var_name='foobar')
    t_cube.add_aux_coord(coord, 0)
    assert 'foobar' in t_cube._data_obj

    assert coord in t_cube.coords()
    assert t_cube.coord(coord)

    new_coord = t_cube.coord('foobar')
    assert new_coord is not coord
    assert new_coord == coord

from numpy.testing import assert_array_equal
def test_set_data(t_cube):
    expected = np.arange(12).reshape(3, 4)
    assert_array_equal(t_cube.data, expected)
    t_cube.data = expected**2
    assert_array_equal(t_cube._xvar.data, expected**2)
