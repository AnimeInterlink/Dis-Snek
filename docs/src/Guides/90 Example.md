# Examples

## `main.py`

```python

import logging

import dis_snek.const
from dis_snek.client import Snake
from dis_snek.models.context import ComponentContext
from dis_snek.models.enums import Intents
from dis_snek.models.events import Component
from dis_snek.models.listener import listen


logging.basicConfig()
cls_log = logging.getLogger(dis_snek.const.logger_name)
cls_log.setLevel(logging.DEBUG)

bot = Snake(intents=Intents.DEFAULT, sync_interactions=True, asyncio_debug=True)


@listen()
async def on_ready():
    print("Ready")
    print(f"This bot is owned by {bot.owner}")


@listen()
async def on_guild_create(event):
    print(f"guild created : {event.guild.name}")


@listen()
async def on_message_create(event):
    print(f"message received: {event.message.content}")


@listen()
async def on_component(event: Component):
    ctx = event.context
    await ctx.edit_origin("test")


bot.load_extension("test_components")
bot.load_extension("test_application_commands")
bot.start("Token")
```

## `test_components.py`

```python

from dis_snek import prefixed_command, Button, ActionRow, ButtonStyles, Scale


class ButtonExampleSkin(Scale):
    @prefixed_command()
    async def blurple_button(self, ctx):
        await ctx.send("hello there", components=Button(ButtonStyles.BLURPLE, "A blurple button"))

    @prefixed_command()
    async def multiple_buttons(self, ctx):
        await ctx.send(
            "2 buttons in a row",
            components=[Button(ButtonStyles.BLURPLE, "A blurple button"), Button(ButtonStyles.RED, "A red button")],
        )

    @prefixed_command()
    async def action_rows(self, ctx):
        await ctx.send(
            "2 buttons in 2 rows, using nested lists",
            components=[[Button(ButtonStyles.BLURPLE, "A blurple button")], [Button(ButtonStyles.RED, "A red button")]],
        )

    @prefixed_command()
    async def action_rows_more(self, ctx):
        await ctx.send(
            "2 buttons in 2 rows, using explicit action_rows lists",
            components=[
                ActionRow(Button(ButtonStyles.BLURPLE, "A blurple button")),
                ActionRow(Button(ButtonStyles.RED, "A red button")),
            ],
        )


def setup(bot):
    ButtonExampleSkin(bot)
```

## `test_application_commands.py`

```python

from dis_snek import slash_command, slash_option, InteractionContext, context_menu, CommandTypes, Button, ActionRow, ButtonStyles, Scale


class CommandsExampleSkin(Scale):
    @slash_command("command", description="This is a test", scopes=701347683591389185)
    @slash_option("another", "str option", 3, required=True)
    @slash_option("option", "int option", 4, required=True)
    async def command(self, ctx: InteractionContext, **kwargs):
        await ctx.send(str(ctx.resolved))
        await ctx.send(f"Test: {kwargs}", components=[ActionRow(Button(1, "Test"))])
        print(ctx.resolved)

    @command.error
    async def command_error(self, e, *args, **kwargs):
        print(f"Command hit error with {args=}, {kwargs=}")

    @command.pre_run
    async def command_pre_run(self, context, *args, **kwargs):
        print("I ran before the command did!")

    @context_menu(name="user menu", context_type=CommandTypes.USER, scopes=701347683591389185)
    async def user_context(self, ctx):
        await ctx.send("Context menu:: user")


def setup(bot):
    CommandsExampleSkin(bot)
```
