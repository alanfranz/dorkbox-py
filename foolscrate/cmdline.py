# -*- coding: utf-8 -*-
from os.path import expanduser
from os.path import join

import click

from foolscrate import foolscrate

config_broker = foolscrate.ConfigBroker(join(expanduser("~"), ".foolscrate.conf"), join(expanduser("~"), ".foolscrate.conf.lock"))

@click.group()
def cmdline():
    pass


@cmdline.command()
@click.argument("directory")
@click.argument("remote_url")
def create(directory, remote_url):
    foolscrate.Repository.create_new(directory, remote_url, config_broker)


@cmdline.command()
@click.argument("directory")
@click.argument("remote_url")
def connect(directory, remote_url):
    foolscrate.Repository.connect_existing(directory, remote_url, config_broker)


@cmdline.command()
@click.argument("directory", default=".")
def sync(directory):
    foolscrate.Repository(directory, config_broker).sync()


@cmdline.command()
@click.argument("directory", default=".")
def track(directory):
    foolscrate.Repository(directory, config_broker).track()


@cmdline.command()
@click.argument("directory", default=".")
def untrack(directory):
    foolscrate.Repository(directory, config_broker).untrack()


@cmdline.command()
def sync_all_tracked():
    foolscrate.SyncAll(config_broker).sync_all_tracked()


@cmdline.command()
def enable_autosync_all_tracked():
    foolscrate.Repository.enable_foolscrate_cronjob()
