# NOT THE ORIGINAL.
# Copied from : /net/home/h05/itpp/py_ownmods/pp_utils.py

import datetime

class TimedBlock(object):
    """ A class with contextmanager behaviour, to time a block of statements. """

    def __init(self):
        """ Create contextmanager object, which after use contains the elapsed time result. 

            Usage:
              with TimedBlock() as t:
                  <statements ...
                  ...
                  >
              time_taken = t.seconds()
        """
        self.start_datetime = None
        self.elapsed_deltatime = None

    def __enter__(self):
        self.start_datetime = datetime.datetime.now()
        return self

    def __exit__(self, e1, e2, e3):
        self.end_datetime = datetime.datetime.now()
        self.elapsed_deltatime = self.end_datetime - self.start_datetime
        self._seconds = self.elapsed_deltatime.total_seconds()

    def seconds(self):
        """ Our elapsed time in seconds. """ 
        return self._seconds

