import io
import textwrap
import traceback
from contextlib import redirect_stdout
from typing import Any, Optional

from dis_snek import (
    Scale,
    slash_command,
    InteractionContext,
    Modal,
    ParagraphText,
    MISSING,
    ModalContext,
)
from dis_snek.ext.debug_scale.utils import debug_embed
from dis_snek.ext.paginators import Paginator
from dis_snek.models import (
    Embed,
    Message,
    File,
)

__all__ = ("DebugExec",)


class DebugExec(Scale):
    def __init__(self, bot) -> None:
        self.cache: dict[int, str] = {}

    @slash_command("debug", sub_cmd_name="exec", sub_cmd_description="Run arbitrary code")
    async def debug_exec(self, ctx: InteractionContext) -> Optional[Message]:
        last_code = self.cache.get(ctx.author.id, MISSING)

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "server": ctx.guild,
            "guild": ctx.guild,
            "message": ctx.message,
        } | globals()

        modal = Modal(
            title="Debug-Exec",
            components=[
                ParagraphText(
                    label="Code to run", value=last_code, custom_id="body", placeholder="Write your code here!"
                )
            ],
        )
        await ctx.send_modal(modal)

        m_ctx = await self.bot.wait_for_modal(modal, ctx.author)
        await m_ctx.defer()

        body = m_ctx.kwargs["body"]
        self.cache[ctx.author.id] = body

        if body.startswith("```") and body.endswith("```"):
            body = "\n".join(body.split("\n")[1:-1])
        else:
            body = body.strip("` \n")

        stdout = io.StringIO()

        to_compile = "async def func():\n%s" % textwrap.indent(body, "  ")
        try:
            exec(to_compile, env)  # noqa: S102
        except SyntaxError:
            return await ctx.send(f"```py\n{traceback.format_exc()}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()  # noqa
        except Exception:
            return await m_ctx.send(f"```py\n{stdout.getvalue()}{traceback.format_exc()}\n```")
        else:
            return await self.handle_exec_result(m_ctx, ret, stdout.getvalue(), body)

    async def handle_exec_result(self, ctx: ModalContext, result: Any, value: Any, body: str) -> Optional[Message]:
        if len(body) <= 2000:
            await ctx.send(f"```py\n{body}```")

        else:
            paginator = Paginator.create_from_string(self.bot, body, prefix="```py", suffix="```", page_size=4000)
            await paginator.send(ctx)

        if result is None:
            result = value or "No Output!"

        if isinstance(result, Message):
            try:
                e = debug_embed("Exec", timestamp=result.created_at, url=result.jump_url)
                e.description = result.content
                e.set_author(result.author.tag, icon_url=(result.author.guild_avatar or result.author.avatar).url)
                e.add_field("\u200b", f"[Jump To]({result.jump_url})\n{result.channel.mention}")

                return await ctx.send(embeds=e)
            except Exception:
                return await ctx.send(result.jump_url)

        if isinstance(result, Embed):
            return await ctx.send(embeds=[result])

        if isinstance(result, File):
            return await ctx.send(file=result)

        if isinstance(result, Paginator):
            return await result.send(ctx)

        if hasattr(result, "__iter__"):
            l_result = list(result)
            if all([isinstance(r, Embed) for r in result]):
                paginator = Paginator.create_from_embeds(self.bot, *l_result)
                return await paginator.send(ctx)

        if not isinstance(result, str):
            result = repr(result)

        # prevent token leak
        result = result.replace(self.bot.http.token, "[REDACTED TOKEN]")

        if len(result) <= 2000:
            return await ctx.send(f"```py\n{result}```")

        else:
            paginator = Paginator.create_from_string(self.bot, result, prefix="```py", suffix="```", page_size=4000)
            return await paginator.send(ctx)


def setup(bot) -> None:
    DebugExec(bot)
