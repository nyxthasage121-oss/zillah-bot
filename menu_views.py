"""
Views and modals for the /visionmenu command.

MainMenuView        — top-level Player / Storyteller split
PlayerMenuView      — Seek a Vision, My Visions, My Journal
STMenuView          — select dropdown for all ST actions
STPlayerSelectView  — UserSelect picker reused for assign/end/reset flows
STEndThreadConfirmView — confirm before closing a thread
SendVisionModal     — collect target + vision parameters via modal
AssignThreadModal   — collect motif + duration via modal
"""

import asyncio
import functools
import logging
import random
from datetime import datetime, timezone

import discord

import clients
import db
from config import (
    CLAUDE_MODEL,
    VISION_EMBED_COLOR,
    ST_EMBED_COLOR,
    VISION_ALL_TYPES,
)
from utils import get_clan_flavor, get_elapsed_nights, has_mod_permission
from views import JournalView, VisionHistoryView, _run_symbol_detection

logger = logging.getLogger("zillah.menu_views")

_ST_VISION_TYPES = [t for t in VISION_ALL_TYPES if t != "Lucid Vision"]
_VALID_SOURCES = {"AI Generated", "ST Written", "ST Prompted"}


# ── Modals ────────────────────────────────────────────────────────────────────

class SendVisionModal(discord.ui.Modal, title="Send Vision"):
    target_input = discord.ui.TextInput(
        label="Target",
        placeholder="Player display name  or  @Role name",
    )
    vision_type_input = discord.ui.TextInput(
        label="Vision Type",
        placeholder="Random, Standard Vision, Glitch Vision…",
        default="Random",
    )
    source_input = discord.ui.TextInput(
        label="Source",
        placeholder="AI Generated, ST Written, ST Prompted",
        default="AI Generated",
    )
    custom_text_input = discord.ui.TextInput(
        label="Custom Text (optional)",
        style=discord.TextStyle.paragraph,
        required=False,
        placeholder="Vision text (ST Written) or custom prompt (ST Prompted)…",
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        config = db.get_server_config(guild_id)
        if not config:
            await interaction.followup.send("Server not configured.", ephemeral=True)
            return

        auspex_role_id = str(config[0])

        # ── Resolve target ────────────────────────────────────────────────────
        target_str = self.target_input.value.strip()
        players: list[discord.Member] = []

        if target_str.startswith("@"):
            role_name = target_str[1:].lower()
            role = discord.utils.find(
                lambda r: r.name.lower() == role_name, interaction.guild.roles
            )
            if not role:
                await interaction.followup.send(
                    f"Role `{target_str}` not found.", ephemeral=True
                )
                return
            players = [
                m for m in role.members
                if auspex_role_id in [str(r.id) for r in m.roles]
            ]
            if not players:
                await interaction.followup.send(
                    "No Auspex members found in that role.", ephemeral=True
                )
                return
        else:
            member = discord.utils.find(
                lambda m: (
                    m.display_name.lower() == target_str.lower()
                    or m.name.lower() == target_str.lower()
                ),
                interaction.guild.members,
            )
            if not member:
                await interaction.followup.send(
                    f"Player `{target_str}` not found. "
                    f"Use their exact display name, or `@RoleName` for a role.",
                    ephemeral=True,
                )
                return
            players = [member]

        # ── Parse vision type ─────────────────────────────────────────────────
        vt_str = self.vision_type_input.value.strip()
        if vt_str.lower() in ("random", ""):
            vision_type = "Random"
        elif vt_str in VISION_ALL_TYPES and vt_str != "Lucid Vision":
            vision_type = vt_str
        else:
            await interaction.followup.send(
                f"Unknown vision type `{vt_str}`. "
                f"Use Random or one of the 8 standard types (Lucid Vision excluded).",
                ephemeral=True,
            )
            return

        # ── Parse source ──────────────────────────────────────────────────────
        source = next(
            (s for s in _VALID_SOURCES if s.lower() == self.source_input.value.strip().lower()),
            None,
        )
        if not source:
            await interaction.followup.send(
                "Source must be `AI Generated`, `ST Written`, or `ST Prompted`.",
                ephemeral=True,
            )
            return

        custom_text = self.custom_text_input.value.strip() or None
        if source in ("ST Written", "ST Prompted") and not custom_text:
            await interaction.followup.send(
                f"Custom Text is required for source **{source}**.", ephemeral=True
            )
            return

        # ── Post channel ──────────────────────────────────────────────────────
        premonition_channel_id = config[2]
        post_channel = (
            interaction.guild.get_channel(int(premonition_channel_id))
            if premonition_channel_id
            else interaction.channel
        )
        if not post_channel:
            await interaction.followup.send(
                "Could not find the premonition channel. Check /config channel.",
                ephemeral=True,
            )
            return

        # ── Generate and send ─────────────────────────────────────────────────
        from commands.send_vision import _generate_vision

        now = datetime.now(timezone.utc)
        sent = 0
        errors = 0

        for player in players:
            chosen_type = (
                random.choice(_ST_VISION_TYPES) if vision_type == "Random" else vision_type
            )
            try:
                vision_text = await _generate_vision(chosen_type, source, custom_text)
            except Exception as e:
                logger.error(
                    "menu send_vision generation error for %s: %s", player.id, e, exc_info=True
                )
                errors += 1
                continue

            clan_flavor = get_clan_flavor(player.roles)
            desc = f"*{clan_flavor}*\n\n*{vision_text}*" if clan_flavor else f"*{vision_text}*"
            embed = discord.Embed(description=desc, color=ST_EMBED_COLOR)
            embed.set_footer(text=f"{chosen_type} · ST Sent")
            embed.set_author(name=player.display_name)

            try:
                await post_channel.send(embed=embed)
            except Exception as e:
                logger.error(
                    "menu send_vision post error for %s: %s", player.id, e, exc_info=True
                )
                errors += 1
                continue

            db.save_vision(
                guild_id, str(player.id), chosen_type, vision_text,
                now.isoformat(), is_st_triggered=True,
            )
            asyncio.create_task(_run_symbol_detection(guild_id, str(player.id)))
            sent += 1

        summary = f"Vision(s) sent: **{sent}**"
        if errors:
            summary += f" | Errors: {errors}"
        await interaction.followup.send(summary, ephemeral=True)


class AssignThreadModal(discord.ui.Modal, title="Assign Vision Thread"):
    motif = discord.ui.TextInput(
        label="Motif",
        placeholder="e.g. the drowned bell",
        max_length=100,
    )
    duration = discord.ui.TextInput(
        label="Duration (nights, 1–30)",
        placeholder="e.g. 5",
        max_length=2,
    )

    def __init__(self, player: discord.Member, guild_id: str) -> None:
        super().__init__()
        self.player = player
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            duration_nights = int(self.duration.value.strip())
            if not (1 <= duration_nights <= 30):
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "Duration must be a whole number between 1 and 30.", ephemeral=True
            )
            return

        motif = self.motif.value.strip()
        user_id = str(self.player.id)
        now_iso = datetime.now(timezone.utc).isoformat()

        existing = db.get_active_thread(self.guild_id, user_id)
        if existing:
            db.deactivate_thread(self.guild_id, user_id)
            prefix = "⚠️ Previous thread overwritten. "
        else:
            prefix = ""

        db.create_thread(self.guild_id, user_id, motif, duration_nights, True, now_iso)
        await interaction.response.send_message(
            f"{prefix}Thread assigned to **{self.player.display_name}**.\n"
            f"Motif: *{motif}* · {duration_nights} nights.\n"
            f"*(Player has not been notified.)*",
            ephemeral=True,
        )


# ── ST helper views ───────────────────────────────────────────────────────────

class STEndThreadConfirmView(discord.ui.View):
    """Confirm / cancel before closing a player's active thread."""

    def __init__(self, player: discord.Member, thread: dict, guild_id: str) -> None:
        super().__init__(timeout=60)
        self.player = player
        self.thread = thread
        self.guild_id = guild_id

    @discord.ui.button(label="End Thread", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        db.deactivate_thread(self.guild_id, str(self.player.id))
        source = "ST-assigned" if self.thread["is_st_assigned"] else "auto-triggered"
        self.stop()
        await interaction.response.edit_message(
            content=(
                f"Thread closed for **{self.player.display_name}**.\n"
                f"The {source} motif *{self.thread['motif']}* "
                f"will no longer appear in their visions."
            ),
            embed=None,
            view=None,
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.stop()
        await interaction.response.edit_message(content="Cancelled.", embed=None, view=None)


class STPlayerSelectView(discord.ui.View):
    """UserSelect picker reused for assign / end / reset actions."""

    def __init__(self, action: str, guild_id: str) -> None:
        super().__init__(timeout=60)
        self.action = action
        self.guild_id = guild_id

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select a player…",
        min_values=1,
        max_values=1,
    )
    async def player_select(
        self, interaction: discord.Interaction, select: discord.ui.UserSelect
    ) -> None:
        player = select.values[0]

        if self.action == "assign":
            await interaction.response.send_modal(
                AssignThreadModal(player, self.guild_id)
            )

        elif self.action == "end":
            thread = db.get_active_thread(self.guild_id, str(player.id))
            if not thread:
                await interaction.response.send_message(
                    f"**{player.display_name}** has no active vision thread.",
                    ephemeral=True,
                )
                return
            embed = discord.Embed(
                title="End Vision Thread?",
                description=(
                    f"**{player.display_name}** · "
                    f"{'ST-assigned' if thread['is_st_assigned'] else 'Auto'}\n"
                    f"Motif: *{thread['motif']}*\n\n"
                    f"This cannot be undone."
                ),
                color=0xFF8C00,
            )
            view = STEndThreadConfirmView(player, thread, self.guild_id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        elif self.action == "reset":
            now_iso = datetime.now(timezone.utc).isoformat()
            cooldown = db.get_cooldown(self.guild_id, str(player.id))
            if cooldown and cooldown[0] > 0:
                db.reset_cooldown(self.guild_id, str(player.id), now_iso)
                await interaction.response.send_message(
                    f"The veil parts once more. **{player.display_name}**'s sight has been restored.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"**{player.display_name}** has no uses this night — already free to seek visions.",
                    ephemeral=True,
                )


# ── ST Panel ──────────────────────────────────────────────────────────────────

class STMenuView(discord.ui.View):
    def __init__(self, guild_id: str) -> None:
        super().__init__(timeout=120)
        self.guild_id = guild_id

    @discord.ui.select(
        placeholder="Select an action…",
        options=[
            discord.SelectOption(label="Send Vision", emoji="👁", description="Send a vision to a player or role"),
            discord.SelectOption(label="Assign Thread", emoji="🩸", description="Assign a vision motif thread to a player"),
            discord.SelectOption(label="End Thread", emoji="✂️", description="Close a player's active vision thread"),
            discord.SelectOption(label="Reset Cooldown", emoji="🔄", description="Restore a player's sight for tonight"),
            discord.SelectOption(label="View Threads", emoji="📋", description="See all active vision threads"),
            discord.SelectOption(label="Settings", emoji="⚙️", description="View server configuration"),
        ],
        row=0,
    )
    async def action_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        action = select.values[0]
        guild_id = str(interaction.guild_id)

        if action == "Send Vision":
            await interaction.response.send_modal(SendVisionModal())

        elif action == "Assign Thread":
            await interaction.response.send_message(
                "Select a player to assign a thread to:",
                view=STPlayerSelectView("assign", guild_id),
                ephemeral=True,
            )

        elif action == "End Thread":
            await interaction.response.send_message(
                "Select a player whose thread to close:",
                view=STPlayerSelectView("end", guild_id),
                ephemeral=True,
            )

        elif action == "Reset Cooldown":
            await interaction.response.send_message(
                "Select a player to restore:",
                view=STPlayerSelectView("reset", guild_id),
                ephemeral=True,
            )

        elif action == "View Threads":
            config = db.get_server_config(guild_id)
            night_length_days = config[5] or 14
            sundown_time = config[6] or "20:00"
            sundown_timezone = config[7] or "EST"
            threads = db.get_all_active_threads(guild_id)
            embed = discord.Embed(title="Active Vision Threads", color=VISION_EMBED_COLOR)
            lines = []
            for t in threads:
                elapsed = get_elapsed_nights(
                    t["start_timestamp"], night_length_days, sundown_time, sundown_timezone
                )
                if elapsed >= t["duration_nights"]:
                    db.deactivate_thread(guild_id, t["user_id"])
                    continue
                member = interaction.guild.get_member(int(t["user_id"]))
                name = member.display_name if member else f"User {t['user_id']}"
                remaining = t["duration_nights"] - elapsed
                source = "ST" if t["is_st_assigned"] else "Auto"
                lines.append(
                    f"**{name}** · {source}\n*{t['motif']}*\n{remaining} night(s) remaining"
                )
            embed.description = "\n\n".join(lines) if lines else "No active vision threads."
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "Settings":
            config = db.get_server_config(guild_id)
            auspex_role = interaction.guild.get_role(int(config[0])) if config[0] else None
            mod_role = interaction.guild.get_role(int(config[1])) if config[1] else None
            channel = interaction.guild.get_channel(int(config[2])) if config[2] else None
            embed = discord.Embed(title="Zillah — Server Settings", color=VISION_EMBED_COLOR)
            embed.add_field(
                name="Roles",
                value=(
                    f"Auspex: {auspex_role.mention if auspex_role else '*(not set)*'}\n"
                    f"Mod: {mod_role.mention if mod_role else '*(not set)*'}"
                ),
                inline=False,
            )
            embed.add_field(
                name="Channel",
                value=channel.mention if channel else "*(any channel)*",
                inline=False,
            )
            embed.add_field(
                name="Night Cycle",
                value=(
                    f"Length: **{config[5] or 14} days** · Uses: **{config[3]}/night**\n"
                    f"Sundown: **{config[6] or '20:00'} {config[7] or 'EST'}**"
                ),
                inline=False,
            )
            weights = db.get_vision_weights(guild_id)
            if weights:
                total = sum(w for _, w in weights)
                top = sorted(weights, key=lambda x: -x[1])[:4]
                lines = [f"{vt}: **{w / total * 100:.0f}%**" for vt, w in top]
                if len(weights) > 4:
                    lines.append(f"*+ {len(weights) - 4} more — see /vision weights*")
                embed.add_field(name="Vision Weights (top)", value="\n".join(lines), inline=False)
            pool = db.get_thread_pool(guild_id)
            embed.add_field(
                name="Thread Pool",
                value=f"**{len(pool)}** motif(s) — see /thread pool",
                inline=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="← Back", style=discord.ButtonStyle.secondary, row=1)
    async def back(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        embed = discord.Embed(
            title="🌙 Zillah",
            description="What do you seek, Kindred?",
            color=VISION_EMBED_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=MainMenuView())


# ── Player Menu ───────────────────────────────────────────────────────────────

class PlayerMenuView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=120)

    @discord.ui.button(label="Seek a Vision", style=discord.ButtonStyle.primary, row=0)
    async def seek_vision(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        from commands.premonition import run_premonition
        await run_premonition(interaction)

    @discord.ui.button(label="My Visions", style=discord.ButtonStyle.secondary, row=0)
    async def my_visions(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        view = VisionHistoryView(
            guild_id=str(interaction.guild_id),
            user_id=str(interaction.user.id),
            title="Your Vision History",
        )
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)

    @discord.ui.button(label="My Journal", style=discord.ButtonStyle.secondary, row=0)
    async def my_journal(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        view = JournalView(
            guild_id=str(interaction.guild_id),
            user_id=str(interaction.user.id),
        )
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)

    @discord.ui.button(label="← Back", style=discord.ButtonStyle.secondary, row=1)
    async def back(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        embed = discord.Embed(
            title="🌙 Zillah",
            description="What do you seek, Kindred?",
            color=VISION_EMBED_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=MainMenuView())


# ── Main Menu ─────────────────────────────────────────────────────────────────

class MainMenuView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=120)

    @discord.ui.button(label="Player", style=discord.ButtonStyle.secondary, row=0)
    async def player(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        embed = discord.Embed(
            title="🌙 Player Actions",
            description="Choose what you wish to do.",
            color=VISION_EMBED_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=PlayerMenuView())

    @discord.ui.button(label="Storyteller", style=discord.ButtonStyle.secondary, row=0)
    async def storyteller(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        guild_id = str(interaction.guild_id)
        config = db.get_server_config(guild_id)
        if not config or not has_mod_permission(interaction, str(config[1])):
            await interaction.response.send_message(
                "The Storyteller panel is restricted to mods and administrators.",
                ephemeral=True,
            )
            return
        embed = discord.Embed(
            title="🩸 Storyteller Panel",
            description="Select an action to perform.",
            color=0xED4245,
        )
        await interaction.response.edit_message(embed=embed, view=STMenuView(guild_id))
