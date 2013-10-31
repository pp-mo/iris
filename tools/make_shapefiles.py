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
import os.path

parser = argparse.ArgumentParser(
    description='Save 2d fields as shapefiles.')
parser.add_argument('in_paths', nargs='+',
                    help='paths to source files')
parser.add_argument('-o', '--out-path', default=None,
                    help='alternative filename or directory path for output')
parser.add_argument('-y', '--dryrun', action='store_true',
                    help="don't perform actual actions")
parser.add_argument('-v', '--verbose', action='store_true',
                    help="print extra messages")

args = parser.parse_args()

do_dryrun = args.dryrun
do_verbose = args.verbose

if do_dryrun and do_verbose:
    print '(Dry run : no actual operations will be performed.)'

in_paths, out_path = args.in_paths, args.out_path

# Fetch extra imports (avoids delay in error responses)
import iris
# Import main function unless already defined
# NOTE: enables script to work with shapefiles module pasted in same file.
if not 'export_shapefiles' in dir():
    from iris.experimental.shapefiles import export_shapefiles

outpath_is_dir = out_path and os.path.isdir(out_path)
if len(in_paths) > 1 and out_path and not outpath_is_dir:
    print ('Output path is not a directory, as '
           'required for use with multiple inputs.')
    exit(1)

for in_filepath in in_paths:
    out_filepath = in_filepath
    if out_path:
        if outpath_is_dir:
            # Given path is directory
            out_filepath = os.path.join(out_path,
                                        os.path.basename(in_filepath))
        else:
            # Output path is a complete filename
            out_filepath = out_path
    if do_verbose:
        print 'Loading : "{}" ..'.format(in_filepath)
    if not do_dryrun:
        cube = iris.load_cube(in_filepath)
    if do_verbose:
        print '.. Saving "{}"'.format(out_filepath)
    if not do_dryrun:
        export_shapefiles(cube, out_filepath)

if do_verbose:
    print 'All Done.'
