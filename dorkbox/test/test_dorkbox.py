# -*- coding: utf-8 -*-
from unittest import TestCase
from tempfile import TemporaryDirectory
import os
from subprocess import check_call

from dorkbox.dorkbox import Git, Repository, GITIGNORE

class TestRepository(TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self._old = os.getcwd()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._old)
        self._tmp.cleanup()
        Repository.cleanup_tracked()

    def test_repository_create_creates_a_new_git_repo_with_proper_ignore_file(self):
        with TemporaryDirectory() as gitrepodir:
            check_call(["git", "init", "--bare", gitrepodir])
            Repository.create_new(os.path.abspath("."), gitrepodir)
            self.assertTrue(os.path.exists("./{}".format(GITIGNORE)))
