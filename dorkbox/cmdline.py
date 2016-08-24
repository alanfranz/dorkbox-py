import click
from dorkbox import dorkbox

@click.group()
def cmdline():
    pass

@cmdline.command()
@click.argument("directory")
@click.argument("dorkbox_remote_url")
def create(directory, dorkbox_remote_url):
    dorkbox.Repository.create_new(directory, dorkbox_remote_url)

@cmdline.command()
@click.argument("directory")
@click.argument("dorkbox_remote_url")
def connect(directory, dorkbox_remote_url):
    dorkbox.Repository.connect_existing(directory, dorkbox_remote_url)

@cmdline.command()
@click.argument("directory", default=".")
def sync(directory):
    dorkbox.Repository(directory).sync()

@cmdline.command()
@click.argument("directory", default=".")
def track(directory):
    dorkbox.Repository(directory).track()

@cmdline.command()
@click.argument("directory", default=".")
def untrack(directory):
    dorkbox.Repository(directory).untrack()

@cmdline.command()
def sync_all_tracked():
    dorkbox.Repository.sync_all_tracked()

@cmdline.command()
def enable_autosync_all_tracked():
    dorkbox.Repository.enable_dorkbox_cronjob()


