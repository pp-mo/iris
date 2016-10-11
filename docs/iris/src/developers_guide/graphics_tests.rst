.. _developer_graphics_tests:

Graphics tests
**************

The only practical way of testing plotting functionality is to check actual
output plots.
For this, a basic 'graphics test' assertion operation is provided in the method
:method:`iris.tests.IrisTest.check_graphic` :  This tests plotted output for a
match against a stored reference.
A "graphics test" is any test which employs this.

At present (Iris version 1.10), such tests include the testing for modules
`iris.tests.test_plot` and `iris.tests.test_quickplot`, and also some other
'legacy' style tests (as described in :ref:`developer_tests`).
It is conceivable that new 'graphics tests' of this sort can still be added.
However, as graphics tests are inherently "integration" style rather than true
unit tests, results are dependent on the installed versions of dependences (see
below), so this is not recommended except where no alternative is practical.

Testing actual plot results introduces some significant difficulties :
 * Graphics tests are inherently 'integration' style tests, so results will
   often vary with the versions of key dependencies :  Obviously, results will
   depend on the matplotlib version, but they can also depend on numpy and
   other installed packages.
 * Although seems possible in principle to accommodate 'small' result changes
   by distinguishing plots which are 'nearly the same' from those which are
   'significantly different', in practice no *automatic* scheme for this can be
   perfect :  That is, any calculated tolerance in output matching will allow
   some changes which a human would judge as a significant error.
 * Storing a variety of alternative 'acceptable' results as reference images
   can easily lead to uncontrolled increases in the size of the repository,
   given multiple indpendent sources of variation.


Graphics Testing Strategy
=========================

Prior to Iris 1.10, all graphics tests compared against a stored reference
image with a small allowed RMS tolerance, based on RGB values in each pixel.

From Iris v1.11 onward, we want to support testing Iris against multiple
versions of matplotlib (and some other dependencies).  
To make these reasonable, we have now rewritten "check_graphic" to allow
multiple alternative 'correct' results without including many more images in
the Iris repository.  
This consists of :

 * using a hash of image output pixels (the SHA of a PNG file) as the basis
   for checking test results
 * storing the hashes of 'known accepted results' for each test in a
   database in the repo (which is actually stored in 
   ``lib/iris/tests/results/imagerepo.json``).
 * storing associated reference images for each hash value in a separate web
   project, currently in https://github.com/SciTools/test-images-scitools ,
   allowing human-eye judgement of 'valid equivalent' results.
 * a new version of the 'iris/tests/idiff.py' assists in comparing proposed
   new 'correct' result images with the existing accepted ones.

BRIEF...
There should be sufficient work-flow detail here to allow an iris developer to:
    * understand the new check graphic test process
    * understand the steps to take and tools to use to add a new graphic test
    * understand the steps to take and tools to use to diagnose and fix an graphic test failure


Basic workflow
==============
#. a graphics test result has changed, following changes in Iris or
   dependencies, so a test is failing
#. the developer judges that the resulting, changed plot image is actually
   "correct" (usually, by visually comparing it with previous 'good' results).
#. a copy of the output PNG file is added to the reference image repository in
   https://github.com/SciTools/test-images-scitools.  The file is named
   according to the image hash value, as ``<hash>.png``.
#. the hash value of the new result is added into the relevant set of 'valid
   result hashes' in the image result database file,
   ``tests/results/imagerepo.json``.
#. the tests can now be re-run, and the 'new' result should now be accepted.
#. a pull request is created to add this file into the test-images-scitools
   repository
#. a pull request is created in the Iris repository, including the change to
   the image results database (``tests/results/imagerepo.json``) :
   This pull request must contain a reference to the matching one in
   test-images-scitools.

Note: the Iris pull-request will not test out successfully in Travis until the
test-images-scitools pull request has been merged :  This is because there is
an Iris test which ensures the existence of the reference images (uris) for all
the targets in the image results database.


Fixing a failing graphics test
==============================


Adding a new graphics test
==========================
