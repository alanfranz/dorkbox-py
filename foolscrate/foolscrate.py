# -*- coding: utf-8 -*-
import logging
import os
import string
import sys
from time import sleep
from shlex import quote as shell_quote
from socket import gethostname
from subprocess import check_output, CalledProcessError, Popen, PIPE
from random import shuffle, uniform

from configobj import ConfigObj
from filelock import FileLock
from foolscrate.git import Git
from os import access, R_OK, W_OK, X_OK
from os.path import expanduser, join, abspath, exists, dirname
from random import choice
from re import compile as re_compile, DOTALL as RE_DOTALL
from tempfile import NamedTemporaryFile





class SyncError(Exception):
    def __init__(self, directory):
        super().__init__("Could not sync '{}'".format(directory))

class Crontab(object):
    _crontab_command = "crontab"

    def cmd(self, *args):
        return check_output([self._crontab_command] + list(args), universal_newlines=True, stderr=PIPE)

class Repository(object):
    FOOLSCRATE_CONFIG_PATH = join(expanduser("~"), ".foolscrate.conf")
    FOOLSCRATE_CONFIG_LOCK = FOOLSCRATE_CONFIG_PATH + '.lock'
    FOOLSCRATE_CRONTAB_COMMENT = '# foolscrate sync cronjob'

    LOCKFILE_NAME = '.foolscrate.lock'
    CONFLICT_STRING = 'CONFLICT_MUST_MANUALLY_MERGE'
    GITIGNORE = '.gitignore'

    _logger = logging.getLogger("Repository")
    _track_lock = FileLock(FOOLSCRATE_CONFIG_LOCK)

    _SLEEP_BETWEEN_MERGE_ATTEMPTS_SECONDS = 1
    _SLEEP_BETWEEN_SYNC_ALL_TRACKED_ATTEMPTS_MIN_SECONDS = 1
    _SLEEP_BETWEEN_SYNC_ALL_TRACKED_ATTEMPTS_MAX_SECONDS = 4

    @classmethod
    def create_new(cls, local_directory, remote_url):
        cls._logger.info(
            "Will create new foolscrate-enabled repository in local directory. Remote %s should exist and be empty.",
            remote_url)

        if exists(join(local_directory, ".git")):
            raise ValueError("Preexisting git repo found")

        git = Git.init(local_directory)
        with open(join(local_directory, cls.GITIGNORE), "a", encoding="utf-8") as f:
            f.write(cls.CONFLICT_STRING + "\n")
            f.write(cls.LOCKFILE_NAME+ "\n")

        git.cmd("remote", "add", "foolscrate", remote_url)
        git.cmd("add", cls.GITIGNORE)
        git.cmd("commit", "-m", "enabling foolscrate")

        return cls.configure_repository(git, local_directory)

    @classmethod
    def configure_repository(cls, git, local_directory):
        client_id = cls.configure_client_id(git)
        cls._align_client_ref_to_master(git, client_id)
        git.cmd("push", "-u", "foolscrate", "master", client_id)
        repo = Repository(local_directory)
        repo.track()
        return repo

    @classmethod
    def connect_existing(cls, local_directory, remote_url):
        cls._logger.info(
            "Will create new git repo in local directory and connect to remote existing foolscrate repository %s",
            remote_url)

        if exists(join(local_directory, ".git")):
            raise ValueError("Preexisting git repo found")

        git = Git.init(local_directory)
        git.cmd("remote", "add", "foolscrate", remote_url)
        git.cmd("fetch", "--all")
        git.cmd("checkout", "master")

        return cls.configure_repository(git, local_directory)

    def __init__(self, local_directory):
        abs_local_directory = abspath(local_directory)

        if not (
                        exists(abs_local_directory) and
                        access(abs_local_directory, R_OK | W_OK | X_OK) and
                    exists(join(abs_local_directory, ".git"))
        ):
            raise ValueError("{} is not a valid foolscrate-enabled repository".format(abs_local_directory))

        # TODO: what was that alan-mayday error?

        self._git = Git(abs_local_directory)
        self.localdir = abs_local_directory
        self._conflict_string = join(abs_local_directory, self.CONFLICT_STRING)
        self.client_id = self._git.cmd("config", "--local", "--get", "foolscrate.client-id").strip()
        self._sync_lock = FileLock(join(self.localdir, self.LOCKFILE_NAME))

    def sync(self):
        # TODO: probably we should sleep a little between merging attempts
        with self._sync_lock.acquire(timeout=60):
            if exists(self.CONFLICT_STRING):
                self._logger.info("Conflict found, not syncing")
                raise ValueError("Conflict found, not syncing")

            # begin
            for attempt in range(0, 5):
                self._logger.debug("Merge attempt n. %s", attempt)
                self._git.cmd("fetch", "--all")
                self._git.cmd("add", "-A")
                any_change = self._git.cmd("diff", "--staged").strip()

                if any_change != "":
                    self._git.cmd("commit", "-m", "Automatic foolscrate commit")

                try:
                    self._git.cmd("merge", "--no-edit", "foolscrate/master")
                except Exception as e:
                    self._logger.exception("Error while merging, aborting merge")
                    self._git.cmd("merge", "--abort")
                    sleep(self._SLEEP_BETWEEN_MERGE_ATTEMPTS_SECONDS)
                    continue

                self._align_client_ref_to_master(self._git, self.client_id)

                try:
                    self._git.cmd("push", "foolscrate", "master", self.client_id)
                except Exception as e:
                    self._logger.exception("Error while pushing")
                    sleep(self._SLEEP_BETWEEN_MERGE_ATTEMPTS_SECONDS)
                    continue
                break
            else:
                self._logger.error(
                    "Couldn't succeed at merging or pushing back our changes, probably we've got a conflict")
                with open(self._conflict_string, "w") as f:
                    pass
                raise SyncError(self.localdir)

            self._logger.info("Sync succeeded")

    def track(self):
        with self._track_lock.acquire(timeout=60):
            cfg = ConfigObj(self.FOOLSCRATE_CONFIG_PATH, unrepr=True, write_empty_values=True)
            # configobj doesn't support sets natively, only lists.
            track = cfg.get("track", [])
            track.append(self.localdir)
            cfg["track"] = list(set(track))
            cfg.write()

    def untrack(self):
        with self._track_lock.acquire(timeout=60):
            cfg = ConfigObj(self.FOOLSCRATE_CONFIG_PATH, unrepr=True, write_empty_values=True)
            cfg.setdefault("track", []).remove(self.localdir)
            cfg.write()

    @classmethod
    def configure_client_id(cls, git):
        client_id = 'foolscrate-' + gethostname() + "-" + "".join(
            choice(string.ascii_lowercase + string.digits) for _ in range(5))
        git.cmd('config', '--local', 'foolscrate.client-id', client_id)
        return client_id

    @classmethod
    def _align_client_ref_to_master(cls, git, client_id):
        return git.cmd('update-ref', "refs/heads/{}".format(client_id), 'master')

    @classmethod
    def sync_all_tracked(cls):
        with cls._track_lock.acquire(timeout=60):
            cls._logger.debug("Now syncing all tracked repositories")
            try:
                cfg = ConfigObj(cls.FOOLSCRATE_CONFIG_PATH, unrepr=True, write_empty_values=True)
                tracked = cfg.get("track", [])
            except FileNotFoundError as e:
                # TODO: check whether it really is meaningful with configobj
                cls._logger.debug("file not found while opening foolscrate config file", e)
                return

        # shuffle the order in which we sync repos, AND send a bit of random delay;
        # this should improve on the hammering issue.
        shuffle(tracked)
        for localdir in tracked:
            try:
                repo = Repository(localdir)
                delay = uniform(cls._SLEEP_BETWEEN_SYNC_ALL_TRACKED_ATTEMPTS_MIN_SECONDS, cls._SLEEP_BETWEEN_SYNC_ALL_TRACKED_ATTEMPTS_MAX_SECONDS)
                sleep(delay)
                repo.sync()
                cls._logger.info("synced '%s'", localdir)
            except Exception as e:
                cls._logger.exception("Error while syncing '%s'", localdir)

    @classmethod
    def enable_foolscrate_cronjob(cls, foolscrate_executable=None, crontab_command=Crontab()):
        if foolscrate_executable is None:
            # we try to determine where our launch script is located. this is mostly heuristic, so far.
            # we suppose it's in the same dir as our executable since we work within a virtualenv
            python_interpreter_dir = os.path.dirname(sys.executable)
            foolscrate_executable = join(python_interpreter_dir, "foolscrate")

        if not os.access(foolscrate_executable, os.R_OK | os.X_OK):
            raise ValueError("Check your install; invalid foolscrate executable: '{}' ".format(foolscrate_executable))

        cron_start = "{} start\n".format(cls.FOOLSCRATE_CRONTAB_COMMENT)
        cron_end = "{} end\n".format(cls.FOOLSCRATE_CRONTAB_COMMENT)
        try:
            old_crontab = crontab_command.cmd("-l")
        except CalledProcessError:
            old_crontab = ""
        cron_pattern = re_compile("{}.*?{}".format(cron_start, cron_end), RE_DOTALL)
        old_crontab = cron_pattern.sub("", old_crontab)

        if len(old_crontab) > 0 and (old_crontab[-1] != "\n"):
            old_crontab += "\n"


        # I don't know if this locale approach is sound... but seems to work on macos,
        # at least
        new_crontab = old_crontab + \
                cron_start + \
                "*/5 * * * * LANG={} {} sync_all_tracked\n".format(shell_quote(_find_suitable_utf8_locale()), shell_quote(foolscrate_executable)) + \
                      cron_end

        with NamedTemporaryFile(prefix="foolscrate-temp", mode="w+", encoding="utf-8") as tmp:
            tmp.write(new_crontab)
            tmp.flush()
            crontab_command.cmd(tmp.name)

    @classmethod
    def cleanup_tracked(cls):
        cfg = ConfigObj(cls.FOOLSCRATE_CONFIG_PATH, unrepr=True, write_empty_values=True)
        still_to_be_tracked = [directory for directory in cfg["track"] if exists(directory)]
        cfg["track"] = still_to_be_tracked
        cfg.write()

    @classmethod
    def test(cls):
        raise NotImplementedError("not yet implemented")


# this is to workaround click madness.. hope to remove it in the future.
# it actually mimics what click._unicodefun itself does..
# see https://github.com/pallets/click/issues/448
def _find_suitable_utf8_locale():
    rv = Popen(['locale', '-a'], stdout=PIPE, stderr=PIPE).communicate()[0]
    good_locales = set()

    # Make sure we're operating on text here.
    if isinstance(rv, bytes):
        rv = rv.decode('ascii', 'replace')

    for line in rv.splitlines():
        locale = line.strip()
        if locale.lower() in good_locales:
            continue
        if locale.lower().endswith(('.utf-8', '.utf8')):
            if locale.lower() in ('c.utf8', 'c.utf-8'):
                # click says that c.utf8 is the best locale ever,
                # so if we encounter it, we use it immediately.
                return locale
            else:
                good_locales.add(locale)

    if not good_locales:
        raise ValueError("could not find any utf8 enabled locale on this system")

    # just anyone will do, since ASCII would work perfectly fine as well.
    return good_locales.pop()


