# -*- coding: utf-8 -*-
from os.path import expanduser, join, abspath, exists, dirname
from os import access, R_OK, W_OK, X_OK
from subprocess import check_output, run as popen_run
import logging
from socket import gethostname
from shlex import quote as shell_quote
import string
from random import choice
from re import sub as re_sub, compile as re_compile, MULTILINE as RE_MULTILINE
from tempfile import NamedTemporaryFile
from configobj import ConfigObj
from filelock import FileLock
import sys

LOCKFILE_NAME = '.dorkbox.lock'
CONFLICT_STRING = 'CONFLICT_MUST_MANUALLY_MERGE'
GITIGNORE = '.gitignore'
DORKBOX_CONFIG_PATH = join(expanduser("~"), ".dorkbox.conf")
DORKBOX_CONFIG_LOCK = DORKBOX_CONFIG_PATH + '.lock'
DORKBOX_CRONTAB_COMMENT = '# dorkbox sync cronjob'


class Git(object):
    def __init__(self, root_repository_dir):
        self._root_repository_dir = root_repository_dir
        self._git_command = self.generate_git_command(root_repository_dir)
        self.cmd("status")

    @classmethod
    def generate_git_command(cls, local_directory):
        abs_local_directory = abspath(local_directory)
        gitdir = join(abs_local_directory, ".git")
        return ["git", "--work-tree={}".format(abs_local_directory), "--git-dir={}".format(gitdir)]

    def cmd(self, *args):
        return check_output(self._git_command + list(args))

    @classmethod
    def init(self, root_repository_dir):
        """Performs the actual 'git init' command"""
        path = abspath(root_repository_dir)
        check_output(["git", "init", path])
        return Git(path)


class Repository(object):
    _logger = logging.getLogger("Repository")
    _track_lock = FileLock(DORKBOX_CONFIG_LOCK)

    @classmethod
    def create_new(cls, local_directory, remote_url):
        cls._logger.info("Will create new dorkbox-enabled repository in local directory. Remote %s should exist and be empty.", remote_url)

        if exists(join(local_directory, ".git")):
            raise ValueError("Preexisting git repo found")

        git = Git.init(local_directory)
        with open(join(local_directory, GITIGNORE), "a", encoding="utf-8") as f:
            f.write(CONFLICT_STRING)
            f.write(LOCKFILE_NAME)

        git.cmd("remote", "add", "dorkbox", remote_url)
        git.cmd("add", GITIGNORE)
        git.cmd("commit", "-m", "enabling dorkbox")

        return cls.configure_repository(git, local_directory)

    @classmethod
    def configure_repository(cls, git, local_directory):
        dorkbox_client_id = cls.configure_client_id(git)
        cls._align_client_ref_to_master(git, dorkbox_client_id)
        git.cmd("push", "-u", "dorkbox", "master", dorkbox_client_id)
        repo = Repository(local_directory)
        repo.track()
        return repo

    @classmethod
    def connect_existing(cls, local_directory, remote_url):
        cls._logger.info("Will create new git repo in local directory and connect to remote existing dorkbox repository %s", remote_url)

        if exists(join(local_directory, ".git")):
            raise ValueError("Preexisting git repo found")

        git = Git.init(local_directory)
        git.cmd("remote", "add", "dorkbox", remote_url)
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
            raise ValueError("{} is not a valid dorkbox-enabled repository".format(abs_local_directory))

        # TODO: what was that alan-mayday error?

        self._git = Git(abs_local_directory)
        self.localdir = abs_local_directory
        self._conflict_string = join(abs_local_directory, CONFLICT_STRING)
        self.client_id = self._git.cmd("config", "--local", "--get", "dorkbox.client-id").strip()
        self._sync_lock = FileLock(join(self.localdir, LOCKFILE_NAME))

    def sync(self):
        with self._sync_lock.acquire(timeout=60):
            if exists(CONFLICT_STRING):
                self._logger.info("Conflict found, not syncing")
                raise ValueError("Conflict found, not syncing")

            # begin
            for _ in range(0, 5):
                self._git.cmd("fetch", "--all")
                self._git.cmd("add", "-A")
                any_change = self._git.cmd("diff", "--staged").strip()

                if any_change != "":
                    self._git.cmd("commit", "-m", "Automatic dorkbox commit")

                try:
                    self._git.cmd("merge", "--no-edit", "dorkbox/master")
                except Exception as e:
                    self._logger.exception("Error while merging")
                    continue

                self._align_client_ref_to_master(self._git, self.client_id)

                try:
                    self._git.cmd("push", "dorkbox", "master", self.client_id)
                except Exception as e:
                    self._logger.exception("Error while pushing")
                    continue

                break
            else:
                self._logger.error("Couldn't succeed at merging or pushing back our changes, probably we've got a conflict")
                with open(self._conflict_string, "w") as f:
                    pass
                return

            self._logger.info("Sync succeeded")

    def track(self):
        with self._track_lock.acquire(timeout=60):
            cfg = ConfigObj(DORKBOX_CONFIG_PATH, unrepr=True, write_empty_values=True)
            # configobj doesn't support sets natively, only lists.
            track = cfg.get("track", [])
            track.append(self.localdir)
            cfg["track"] = list(set(track))
            cfg.write()

    def untrack(self):
        with self._track_lock.acquire(timeout=60):
            cfg = ConfigObj(DORKBOX_CONFIG_PATH, unrepr=True, write_empty_values=True)
            cfg.setdefault("track", []).remove(self.localdir)
            cfg.write()

    @classmethod
    def configure_client_id(cls, git):
      dorkbox_client_id = 'dorkbox-' + gethostname() + "-" + "".join(choice(string.ascii_lowercase + string.digits) for _ in range(5))
      git.cmd('config', '--local', 'dorkbox.client-id', dorkbox_client_id)
      return dorkbox_client_id

    @classmethod
    def _align_client_ref_to_master(cls, git, dorkbox_client_id):
       return git.cmd('update-ref', "refs/heads/{}".format(dorkbox_client_id), 'master')


    @classmethod
    def sync_all_tracked(cls):
        with cls._track_lock.acquire(timeout=60):
            try:
                cfg = ConfigObj(DORKBOX_CONFIG_PATH, unrepr=True, write_empty_values=True)
            except FileNotFoundError as e:
                # TODO: check whether it really is meaningful with configobj
                cls._logger.debug("file not found while opening dorkbox config file", e)
                for localdir in cfg.get("track", []):
                    try:
                        repo = Repository(localdir)
                        repo.sync()
                    except Exception as e:
                        cls._logger.exception("Error while syncing '%s'", localdir)

    @classmethod
    def enable_dorkbox_cronjob(cls, executable=join(dirname(abspath(__file__)), "devenv", "bin", "dorkbox")):
        cron_start = "{} start\n".format(DORKBOX_CRONTAB_COMMENT)
        cron_end = "{} end\n".format(DORKBOX_CRONTAB_COMMENT)
        old_crontab = popen_run(["crontab", "-l"]).stdout
        old_crontab = re_sub(re_compile("{}.*?{}".format(cron_start, cron_end), RE_MULTILINE), "", old_crontab)

        if len(old_crontab) > 0 and (old_crontab[-1] != "\n"):
            old_crontab += "\n"

        new_crontab = old_crontab + cron_start + "*/5 * * * * {}".format(shell_quote(executable) + " sync_all_tracked\n") + cron_end

        with NamedTemporaryFile(prefix="dorkbox-temp", encoding="utf-8") as tmp:
            tmp.puts(new_crontab)
            tmp.flush()
            check_output(["crontab", tmp.name])

    @classmethod
    def cleanup_tracked(cls):
        cfg = ConfigObj(DORKBOX_CONFIG_PATH, unrepr=True, write_empty_values=True)
        still_to_be_tracked = [directory for directory in cfg["track"] if exists(directory)]
        cfg["track"] = still_to_be_tracked
        cfg.write()

    @classmethod
    def test(cls):
        raise NotImplementedError("not yet implemented")


def cmdline():
    # TODO: improve this with the right library, e.g. click
    commands = ["test", "enable_autosync_all_tracked", "sync_all_tracked", "track", "untrack", "create", "connect"]
    command = sys.argv[1]
    if command not in commands:
        raise ValueError("unknown command '{}'".format(command))

