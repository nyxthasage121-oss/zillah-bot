"""
All discord.ui.View subclasses plus shared background task helpers.

Background helpers (_run_symbol_detection, _try_auto_thread) are imported
by commands/premonition.py so they run for both regular and Lucid visions.
"""

import asyncio
import functools
import json
import random
from datetime import datetime, timezone

import discord

import clients
import db
from config import (
    AUTO_THREAD_CHANCE,
    AUTO_THREAD_MAX_DURATION,
    AUTO_THREAD_MIN_DURATION,
    CLAUDE_MODEL,
    SYMBOL_DETECTION_COUNT,
    SYMBOL_MIN_VISIONS,
    VISION_EMBED_COLOR,
)


# ── Background task helpers ───────────────────────────────────────────────────

async def _run_symbol_detection(guild_id: str, user_id: str) -> None:
    """Scan recent visions for recurring symbols. Silent failure — never blocks the player."""
    try:
        texts = db.get_recent_visions_text(guild_id, user_id, SYMBOL_DETECTION_COUNT)
        if len(texts) < SYMBOL_MIN_VISIONS:
            return

        numbered = "\n".join(f"{i + 1}. {v}" for i, v in enumerate(texts))
        prompt = (
            "Analyze these vision fragments from a Vampire: The Masquerade player. "
            "Identify symbols, images, or motifs that appear in more than one vision.\n\n"
            f"Visions:\n{numbered}\n\n"
            "Return ONLY a JSON array of recurring symbol names (2-4 words each). "
            'If none found, return []. Example: ["red door", "drowned figure"]'
        )

        response = await asyncio.to_thread(
            functools.partial(
                clients.client.messages.create,
                model=CLAUDE_MODEL,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
        )
        text = response.content[0].text.strip()
        start, end = text.find("["), text.rfind("]") + 1
        if start == -1:
            return
        symbols: list = json.loads(text[start:end])
        now_iso = datetime.now(timezone.utc).isoformat()
        for symbol in symbols:
            if isinstance(symbol, str) and symbol.strip():
                db.upsert_detected_symbol(guild_id, user_id, symbol.strip().lower(), now_iso)
    except Exception as e:
        print(f"Symbol detection error (non-fatal): {e}")


async def _try_auto_thread(
    interaction: discord.Interaction, guild_id: str, user_id: str
) -> None:
    """
    Maybe auto-trigger a vision thread. 8% chance. Silent failure.
    Notifies mod role members via DM if triggered.
    """
    try:
        if random.random() >= AUTO_THREAD_CHANCE:
            return

        motif = db.get_random_motif(guild_id)
        if not motif:
            return

        duration = random.randint(AUTO_THREAD_MIN_DURATION, AUTO_THREAD_MAX_DURATION)
        now_iso = datetime.now(timezone.utc).isoformat()
        db.create_thread(guild_id, user_id, motif, duration, False, now_iso)

        config = db.get_server_config(guild_id)
        if not config:
            return
        mod_role_id = str(config[1])
        guild = interaction.guild
        mod_role = guild.get_role(int(mod_role_id))
        if not mod_role:
            return

        msg = (
            f"**Auto-thread triggered** for **{interaction.user.display_name}** in {guild.name}.\n"
            f"Motif: *{motif}*\n"
            f"Duration: {duration} nights\n"
            f"*(Player has not been notified.)*"
        )
        for member in mod_role.members:
            try:
                await member.send(msg)
            except Exception:
                pass
    except Exception as e:
        print(f"Auto-thread trigger error (non-fatal): {e}")


# ── Lucid Vision helpers ──────────────────────────────────────────────────────

async def _call_lucid(
    accumulated: str, last_choice: str, is_final: bool, active_motif: str | None
) -> dict:
    """Call Claude for the next Lucid Vision fragment. Returns parsed JSON dict."""
    thread_note = ""
    if active_motif:
        thread_note = (
            f"\nIf it fits naturally, weave a very subtle reference "
            f"to this motif: {active_motif}"
        )

    if is_final:
        prompt = (
            "You are concluding an interactive Lucid Vision for a VTM V5 play-by-post game.\n\n"
            f"Vision so far:\n{accumulated}\n\n"
            f'The player chose: "{last_choice}"{thread_note}\n\n'
            "Write the final vision statement (2-3 sentences). "
            "Provide a sense of closure but remain ambiguous.\n\n"
            'Return ONLY valid JSON: {"fragment": "...", "choices": []}'
        )
    else:
        prompt = (
            "You are continuing an interactive Lucid Vision for a VTM V5 play-by-post game.\n\n"
            f"Vision so far:\n{accumulated}\n\n"
            f'The player chose: "{last_choice}"{thread_note}\n\n'
            "Continue the vision (2-3 sentences) then provide 2-3 short evocative choice labels "
            "(3-6 words each) for what the player does next.\n\n"
            'Return ONLY valid JSON: {"fragment": "...", "choices": ["...", "...", "..."]}'
        )

    response = await asyncio.to_thread(
        functools.partial(
            clients.client.messages.create,
            model=CLAUDE_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
    )
    text = response.content[0].text
    start, end = text.find("{"), text.rfind("}") + 1
    return json.loads(text[start:end])


# ── LucidVisionView ───────────────────────────────────────────────────────────

class LucidVisionView(discord.ui.View):
    """Interactive view for Lucid Vision branching choices."""

    def __init__(
        self,
        *,
        guild_id: str,
        user_id: str,
        accumulated: str,
        depth: int,
        max_depth: int,
        active_motif: str | None,
        now_iso: str,
    ) -> None:
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.user_id = user_id
        self.accumulated = accumulated
        self.depth = depth
        self.max_depth = max_depth
        self.active_motif = active_motif
        self.now_iso = now_iso

    def add_choice_button(self, label: str) -> None:
        btn = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary)

        async def callback(interaction: discord.Interaction, _btn: discord.ui.Button = btn) -> None:
            await self._on_choice(interaction, _btn.label)

        btn.callback = callback
        self.add_item(btn)

    async def _on_choice(self, interaction: discord.Interaction, choice: str) -> None:
        # Disable all buttons immediately to prevent double-clicks.
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        self.depth += 1
        is_final = self.depth >= self.max_depth

        try:
            data = await _call_lucid(self.accumulated, choice, is_final, self.active_motif)
        except Exception as e:
            print(f"Lucid Vision continuation error: {e}")
            await interaction.followup.send(
                "The vision fractures. The thread is lost.", ephemeral=True
            )
            return

        fragment = data.get("fragment", "")
        choices = data.get("choices", [])[:3]
        self.accumulated += f"\n\n*{fragment}*"

        embed = discord.Embed(description=self.accumulated, color=VISION_EMBED_COLOR)
        embed.set_footer(text="Lucid Vision")
        embed.set_author(name=interaction.user.display_name)

        if is_final or not choices:
            await interaction.edit_original_response(embed=embed, view=None)
            clean_text = self.accumulated.replace("*", "").strip()
            db.save_vision(self.guild_id, self.user_id, "Lucid Vision", clean_text, self.now_iso)
            asyncio.create_task(_run_symbol_detection(self.guild_id, self.user_id))
            asyncio.create_task(_try_auto_thread(interaction, self.guild_id, self.user_id))
        else:
            new_view = LucidVisionView(
                guild_id=self.guild_id,
                user_id=self.user_id,
                accumulated=self.accumulated,
                depth=self.depth,
                max_depth=self.max_depth,
                active_motif=self.active_motif,
                now_iso=self.now_iso,
            )
            for c in choices:
                new_view.add_choice_button(c)
            await interaction.edit_original_response(embed=embed, view=new_view)


# ── ConfirmOverwriteView ──────────────────────────────────────────────────────

class ConfirmOverwriteView(discord.ui.View):
    """Confirmation prompt for /assign_thread when a thread is already active."""

    def __init__(
        self,
        guild_id: str,
        user_id: str,
        motif: str,
        duration_nights: int,
        now_iso: str,
    ) -> None:
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id
        self.motif = motif
        self.duration_nights = duration_nights
        self.now_iso = now_iso

    @discord.ui.button(label="Confirm Overwrite", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        db.deactivate_thread(self.guild_id, self.user_id)
        db.create_thread(
            self.guild_id, self.user_id, self.motif, self.duration_nights, True, self.now_iso
        )
        self.stop()
        await interaction.response.edit_message(
            content=(
                f"Thread assigned.\n"
                f"Motif: *{self.motif}*\n"
                f"Duration: {self.duration_nights} nights."
            ),
            embed=None,
            view=None,
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.stop()
        await interaction.response.edit_message(
            content="Assignment cancelled. Existing thread is still active.",
            embed=None,
            view=None,
        )


# ── VisionHistoryView ─────────────────────────────────────────────────────────

class VisionHistoryView(discord.ui.View):
    """Paginated vision history for /my_visions and /vision_log."""

    PER_PAGE = 10

    def __init__(self, guild_id: str, user_id: str, title: str = "Vision History") -> None:
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.user_id = user_id
        self.title = title
        self.page = 0
        self._refresh_buttons()

    def _max_page(self) -> int:
        total = db.count_vision_history(self.guild_id, self.user_id)
        return max(0, (total - 1) // self.PER_PAGE) if total > 0 else 0

    def _refresh_buttons(self) -> None:
        self.prev_btn.disabled = self.page == 0
        self.next_btn.disabled = self.page >= self._max_page()

    def build_embed(self) -> discord.Embed:
        visions = db.get_vision_history_page(
            self.guild_id, self.user_id, self.page, self.PER_PAGE
        )
        embed = discord.Embed(title=self.title, color=VISION_EMBED_COLOR)
        if not visions:
            embed.description = "No visions recorded yet."
        else:
            lines = []
            for v in visions:
                ts = datetime.fromisoformat(v["timestamp"]).strftime("%b %d, %Y")
                tag = " *(ST)*" if v["is_st_triggered"] else ""
                preview = v["vision_text"][:140]
                if len(v["vision_text"]) > 140:
                    preview += "…"
                lines.append(f"**{v['vision_type']}**{tag} · {ts}\n*{preview}*")
            embed.description = "\n\n".join(lines)
        embed.set_footer(text=f"Page {self.page + 1} of {self._max_page() + 1}")
        return embed

    @discord.ui.button(label="← Previous", style=discord.ButtonStyle.secondary)
    async def prev_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page = max(0, self.page - 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next →", style=discord.ButtonStyle.secondary)
    async def next_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page = min(self._max_page(), self.page + 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


# ── JournalView ───────────────────────────────────────────────────────────────

class JournalView(discord.ui.View):
    """Two-tab journal for /my_journal: Visions tab + Symbols tab."""

    PER_PAGE = 8

    def __init__(self, guild_id: str, user_id: str) -> None:
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.user_id = user_id
        self.current_tab = "visions"
        self.visions_page = 0
        self._refresh_buttons()

    def _max_page(self) -> int:
        total = db.count_vision_history(self.guild_id, self.user_id)
        return max(0, (total - 1) // self.PER_PAGE) if total > 0 else 0

    def _refresh_buttons(self) -> None:
        self.visions_tab.style = (
            discord.ButtonStyle.primary
            if self.current_tab == "visions"
            else discord.ButtonStyle.secondary
        )
        self.symbols_tab.style = (
            discord.ButtonStyle.primary
            if self.current_tab == "symbols"
            else discord.ButtonStyle.secondary
        )
        on_visions = self.current_tab == "visions"
        self.prev_btn.disabled = not on_visions or self.visions_page == 0
        self.next_btn.disabled = not on_visions or self.visions_page >= self._max_page()

    def build_embed(self) -> discord.Embed:
        return self._visions_embed() if self.current_tab == "visions" else self._symbols_embed()

    def _visions_embed(self) -> discord.Embed:
        visions = db.get_vision_history_page(
            self.guild_id, self.user_id, self.visions_page, self.PER_PAGE
        )
        embed = discord.Embed(title="📖 Your Journal — Visions", color=VISION_EMBED_COLOR)
        if not visions:
            embed.description = "No visions recorded yet."
        else:
            lines = []
            for v in visions:
                ts = datetime.fromisoformat(v["timestamp"]).strftime("%b %d")
                tag = " *(ST)*" if v["is_st_triggered"] else ""
                preview = v["vision_text"][:120]
                if len(v["vision_text"]) > 120:
                    preview += "…"
                lines.append(f"**{v['vision_type']}**{tag} · {ts}\n*{preview}*")
            embed.description = "\n\n".join(lines)
        embed.set_footer(
            text=f"Page {self.visions_page + 1} of {self._max_page() + 1}"
        )
        return embed

    def _symbols_embed(self) -> discord.Embed:
        symbols = db.get_detected_symbols(self.guild_id, self.user_id)
        embed = discord.Embed(title="🔍 Your Journal — Recurring Symbols", color=VISION_EMBED_COLOR)
        if not symbols:
            embed.description = (
                "No recurring symbols detected yet.\n"
                "Keep seeking visions — patterns reveal themselves over time."
            )
        else:
            lines = []
            for s in symbols:
                first = datetime.fromisoformat(s["first_seen"]).strftime("%b %d")
                last = datetime.fromisoformat(s["last_seen"]).strftime("%b %d")
                lines.append(
                    f"**{s['symbol']}** (×{s['occurrence_count']})\n"
                    f"First seen: {first} · Last seen: {last}"
                )
            embed.description = "\n\n".join(lines)
        return embed

    @discord.ui.button(label="Visions", style=discord.ButtonStyle.primary, row=0)
    async def visions_tab(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.current_tab = "visions"
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Symbols", style=discord.ButtonStyle.secondary, row=0)
    async def symbols_tab(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.current_tab = "symbols"
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="← Prev", style=discord.ButtonStyle.secondary, row=1)
    async def prev_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.visions_page = max(0, self.visions_page - 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next →", style=discord.ButtonStyle.secondary, row=1)
    async def next_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.visions_page = min(self._max_page(), self.visions_page + 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
