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


