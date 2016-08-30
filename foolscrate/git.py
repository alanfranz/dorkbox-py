# -*- coding: utf-8 -*-
from subprocess import check_output, PIPE

from os.path import abspath, join


class Git(object):
    def __init__(self, root_repository_dir):
        self._root_repository_dir = root_repository_dir
        self._git_command = self._generate_git_command(root_repository_dir)
        self.cmd("status")

    @classmethod
    def _generate_git_command(cls, local_directory):
        abs_local_directory = abspath(local_directory)
        gitdir = join(abs_local_directory, ".git")
        return ["git", "--work-tree={}".format(abs_local_directory), "--git-dir={}".format(gitdir)]

    def cmd(self, *args):
        return check_output(self._git_command + list(args), universal_newlines=True, stderr=PIPE)

    @classmethod
    def init(self, root_repository_dir):
        """Performs the actual 'git init' command"""
        path = abspath(root_repository_dir)
        cmd = ["git", "init", path]
        check_output(cmd)
        return Git(path)
