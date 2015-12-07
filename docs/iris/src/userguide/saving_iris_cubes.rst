.. _saving_iris_cubes:

==================
Saving Iris cubes
==================

Iris supports the saving of cubes and cube lists to:

* CF netCDF (1.5)
* GRIB (edition 2)
* Met Office PP


The :py:func:`iris.save` function saves one or more cubes to a file.

If the filename includes a supported suffix then Iris will use the correct saver
and the keyword argument `saver` is not required.

    >>> import iris
    >>> filename = iris.sample_data_path('uk_hires.pp')
    >>> cubes = iris.load(filename)
    >>> cube = cubes[0]
    >>> iris.save(cubes, '/tmp/uk_hires.nc')

.. warning::

    Saving a cube whose data has been loaded lazily
    (if `cube.has_lazy_data()` returns `True`) to the same file it expects
    to load data from will cause both the data in-memory and the data on
    disk to be lost.

    .. code-block:: python

        cube = iris.load_cube('somefile.nc')
        # The next line causes data loss in 'somefile.nc' and the cube.
        iris.save(cube, 'somefile.nc')

    In general, overwriting a file which is the source for any lazily loaded
    data can result in corruption. Users should proceed with caution when
    attempting to overwrite an existing file.


Controlling the save process
-----------------------------

The :py:func:`iris.save` function passes all other keywords through to the saver function defined, or automatically set from the file extension.  This enables saver specific functionality to be called.

    >>> # Save a cube to PP
    >>> iris.save(cube, "myfile.pp")
    >>> # Save a cube list to a PP file, appending to the contents of the file
    >>> # if it already exists
    >>> iris.save(cubes, "myfile.pp", append=True)
    >>> # Save a cube to netCDF, defaults to NETCDF4 file format
    >>> iris.save(cube, "myfile.nc")
    >>> # Save a cube list to netCDF, using the NETCDF4_CLASSIC storage option
    >>> iris.save(cubes, "myfile.nc", netcdf_format="NETCDF3_CLASSIC")

See 

* :py:func:`iris.fileformats.netcdf.save`
* :py:func:`iris.fileformats.grib.save_grib2`
* :py:func:`iris.fileformats.pp.save`

for more details on supported arguments for the individual savers.

Customising the save process
-----------------------------

When saving to GRIB or PP, the save process may be intercepted between the translation step and the file writing.
  This enables customisation of the output messages, based on Cube metadata if required, over and above the
 translations supplied by Iris.

The pattern to follow to customise a save involves defining a function which takes a cube as an argument::

        def custom_saver(cube):
	    pass

Within this function, iterate through the, cube:fileformat pairs, e.g, for grib::

        def custom_saver(cube):
            for cube, message in iris.fileformats.grib.as_pairs(cube):
                pass     

and implement any custom logic within this loop.  At a step within the loop a there is a 2D cube, sliced
 from the input cube, and a GRIB message in scope.  Any logic check can be run on a cube here and any conditional
 setting of metadata on the GRIB message, prior to saving can be achieved, including passing cube metadata values,
 correctly formatted, to the message.

The as_pairs iterator must yield the message/field, for every iteration of the loop, (note the indentation)::

        def custom_saver(cube):
            for cube, message in iris.fileformats.grib.as_pairs(cube):
                pass
            yield message

This function can now be passed to the format specific save_messages function.  In this example, nothing will be
 changed compared to the standard iris save::

        iris.fileformats.grib.save_messages(custom_saver(mycube), '/tmp/agrib2.grib2')

Knowledge of the GRIB or PP metadata and the constraints assocaited is important here, as poorly formed results and
 exceptions can result.

For example, a GRIB2 message with a particular known long_name may need to be saved to a specific parameter code
 and type of statistical process.  This can be achieved by::

        def tweaked_messages(cube):
            for cube, grib_message in iris.fileformats.grib.as_pairs(cube):
                # post process the GRIB2 message, prior to saving
                if cube.name() == 'carefully_customised_precipitation_amount':
		    gribapi.grib_set_long(grib_message, "typeOfStatisticalProcess", 1)
                    gribapi.grib_set_long(grib_message, "parameterCategory", 1)
                    gribapi.grib_set_long(grib_message, "parameterNumber", 1)
                yield message
        iris.fileformats.grib.save_messages(tweaked_messages(cube), '/tmp/agrib2.grib2')

Similarly a PP field may need to be written out with a specific value for LBEXP.  This can be achieved by::

        def tweaked_fields(cube):
            for cube, field in iris.fileformats.pp.as_pairs(cube):
                # post process the PP field, prior to saving
                if cube.name() == 'air_pressure':
		    field.lbexp = 'meaxp'
		elif cube.name() == 'air_density':
		    field.lbexp = 'meaxr'
                yield field
        iris.fileformats.pp.save_fields(tweaked_fields(cube), '/tmp/app.pp')

In another example, a cube may exist without a forecast_period coordinate, but such information may need to be
 derived for a downstream processing requirement for a set of PP fields::

       def ancil_forecast_period_save(cube):
            for cube, ppfield in iris.fileformats.pp.as_pairs(cube):
	        if iris.rules.scalar_coord(cm, 'forecast_period') is None:
		    ppfield.t1 = iris.rules.scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').points[0])
		    ppfield.t2 = iris.rules.scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').points[0])
    		    ppfield.lbft = 0.0
    		    ppfield.lbtim.ia = 0
    		    ppfield.lbtim.ib = 0
    		    ppfield.lbtim.ic = 1
                yield field
        iris.fileformats.pp.save_fields(ancil_forecast_period_save(cube), '/tmp/app.pp')


netCDF
^^^^^^^

NetCDF is a flexible container for metadata and cube metadata is closely related to the CF for netCDF semantics.  This means that cube metadata is well represented in netCDF files, closely resembling the in memory metadata representation.
Thus there is no provision for similar save customisation functionality for netCDF saving, all customisations should be applied to the cube prior to saving to netCDF.

Bespoke Saver
--------------

A bespoke saver may be written to support an alternative file format.  This can be provided to the :py:func:`iris.save`  function, enabling Iris to write to a different file format.
Such a custom saver will need be written to meet the needs of the file format and to handle the metadata translation from cube metadata effectively. 

Implementing a bespoke saver is out of scope for the user guide.

