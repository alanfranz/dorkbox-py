# -*- coding: utf-8 -*-
from unittest import TestCase

from shutil import rmtree

from os.path import join, expanduser
from os import makedirs
import contextlib

from tempfile import TemporaryDirectory, mkdtemp, NamedTemporaryFile, mktemp
import os, sys
from subprocess import check_call, check_output, DEVNULL, call, CalledProcessError

from foolscrate.foolscrate import Repository,  SyncError, GlobalConfig
from foolscrate.git import Git
import logging

from os.path import exists

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

GITIGNORE = Repository.GITIGNORE
CONFLICT_STRING = Repository.CONFLICT_STRING
FOOLSCRATE_CRONTAB_COMMENT = Repository.FOOLSCRATE_CRONTAB_COMMENT

class TestRepository(TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        confroot = join(self._tmp.name, "confroot")
        makedirs(confroot)
        reporoot = join(self._tmp.name, "reporoot")
        makedirs(reporoot)

        # I hate this kind of global monkeypatching, but I don't want to change too many things right now.
        self._savecfg = Repository._global_config_factory
        Repository._global_config_factory = GlobalConfig.factory(join(confroot, ".foolscrate.conf"), join(confroot, ".foolscrate.conf.lock"))

        self._old = os.getcwd()
        os.chdir(reporoot)

    def tearDown(self):
        os.chdir(self._old)
        Repository.cleanup_tracked()
        Repository._global_config_factory = self._savecfg
        self._tmp.cleanup()

    def test_repository_create_creates_a_new_git_repo_with_proper_ignore_file(self):
        with TemporaryDirectory() as gitrepodir:
            check_call(["git", "init", "--bare", gitrepodir])
            Repository.create_new(os.path.abspath("."), gitrepodir)
            self.assertTrue(os.path.exists("./{}".format(GITIGNORE)))

    def test_when_connection_new_foolscrate_repo_both_references_exist(self):
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

        # I hate this kind of global monkeypatching, but I don't want to change too many things right now.
        self._conftmp = TemporaryDirectory()
        self._savecfg = Repository._global_config_factory
        Repository._global_config_factory = GlobalConfig.factory(join(self._conftmp.name, ".foolscrate.conf"), join(self._conftmp.name, ".foolscrate.conf.lock"))

        self.remote_repo_dir = mkdtemp()
        check_call(["git", "init", "--bare", self.remote_repo_dir])

        self.first_client_dir = mkdtemp()
        self.second_client_dir = mkdtemp()
        self.third_client_dir = mkdtemp()

        self.first_repo = Repository.create_new(self.first_client_dir, self.remote_repo_dir)
        self.second_repo = Repository.connect_existing(self.second_client_dir, self.remote_repo_dir)
        self.third_repo = Repository.connect_existing(self.third_client_dir, self.remote_repo_dir)

        self.sync_all_lock = mktemp()

    def tearDown(self):
        rmtree(self.remote_repo_dir)
        rmtree(self.first_client_dir)
        rmtree(self.second_client_dir)
        rmtree(self.third_client_dir)
        with contextlib.suppress(FileNotFoundError):
            os.unlink(self.sync_all_lock)
        Repository._global_config_factory = self._savecfg
        self._conftmp.cleanup()

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
        Repository.sync_all_tracked(lock_filepath=self.sync_all_lock)
        Repository.sync_all_tracked(lock_filepath=self.sync_all_lock)

        with open(join(self.second_client_dir, "something"), mode="r", encoding="ascii") as f:
            self.assertEqual("asd", f.read())

        with open(join(self.second_client_dir, "something"), mode="a", encoding="ascii") as f:
            f.write("xyz")

        # same as above
        Repository.sync_all_tracked(lock_filepath=self.sync_all_lock)
        Repository.sync_all_tracked(lock_filepath=self.sync_all_lock)

        with open(join(self.first_client_dir, "something"), mode="r", encoding="ascii") as f:
            self.assertEqual("asdxyz", f.read())

    def test_all_synced_repos_are_tracked_independently(self):
        with open(join(self.first_client_dir, "something"), mode="w", encoding="ascii") as f:
            f.write("asd")

        Repository.sync_all_tracked(lock_filepath=self.sync_all_lock)

        with open(join(self.first_client_dir, "something"), mode="w", encoding="ascii") as f:
            f.write("xyzxyz")

        self.first_repo.sync()

        with open(join(self.second_client_dir, "something"), mode="w", encoding="ascii") as f:
            # will result in a sync conflict for the 2nd repo
            f.write("kkkkkk")

        Repository.sync_all_tracked(lock_filepath=self.sync_all_lock)

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

        call(["git", "--work-tree={}".format(self.second_client_dir),
              "--git-dir={}".format(join(self.second_client_dir, ".git")), "merge", "foolscrate/master"],
             stderr=DEVNULL)

        with open(join(self.second_client_dir, "something"), mode="w", encoding="ascii") as f:
            f.write("merged")

        check_call(["git", "--work-tree={}".format(self.second_client_dir),
                    "--git-dir={}".format(join(self.second_client_dir, ".git")), "commit", "-am", "solved conflict"],
                   stderr=DEVNULL)
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

        Repository.sync_all_tracked(lock_filepath=self.sync_all_lock)

        self.assertFalse(exists(join(self.second_client_dir, "something")))


class SpyCrontab(object):
    def __init__(self):
        self.arguments = []
        self.crontab = ""

    def cmd(self, *args):
        self.arguments.append(args)
        if args[0] == "-l":
            return self.crontab
        else:
            self.crontab = open(args[0]).read()

class TestCrontabManipulation(TestCase):
    def test_cron_enabled_when_crontab_empty(self):
        spy = SpyCrontab()
        Repository.enable_foolscrate_cronjob(crontab_command=spy)
        self.assertEqual(2, spy.crontab.count(FOOLSCRATE_CRONTAB_COMMENT))

    def test_cron_is_not_duplicated_if_already_there(self):
        spy = SpyCrontab()
        Repository.enable_foolscrate_cronjob(crontab_command=spy)
        Repository.enable_foolscrate_cronjob(crontab_command=spy)
        self.assertEqual(2, spy.crontab.count(FOOLSCRATE_CRONTAB_COMMENT))

    def test_cron_is_updated_if_already_there_but_executble_changes(self):
        spy = SpyCrontab()
        Repository.enable_foolscrate_cronjob(crontab_command=spy)
        Repository.enable_foolscrate_cronjob(foolscrate_executable="/bin/ls", crontab_command=spy)
        self.assertEqual(1, spy.crontab.count("/bin/ls"))
