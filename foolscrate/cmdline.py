# -*- coding: utf-8 -*-
import click
from foolscrate import foolscrate


@click.group()
def cmdline():
    pass


@cmdline.command()
@click.argument("directory")
@click.argument("remote_url")
def create(directory, remote_url):
    foolscrate.Repository.create_new(directory, remote_url)


@cmdline.command()
@click.argument("directory")
@click.argument("remote_url")
def connect(directory, remote_url):
    foolscrate.Repository.connect_existing(directory, remote_url)


@cmdline.command()
@click.argument("directory", default=".")
def sync(directory):
    foolscrate.Repository(directory).sync()


@cmdline.command()
@click.argument("directory", default=".")
def track(directory):
    foolscrate.Repository(directory).track()


@cmdline.command()
@click.argument("directory", default=".")
def untrack(directory):
    foolscrate.Repository(directory).untrack()


@cmdline.command()
def sync_all_tracked():
    foolscrate.Repository.sync_all_tracked()


@cmdline.command()
def enable_autosync_all_tracked():
    foolscrate.Repository.enable_foolscrate_cronjob()
