#!/usr/bin/env python2.7
# (C) British Crown Copyright 2010 - 2013, Met Office
#
# This file is part of Iris.
#
# Iris is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Iris is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Iris.  If not, see <http://www.gnu.org/licenses/>.
"""A script to save a single 2D input field as shapefiles."""

import argparse
import glob
import os.path


parser = argparse.ArgumentParser(
    description='Save 2d fields as shapefiles.',
    epilog=('NOTE: "in_path" may contain wildcards.  In that case, '
            '"out_path" may only be a directory path.'))
parser.add_argument('in_path',
                   help='Path to source file')
parser.add_argument('out_path', nargs='?', default=None,
                   help='Path to destination files')
parser.add_argument('-y', '--dryrun', action='store_true',
                   help="Don't perform actual action")
parser.add_argument('-v', '--verbose', action='store_true',
                   help="Print extra detail")
parser.add_argument('-d', '--debug', action='store_true',
                   help="Enable debug output")

args = parser.parse_args()

do_test_only = args.dryrun
do_debug = args.debug
do_verbose = args.verbose or do_debug
if do_debug:
    print 'Args : ', args

in_path, out_path = args.in_path, args.out_path
if out_path is None:
    out_path = in_path


# Fetch extra imports (avoids delay in error responses)
import iris
from iris.experimental.shapefiles import export_shapefiles

given_wildcards = in_path.find('*') >= 0 or in_path.find('?') >= 0
in_filepaths = glob.glob(in_path)
if not in_filepaths:
    print 'No input file(s) found for : "{}"'.format(in_path)
    exit(1)

for in_filepath in in_filepaths:
    if given_wildcards:
        out_filepath = os.path.join(out_path,
                                    os.path.basename(in_filepath))
    else:
        out_filepath = out_path
    if do_verbose:
        print 'Loading ..', in_filepath
    if not do_test_only:
        cube = iris.load_cube(in_filepath)
    if do_verbose:
        print '.. Saving ..', out_filepath
    if not do_test_only:
        export_shapefiles(cube, out_filepath)
    if do_verbose:
        print '.. Done.'
