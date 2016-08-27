# -*- coding: utf-8 -*-
from unittest import TestCase

from shutil import rmtree

from os.path import join

from tempfile import TemporaryDirectory, mkdtemp, NamedTemporaryFile
import os, sys
from subprocess import check_call, check_output, DEVNULL, run, CalledProcessError

from dorkbox.dorkbox import Git, Repository, GITIGNORE, CONFLICT_STRING, SyncError, DORKBOX_CRONTAB_COMMENT
import logging

from os.path import exists

logging.basicConfig(stream= sys.stderr, level=logging.DEBUG)


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

class TestSync(TestCase):
    def setUp(self):
        Repository.cleanup_tracked()
        self.remote_repo_dir = mkdtemp()
        check_call(["git", "init", "--bare", self.remote_repo_dir])

        self.first_client_dir = mkdtemp()
        self.second_client_dir = mkdtemp()
        self.third_client_dir = mkdtemp()

        self.first_repo = Repository.create_new(self.first_client_dir, self.remote_repo_dir)
        self.second_repo = Repository.connect_existing(self.second_client_dir, self.remote_repo_dir)
        self.third_repo = Repository.connect_existing(self.third_client_dir, self.remote_repo_dir)

    def tearDown(self):
        rmtree(self.remote_repo_dir)
        rmtree(self.first_client_dir)
        rmtree(self.second_client_dir)
        rmtree(self.third_client_dir)
        Repository.cleanup_tracked()


    def test_syncing_between_two_clients(self):
        with open(join(self.first_client_dir, "something"), mode="w", encoding="ascii") as f:
            f.write("asd")

        self.first_repo.sync()
        self.second_repo.sync()

        with open(join(self.second_client_dir, "something"), mode="r", encoding="ascii") as f:
            self.assertEqual("asd", f.read())

        with open(join(self.second_client_dir, "something"), mode="a", encoding="ascii") as f:
            f.write("xyz")

        self.second_repo.sync()
        self.first_repo.sync()

        with open(join(self.first_client_dir, "something"), mode="r", encoding="ascii") as f:
            self.assertEqual("asdxyz", f.read())

    def test_tracking_between_two_clients(self):
        with open(join(self.first_client_dir, "something"), mode="w", encoding="ascii") as f:
            f.write("asd")

        # we need to sync twice, since the first sync will send our content from 1st upstream,
        # and the second will pull content from upstream to 2n repo
        Repository.sync_all_tracked()
        Repository.sync_all_tracked()

        with open(join(self.second_client_dir, "something"), mode="r", encoding="ascii") as f:
            self.assertEqual("asd", f.read())

        with open(join(self.second_client_dir, "something"), mode="a", encoding="ascii") as f:
            f.write("xyz")

        # same as above
        Repository.sync_all_tracked()
        Repository.sync_all_tracked()

        with open(join(self.first_client_dir, "something"), mode="r", encoding="ascii") as f:
            self.assertEqual("asdxyz", f.read())

    def test_all_synced_repos_are_tracked_independently(self):
        with open(join(self.first_client_dir, "something"), mode="w", encoding="ascii") as f:
            f.write("asd")

        Repository.sync_all_tracked()

        with open(join(self.first_client_dir, "something"), mode="w", encoding="ascii") as f:
            f.write("xyzxyz")

        self.first_repo.sync()

        with open(join(self.second_client_dir, "something"), mode="w", encoding="ascii") as f:
            # will result in a sync conflict for the 2nd repo
            f.write("kkkkkk")

        Repository.sync_all_tracked()

        with open(join(self.third_client_dir, "something"), mode="r", encoding="ascii") as f:
            # will result in a sync conflict
            self.assertEqual("xyzxyz", f.read())

    def test_conflicted_client_doesnt_sync_until_fixed(self):
        with open(join(self.first_client_dir, "something"), mode="w", encoding="ascii") as f:
            f.write("asd")

        self.first_repo.sync()

        with open(join(self.second_client_dir, "something"), mode="w", encoding="ascii") as f:
            f.write("mashup")

        try:
            self.second_repo.sync()
            self.fail("should have launched exception")
        except SyncError:
            pass

        self.assertTrue(exists(join(self.second_client_dir, CONFLICT_STRING)))

        run(["git", "--work-tree={}".format(self.second_client_dir),
                    "--git-dir={}".format(join(self.second_client_dir, ".git")), "merge", "dorkbox/master"], stderr=DEVNULL)

        with open(join(self.second_client_dir, "something"), mode="w", encoding="ascii") as f:
            f.write("merged")

        check_call(["git", "--work-tree={}".format(self.second_client_dir), "--git-dir={}".format(join(self.second_client_dir, ".git")), "commit", "-am", "solved conflict"], stderr=DEVNULL)
        os.unlink(join(self.second_client_dir, CONFLICT_STRING))

        self.second_repo.sync()
        self.first_repo.sync()

        with open(join(self.first_client_dir, "something"), mode="r", encoding="ascii") as f:
            self.assertEqual("merged", f.read())

    def test_multiple_sync_without_changes_doesnt_crash(self):
        self.second_repo.sync()
        self.second_repo.sync()
        self.second_repo.sync()

    def test_untracked_repository_doesnt_get_synced_by_sync_all_tracked(self):
        self.second_repo.untrack()

        with open(join(self.first_client_dir, "something"), mode="w", encoding="ascii") as f:
            f.write("asd")

        Repository.sync_all_tracked()

        self.assertFalse(exists(join(self.second_client_dir, "something")))


class TestCrontabManipulation(TestCase):
    def setUp(self):
        try:
            self.save_user_crontab = check_output(["crontab", "-l"], universal_newlines=True, stderr=DEVNULL)
        except CalledProcessError:
            self.save_user_crontab = None

        # now remove current crontab
        run(["crontab", "-r"], universal_newlines=True, stderr=DEVNULL)

    def tearDown(self):
        if self.save_user_crontab is None:
            run(["crontab", "-r"], universal_newlines=True, stderr=DEVNULL)
            return

        with NamedTemporaryFile() as f:
            f.write(self.save_user_crontab)
            f.flush()
            check_call(["crontab", f.name])


    def test_dorkbox_cron_enabled_when_crontab_empty(self):
        Repository.enable_dorkbox_cronjob()
        current_crontab = check_output(["crontab", "-l"], universal_newlines=True)
        self.assertEqual(2, current_crontab.count(DORKBOX_CRONTAB_COMMENT))

    def test_dorkbox_cron_is_not_duplicated_if_already_there(self):
        Repository.enable_dorkbox_cronjob()
        Repository.enable_dorkbox_cronjob("asdasd")
        current_crontab = check_output(["crontab", "-l"], universal_newlines=True)
        self.assertEqual(2, current_crontab.count(DORKBOX_CRONTAB_COMMENT))

    def test_dorkbox_cron_is_updated_if_already_there(self):
        Repository.enable_dorkbox_cronjob()
        Repository.enable_dorkbox_cronjob("asdasd")
        current_crontab = check_output(["crontab", "-l"], universal_newlines=True)
        self.assertEqual(1, current_crontab.count("asdasd"))

