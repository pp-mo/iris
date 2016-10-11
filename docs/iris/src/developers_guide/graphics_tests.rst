.. _graphics_tests:

Graphics tests
=================

Iris provides specific support for plotting via matplotlib, in the packages
:mod:`iris.plot` and :mod:`iris.quickplot`.  
The effective testing of this plotting functionality is a slightly awkward
problem, as the only method which is both simple and effective is to produce
actual plots and compare them with stored reference images.
This basic 'graphics test' operation is provided by the method
:method:`iris.tests.IrisTest.check_graphic`.

Existing 'graphics tests', which use this method, were previous (up to Iris
1.10) divided between the legacy test modules `iris.tests.test_plot` and
`iris.tests.test_quickplot`, and more recent functions are tested in 
For reasons explained below, all these tests are technically "integration"
tests and not true unit tests.



Testing against actual images introduces two very significant problems:
 * Firstly, it is not practical to automatically distinguish plots which are
   'nearly the same' as a reference image from ones which are
   'significantly different' :  I.E. any allowed tolerance in output 
 * Firstly, these tests are all 'integration' tests using matplotlib, and
   hence tend to be only work with a specific version of matplotlib.

Prior to Iris 1.10, all graphics tests compared against a stored reference
image with a small allowed RMS tolerance, based on RGB values in each pixel.

From Iris v1.11 onward, we have adopted an entirely new means of testing
plotted outputs.
This consists of :

 * using a hash of image output pixels (the SHA of a PNG file) as the basis
   for comparing a test result
 * storing the hashes of 'known accepted results' for each test in a
   database in the repo (which is actually stored in 
   ``lib/iris/tests/results/imagerepo.json``).
 * storing associated reference images for each hash value in a separate web
   project, currently in https://github.com/SciTools/test-images-scitools .


NOTES:
    * not just about mpl versions :  As they tend to be "integration" style
        tests, potentially any dependency can affect the result.
        In practice : especially numpy.

BRIEF...
There should be sufficient work-flow detail here to allow an iris developer to:
    * understand the new check graphic test process
    * understand the steps to take and tools to use to add a new graphic test
    * understand the steps to take and tools to use to diagnose and fix an graphic test failure

