Work in progress

## TODO:

* verify proper authentication and/or remote host validation (ssh/https) to prevent issues that just kill
  the tool
* sync crontab: when using head version or a versioned directory, the autosync must be forced after updates
  otherwise might not work
* mac homebrew version: update autosync link after install if it's there - it contains the full path to the executable which includes the version
* see if libgit2 makes the tool faster
* the 5-minute cron is slow and has the sync-at-the-same-time effect. consider reducing the cron and introducing an optional random delay
  option for the sync_all_tracked command
* something like inotify on linux instead of cron?
