# -*- coding: utf-8 -*-
from os.path import expanduser, join


LOCKFILE_NAME = '.dorkbox.lock'
CONFLICT_STRING = 'CONFLICT_MUST_MANUALLY_MERGE'
GITIGNORE = '.gitignore'
DORKBOX_CONFIG_PATH = join(expanduser("~"), ".dorkbox.conf")
DORKBOX_CONFIG_LOCK = DORKBOX_CONFIG_PATH + '.lock'
DORKBOX_CRONTAB_COMMENT = '# dorkbox sync cronjob'



class InterProcessLock(object):
    def __init__(self, lock_path):

    def initialize(lock_path)
      @lock_path = lock_path
    end

    def exclusive(&block)
      if block.nil?
        raise ArgumentError, "Block is mandatory"
      end

      lockfile = File.open(@lock_path, File::RDWR|File::CREAT, 0644)
      lockfile.flock(File::LOCK_EX)
      begin
        block.call()
      ensure
        lockfile.flock(File::LOCK_UN)
        lockfile.close()
      end
    end
  end