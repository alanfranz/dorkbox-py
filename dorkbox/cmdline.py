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


