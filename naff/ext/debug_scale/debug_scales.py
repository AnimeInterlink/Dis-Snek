from naff import Cog
from naff.client.errors import CogLoadException, CommandCheckFailure, ExtensionLoadException
from naff.models import (
    message_command,
    MessageContext,
    Context,
)

__all__ = ["DebugScales"]


class DebugScales(Cog):
    @message_command("debug_regrow")
    async def regrow(self, ctx: MessageContext, module: str) -> None:
        try:
            await self.shed_scale.callback(ctx, module)
        except (ExtensionLoadException, CogLoadException):
            pass
        await self.grow_scale.callback(ctx, module)

    @message_command("debug_grow")
    async def grow_scale(self, ctx: MessageContext, module: str) -> None:
        self.bot.load_cog(module)
        await ctx.message.add_reaction("🪴")

    @message_command("debug_shed")
    async def shed_scale(self, ctx: MessageContext, module: str) -> None:
        self.bot.drop_cog(module)
        await ctx.message.add_reaction("💥")

    @regrow.error
    @grow_scale.error
    @shed_scale.error
    async def regrow_error(self, error: Exception, ctx: Context, *args) -> None:
        if isinstance(error, CommandCheckFailure):
            return await ctx.send("You do not have permission to execute this command")
        elif isinstance(error, ExtensionLoadException):
            return await ctx.send(str(error))
        raise


def setup(bot) -> None:
    DebugScales(bot)
