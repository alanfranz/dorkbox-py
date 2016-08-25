# -*- coding: utf-8 -*-
from unittest import TestCase
from tempfile import TemporaryDirectory
import os
from subprocess import check_call, check_output

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

    def test_when_connection_new_dorkbox_repo_both_references_exist(self):
        with TemporaryDirectory() as git_repo_dir:
            check_call(["git", "init", "--bare", git_repo_dir])

            with TemporaryDirectory() as first_repo_dir:
                first_repo = Repository.create_new(first_repo_dir, git_repo_dir)
                with TemporaryDirectory() as second_repo_dir:
                    second_repo = Repository.connect_existing(second_repo_dir, git_repo_dir)
                    all_branches = check_output(["git", "--work-tree={}".format(second_repo_dir),
                                                 "--git-dir={}".format(os.path.join(second_repo_dir, ".git")),
                                                 "branch", "-a"], universal_newlines=True)
                    self.assertTrue(first_repo.client_id in all_branches)
                    self.assertTrue(second_repo.client_id in all_branches)
