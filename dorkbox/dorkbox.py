# -*- coding: utf-8 -*-
from os.path import expanduser, join, abspath, exists
from os import access, R_OK, W_OK, X_OK
from subprocess import check_output
import logging
from socket import gethostname
import string
from random import choice

from configobj import ConfigObj
from filelock import FileLock

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
        dorkbox_client_id = cls._configure_client_id(git)
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
        self._track_lock = FileLock(DORKBOX_CONFIG_LOCK)

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
            track.add(self.localdir)
            cfg["track"] = list(set(track))
            cfg.write()

    def untrack(self):
        with self._track_lock.acquire(timeout=60):
            cfg = ConfigObj(DORKBOX_CONFIG_PATH, unrepr=True, write_empty_values=True)
            cfg.setdefault("track", []).remove(self.localdir)
            cfg.write()

    @classmethod
    def configure_client_id(git):
      dorkbox_client_id = 'dorkbox-' + gethostname() + "-" + "".join(choice(string.ascii_lowercase + string.digits) for _ in range(5))
      git.cmd('config', '--local', 'dorkbox.client-id', dorkbox_client_id)
      return dorkbox_client_id

    @classmethod
    def _align_client_ref_to_master(git, dorkbox_client_id):
       git.cmd('update-ref', "refs/heads/{}".format(dorkbox_client_id), 'master')


#   def self.sync_all_tracked
#     begin
#       cfg = YAML.load_file(DORKBOX_CONFIG_PATH)
#     rescue Errno::ENOENT
#       return
#     end
#     # TODO: don't crash if one syncing fails!
#     cfg[:track].each { |d|
#       begin
#         Repository.new(d).sync()
#       rescue
#         log "Error while syncing repository #{d}"
#       end
#     }
#   end
#
#   def self.enable_dorkbox_cronjob(executable=File.join(File.dirname(File.expand_path(__FILE__)), '..', 'bin', 'dorkbox'))
#
#     cron_start = "#{DORKBOX_CRONTAB_COMMENT} start\n"
#     cron_end = "#{DORKBOX_CRONTAB_COMMENT} end\n"
#     old_crontab = c('crontab -l 2>/dev/null || true')
#     old_crontab.sub!(/#{cron_start}.*?#{cron_end}/m, '')
#
#     tmp = Tempfile.new("dorkbox-temp")
#     if (old_crontab.size > 0) && (old_crontab[-1] != "\n")
#       old_crontab.concat("\n")
#     end
#
#     old_crontab.concat(cron_start).concat("*/5 * * * * #{Shellwords.escape(executable)} sync_all_tracked\n").concat(cron_end)
#     tmp.puts(old_crontab)
#     tmp.flush()
#     `crontab #{tmp.path}`
#     tmp.close()
#   end
#
#   def self.cleanup_tracked
#     begin
#       cfg = YAML.load_file(DORKBOX_CONFIG_PATH)
#     rescue Errno::ENOENT
#       return
#     end
#     # TODO: check for dorkbox-enabled dir, e.g. try retrieving client id
#     cfg[:track].select! { |d| Dir.exists?(d) }
#     puts cfg
#     File.open(DORKBOX_CONFIG_PATH, 'w') { |f| f.write(cfg.to_yaml) }
#   end
#
#
#   def self.test
#     require 'dorkbox_test'
#     MiniTest::Unit.autorun
#   end
#
# end