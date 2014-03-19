// (C) British Crown Copyright 2010 - 2012, Met Office
//
// This file is part of Iris.
//
// Iris is free software: you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License as published by the
// Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Iris is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with Iris.  If not, see <http://www.gnu.org/licenses/>.
#include <Python.h>

#include <numpy/arrayobject.h>

#include <wgdosstuff.h>
#include <rlencode.h>

static PyObject *wgdos_unpack_py(PyObject *self, PyObject *args);
static PyObject *rle_decode_py(PyObject *self, PyObject *args);
static PyObject *pack_field_py(PyObject *self, PyObject *args);

#define BYTES_PER_INT_UNPACK_PPFIELD 4
#define LBPACK_NOPACK 0
#define LBPACK_WGDOS_PACKED 1
#define LBPACK_RLE_PACKED 4

static int PACK_TYPE_NONE = LBPACK_NOPACK;
static int PACK_TYPE_WGDOS = LBPACK_WGDOS_PACKED;
static int PACK_TYPE_RLE = LBPACK_RLE_PACKED;

void initpp_packing(void)
{

	/* The module doc string */
	PyDoc_STRVAR(pp_packing__doc__,
	"This extension module provides access to the underlying libmo_unpack library functionality.\n"
	""
	);

	PyDoc_STRVAR(wgdos_unpack__doc__,
	"Unpack PP field data that has been packed using WGDOS archive method.\n"
	"\n"
	"Performs WGDOS unpacking via the libmo_unpack library function 'unpack_ppfield'.\n"
	"\n"
	"Args:\n\n"
	"* data (numpy.ndarray):\n"
	"    The raw field byte array to be unpacked.\n"
	"* lbrow (int):\n"
	"    The number of rows in the grid.\n"
	"* lbnpt (int):\n"
	"    The number of points (columns) per row in the grid.\n"
	"* bmdi (float):\n"
	"    The value used in the field to indicate missing data points.\n"
	"\n"
	"Returns:\n"
	"    numpy.ndarray, 2d array containing normal unpacked field data.\n"
	""
	);


	PyDoc_STRVAR(rle_decode__doc__,
	"Uncompress PP field data that has been compressed using Run Length Encoding.\n"
	"\n"
	"Performs RLE unpacking via the libmo_unpack library function 'unpack_ppfield'.\n"
	"\n"
	"Decodes the field by expanding out the missing data points represented\n"
	"by a single missing data value followed by a value indicating the length\n"
	"of the run of missing data values.\n"
	"\n"
	"Args:\n\n"
	"* data (numpy.ndarray):\n"
	"    The raw field byte array to be uncompressed.\n"
	"* lbrow (int):\n"
	"    The number of rows in the grid.\n"
	"* lbnpt (int):\n"
	"    The number of points (columns) per row in the grid.\n"
	"* bmdi (float):\n"
	"    The value used in the field to indicate missing data points.\n"
	"\n"
	"Returns:\n"
	"    numpy.ndarray, 2d array containing normal uncompressed field data.\n"
	""
	);

	PyDoc_STRVAR(pack_field__doc__,
	"Pack PP field data.\n"
	"\n"
	"Provides access to the libmo_unpack library function 'pack_ppfield'.\n"
	"\n"
	"Args:\n\n"
	"* pack_method (int):\n"
	"    The method to employ (currently defined: 0=unpacked, 1=RLE, 4=WGDOS).\n"
	"* data (numpy.ndarray):\n"
	"    A 2d field array to be packed.\n"
	"* lbrow (int):\n"
	"    The number of rows in the grid.\n"
	"* lbnpt (int):\n"
	"    The number of points (columns) per row in the grid.\n"
	"* bmdi (float):\n"
	"    The value used in the field to indicate missing data points.\n"
	"* bpacc (int):\n"
	"    The power of two that the data accuracy is set to. Used in WGDOS packing.\n"
	"* n_bits (int):\n"
	"    The number of significant bits to be used to pack data. Not used in either packing scheme.\n"
	"\n"
	"Returns:\n"
	"    numpy.ndarray, 2d array containing raw bytes.\n"
	""
	);


	/* ==== Set up the module's methods table ====================== */
	static PyMethodDef pp_packingMethods[] = {
	    {"wgdos_unpack", wgdos_unpack_py, METH_VARARGS, wgdos_unpack__doc__},
	    {"rle_decode", rle_decode_py, METH_VARARGS, rle_decode__doc__},
	    {"pack_field", pack_field_py, METH_VARARGS, pack_field__doc__},
	    {NULL, NULL, 0, NULL}     /* marks the end of this structure */
	};


	/* Create the module, specifying methods. */
	PyObject *this_module = Py_InitModule3("pp_packing", pp_packingMethods, pp_packing__doc__);
	/* Add some useful constant objects */
	PyModule_AddIntConstant(this_module, "PACKING_TYPE_NONE", PACK_TYPE_NONE);
	PyModule_AddIntConstant(this_module, "PACKING_TYPE_WGDOS", PACK_TYPE_WGDOS);
	PyModule_AddIntConstant(this_module, "PACKING_TYPE_RLE", PACK_TYPE_RLE);
	PyModule_AddIntConstant(this_module, "BYTES_PER_PP_WORD", BYTES_PER_INT_UNPACK_PPFIELD);

	import_array();  // Must be present for NumPy.
}


/* wgdos_unpack(byte_array, lbrow, lbnpt, mdi) */
static PyObject *wgdos_unpack_py(PyObject *self, PyObject *args)
{
    char *bytes_in=NULL;
    PyArrayObject *npy_array_out=NULL;
    int bytes_in_len;
    npy_intp dims[2];
    int lbrow, lbnpt, npts;
    float mdi;

    if (!PyArg_ParseTuple(args, "s#iif", &bytes_in, &bytes_in_len, &lbrow, &lbnpt, &mdi)) return NULL;

    // Unpacking algorithm accepts an int - so assert that lbrow*lbnpt does not overflow 
    if (lbrow > 0 && lbnpt >= INT_MAX / (lbrow+1)) {
        PyErr_SetString(PyExc_ValueError, "Resulting unpacked PP field is larger than PP supports.");
        return NULL;
    } else{
        npts = lbnpt*lbrow;
    }

    /* Do the unpack of the given byte array */
    float *dataout = (float*)calloc(npts, sizeof(float));

    if (dataout == NULL) {
        PyErr_SetString(PyExc_ValueError, "Unable to allocate memory for wgdos_unpacking.");
        return NULL;
    }

    function func; // function is defined by wgdosstuff.
    set_function_name(__func__, &func, 0);
    int status = unpack_ppfield(mdi, 0, bytes_in, LBPACK_WGDOS_PACKED, npts, dataout, &func);

    /* Raise an exception if there was a problem with the WGDOS algorithm */
    if (status != 0) {
      free(dataout);
      PyErr_SetString(PyExc_ValueError, "WGDOS unpack encountered an error."); 
      return NULL;
    }
    else {
        /* The data came back fine, so make a Numpy array and return it */
        dims[0]=lbrow;
        dims[1]=lbnpt;
        npy_array_out=(PyArrayObject *) PyArray_SimpleNewFromData(2, dims, NPY_FLOAT, dataout);

        if (npy_array_out == NULL) {
          PyErr_SetString(PyExc_ValueError, "Failed to make the numpy array for the packed data.");
          return NULL;
        }

        // give ownership of dataout to the Numpy array - Numpy will then deal with memory cleanup.
        npy_array_out->flags = npy_array_out->flags | NPY_OWNDATA;

        return (PyObject *)npy_array_out;
    }
}


/* A null function required by the wgdos unpack library */
void MO_syslog(int value, char* message, const function* const caller)
{
	/* printf("MESSAGE %d %s: %s\n", value, caller, message); */
	return; 
}


/* rle_decode(byte_array, lbrow, lbnpt, mdi) */
static PyObject *rle_decode_py(PyObject *self, PyObject *args)
{
    char *bytes_in=NULL;
    PyArrayObject *npy_array_out=NULL;
    int bytes_in_len;
    npy_intp dims[2];
    int lbrow, lbnpt, npts;
    float mdi;

    if (!PyArg_ParseTuple(args, "s#iif", &bytes_in, &bytes_in_len, &lbrow, &lbnpt, &mdi)) return NULL;

    // Unpacking algorithm accepts an int - so assert that lbrow*lbnpt does not overflow
    if (lbrow > 0 && lbnpt >= INT_MAX / (lbrow+1)) {
	PyErr_SetString(PyExc_ValueError, "Resulting unpacked PP field is larger than PP supports.");
        return NULL;
    } else{
        npts = lbnpt*lbrow;
    }

    float *dataout = (float*)calloc(npts, sizeof(float));

    if (dataout == NULL) {
        PyErr_SetString(PyExc_ValueError, "Unable to allocate memory for wgdos_unpacking.");
        return NULL;
    }

    function func;  // function is defined by wgdosstuff.
    set_function_name(__func__, &func, 0);
    int status = unpack_ppfield(mdi, (bytes_in_len/BYTES_PER_INT_UNPACK_PPFIELD), bytes_in, LBPACK_RLE_PACKED, npts, dataout, &func);
    
    /* Raise an exception if there was a problem with the RLE algorithm */
    if (status != 0) {
      free(dataout);
      PyErr_SetString(PyExc_ValueError, "RLE decode encountered an error."); 
      return NULL;
    }
    else {
        /* The data came back fine, so make a Numpy array and return it */
        dims[0]=lbrow;
        dims[1]=lbnpt;
        npy_array_out=(PyArrayObject *) PyArray_SimpleNewFromData(2, dims, NPY_FLOAT, dataout);
        
        if (npy_array_out == NULL) {
          PyErr_SetString(PyExc_ValueError, "Failed to make the numpy array for the packed data.");
          return NULL;
        }

        // give ownership of dataout to the Numpy array - Numpy will then deal with memory cleanup.
        npy_array_out->flags = npy_array_out->flags | NPY_OWNDATA;
        return (PyObject *)npy_array_out;
   }
}


/* pack_field(pack_method, data, lbrow, lbnpt, bmdi, bpacc, n_bits) */
static PyObject *pack_field_py(PyObject *self, PyObject *args)
{
    float *bytes_in=NULL;
    PyArrayObject *npy_array_out=NULL;
    int bytes_in_len;
    int pack, lbrow, lbnpt, npts, bpacc, n_bits;
    float mdi;

    if (!PyArg_ParseTuple(args, "is#iifii",
    		&pack,
    		&bytes_in, &bytes_in_len,
    		&lbrow, &lbnpt, &mdi,
    		&bpacc, &n_bits)) return NULL;

    /* allocate space for result: At least as big as input is ok (according to docs). */
    if (lbrow > 0 && lbnpt >= INT_MAX / (lbrow+1)) {
	PyErr_SetString(PyExc_ValueError, "Resulting unpacked PP field is larger than PP supports.");
        return NULL;
    } else{
        npts = lbnpt*lbrow;
    }
    char *dataout = calloc(npts, sizeof(float));
    if (dataout == NULL) {
        PyErr_SetString(PyExc_ValueError, "Unable to allocate memory for wgdos_unpacking.");
        return NULL;
    }

//    // FOR NOW: print call arguments for security...
//    printf("\nPACK_FIELD: called with: method=%d, lbrow=%d, lbnpt=%d, mdi=%f, bpacc=%d, n_bits=%d\n",
//    	pack, lbrow, lbnpt, mdi, bpacc, n_bits);
//
//    printf("\n  .. first 2 values are : (%f), (%f)", ((float *)bytes_in)[0], ((float *)bytes_in)[1]);

    /* call the library function */
    int out_size;
    function func;  // function is defined by wgdosstuff.
    set_function_name(__func__, &func, 0);
    int status = pack_ppfield(mdi, lbnpt, lbrow, bytes_in, pack, bpacc, n_bits,
    		&out_size, dataout, &func);

    /* Raise an exception if there was a problem with the operation */
    if (status != 0) {
//    if (1) {
      free(dataout);
      char acMsg[] = "PP packing encountered an error: #01234567  ";
      sprintf(acMsg, "PP packing encountered an error: #%08x", status);
      PyErr_SetString(PyExc_ValueError, acMsg);
      return NULL;
    }
    else {
        /* The data came back fine, so make a Numpy array and return it */
    	npy_intp dims[1];
        dims[0] = out_size * BYTES_PER_INT_UNPACK_PPFIELD;
        npy_array_out=(PyArrayObject *) PyArray_SimpleNewFromData(1, dims, NPY_BYTE, dataout);

        if (npy_array_out == NULL) {
          PyErr_SetString(PyExc_ValueError, "Failed to make the numpy array for the packed data.");
          return NULL;
        }

        // give ownership of dataout to the Numpy array - Numpy will then deal with memory cleanup.
        npy_array_out->flags = npy_array_out->flags | NPY_OWNDATA;
        return (PyObject *)npy_array_out;
   }
}
