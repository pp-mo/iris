# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
An abstract representation of Netcdf structured data, according to the
"Common Data Model" : https://docs.unidata.ucar.edu/netcdf-java/5.3/userguide/common_data_model_overview.html

TODO:
  * add consistency checking
  * add "direct" netcdf interfacing, i.e. to_nc4/from_nc4

"""
from ._core import NcAttribute, NcData, NcDimension, NcVariable

__all__ = ["NcAttribute", "NcData", "NcDimension", "NcVariable"]
