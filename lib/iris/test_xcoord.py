import numpy as np
from iris.xcube import XDimCoord
import xarray as xr
import pytest


import pytest

@pytest.fixture
def v_coord():
    ds = xr.Dataset({'foo': xr.DataArray(np.arange(4), attrs={'units': 'm/s', 'standard_name': 'velocity', 'long_name': 'longlong'})})
    return XDimCoord(ds, 'foo')


def test_std_name(v_coord):
    assert v_coord.standard_name == 'velocity'

def test_long_name(v_coord):
    assert v_coord.long_name == 'longlong'

def test_var_name(v_coord):
    assert v_coord.var_name == 'foo'

def test_copy(v_coord):
    new = v_coord.copy(points=v_coord.points - 1)
    assert new._data_obj is not v_coord._data_obj
    assert isinstance(new, XDimCoord)
    new.standard_name = 'wind'
    assert v_coord.standard_name == 'velocity'
    assert new._xvar.attrs['standard_name'] == 'wind'
    assert new.points.min() == v_coord.points.min() - 1

def test_slice(v_coord):
    assert list(v_coord[::2].points) == [0, 2]

def test_set_points(v_coord):
    v_coord.points = [1, 2, 2.1, 5]
    assert list(v_coord.points) == [1, 2, 2.1, 5]

def test_set_points_monotonic(v_coord):
    with pytest.raises(
            ValueError, message="points array must be strictly monotonic"):
        v_coord.points = [1, 2, 2, 5]

@pytest.mark.skip
def test_repr(v_coord):
    assert repr(v_coord) == 1
