"""
Register all slash commands onto the given CommandTree.
"""

from discord import app_commands

from commands import setup as _setup_mod
from commands import set_channel as _set_channel_mod
from commands import premonition as _premonition_mod


def register_all(tree: app_commands.CommandTree, anthropic_client) -> None:
    # Inject the Anthropic client into the premonition module before registering.
    _premonition_mod.anthropic_client = anthropic_client

    tree.add_command(_setup_mod.setup)
    tree.add_command(_set_channel_mod.set_channel)
    tree.add_command(_premonition_mod.premonition)
