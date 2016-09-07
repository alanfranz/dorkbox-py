# -*- coding: utf-8 -*-
import sys
from unittest import TestLoader, TextTestRunner
import foolscrate

"This is an helper to run foolscrate tests from within python"

def run_all_tests():
    loader = TestLoader()
    # probably won't work for namespace packages as they may contain more than one path,
    # but foolscrate currently isn't one of those
    suite = loader.discover(foolscrate.__path__[0])
    runner = TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
