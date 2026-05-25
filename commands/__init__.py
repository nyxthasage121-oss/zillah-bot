"""
Register all slash commands onto the given CommandTree.
"""

from discord import app_commands

from commands.setup import setup
from commands.set_channel import set_channel
from commands.premonition import premonition
from commands.assign_thread import assign_thread
from commands.thread_status import thread_status
from commands.add_motif import add_motif
from commands.send_vision import send_vision
from commands.vision_log import vision_log
from commands.set_weights import set_weights
from commands.set_cooldown import set_cooldown
from commands.my_visions import my_visions
from commands.my_journal import my_journal


def register_all(tree: app_commands.CommandTree) -> None:
    tree.add_command(setup)
    tree.add_command(set_channel)
    tree.add_command(premonition)
    tree.add_command(assign_thread)
    tree.add_command(thread_status)
    tree.add_command(add_motif)
    tree.add_command(send_vision)
    tree.add_command(vision_log)
    tree.add_command(set_weights)
    tree.add_command(set_cooldown)
    tree.add_command(my_visions)
    tree.add_command(my_journal)
