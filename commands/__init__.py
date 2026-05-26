"""
Register all slash commands onto the given CommandTree.

Player commands (top-level):  /premonition  /myvisions  /myjournal  /help
ST commands (top-level):      /setup  /settings
ST command groups:            /thread  /vision  /config
"""

from discord import app_commands

# ── Player commands ───────────────────────────────────────────────────────────
from commands.premonition import premonition
from commands.my_visions import my_visions
from commands.my_journal import my_journal
from commands.help import zillah_help

# ── ST top-level ──────────────────────────────────────────────────────────────
from commands.setup import setup
from commands.settings import settings

# ── /thread group ─────────────────────────────────────────────────────────────
from commands.assign_thread import assign_thread
from commands.thread_status import thread_status
from commands.end_thread import end_thread
from commands.thread_pool import thread_pool
from commands.add_motif import add_motif
from commands.reset_thread_pool import reset_thread_pool

# ── /vision group ─────────────────────────────────────────────────────────────
from commands.send_vision import send_vision
from commands.vision_log import vision_log
from commands.set_weights import set_weights
from commands.reset_weights import reset_weights
from commands.vision_test import vision_test

# ── /config group ─────────────────────────────────────────────────────────────
from commands.set_channel import set_channel
from commands.set_cooldown import set_cooldown
from commands.reset_cooldown import reset_cooldown
from commands.clear_symbols import clear_symbols


def register_all(tree: app_commands.CommandTree) -> None:
    # ── Player top-level ──────────────────────────────────────────────────────
    tree.add_command(premonition)
    tree.add_command(my_visions)
    tree.add_command(my_journal)
    tree.add_command(zillah_help)

    # ── ST top-level ──────────────────────────────────────────────────────────
    tree.add_command(setup)
    tree.add_command(settings)

    # ── /thread ───────────────────────────────────────────────────────────────
    thread_group = app_commands.Group(
        name="thread", description="Vision thread management (ST)"
    )
    thread_group.add_command(assign_thread)
    thread_group.add_command(thread_status)
    thread_group.add_command(end_thread)
    thread_group.add_command(thread_pool)
    thread_group.add_command(add_motif)
    thread_group.add_command(reset_thread_pool)
    tree.add_command(thread_group)

    # ── /vision ───────────────────────────────────────────────────────────────
    vision_group = app_commands.Group(
        name="vision", description="Vision tools for Storytellers"
    )
    vision_group.add_command(send_vision)
    vision_group.add_command(vision_log)
    vision_group.add_command(set_weights)
    vision_group.add_command(reset_weights)
    vision_group.add_command(vision_test)
    tree.add_command(vision_group)

    # ── /config ───────────────────────────────────────────────────────────────
    config_group = app_commands.Group(
        name="config", description="Server configuration (ST)"
    )
    config_group.add_command(set_channel)
    config_group.add_command(set_cooldown)
    config_group.add_command(reset_cooldown)
    config_group.add_command(clear_symbols)
    tree.add_command(config_group)
