import asyncio
import inspect
import logging
from typing import Awaitable, List, TYPE_CHECKING, Callable, Coroutine, Optional

import dis_snek.models.snek as snek
from dis_snek.client.const import logger_name, MISSING
from dis_snek.client.utils.misc_utils import wrap_partial
from dis_snek.models.snek.tasks import Task

if TYPE_CHECKING:
    from dis_snek.client import Client
    from dis_snek.models.snek import AutoDefer, BaseCommand, Listener
    from dis_snek.models.snek import Context

log = logging.getLogger(logger_name)

__all__ = ["Cog"]


class Cog:
    """
    A class that allows you to separate your commands and listeners into separate files. Skins require an entrypoint in the same file called `setup`, this function allows client to load the Cog.

    ??? Hint "Example Usage:"
        ```python
        class ExampleCog(Cog):
            def __init__(self, bot):
                print("Cog Created")

            @message_command
            async def some_command(self, context):
                await ctx.send(f"I was sent from a cog called {self.name}")
        ```

    Attributes:
        bot Client: A reference to the client
        name str: The name of this Cog (`read-only`)
        description str: A description of this Cog
        cog_checks str: A list of checks to be ran on any command in this cog
        cog_prerun List: A list of coroutines to be run before any command in this cog
        cog_postrun List: A list of coroutines to be run after any command in this cog

    """

    bot: "Client"
    __name: str
    extension_name: str
    description: str
    cog_checks: List
    cog_prerun: List
    cog_postrun: List
    cog_error: Optional[Callable[..., Coroutine]]
    _commands: List
    _listeners: List
    auto_defer: "AutoDefer"

    def __new__(cls, bot: "Client", *args, **kwargs) -> "Cog":
        new_cls = super().__new__(cls)
        new_cls.bot = bot
        new_cls.__name = cls.__name__
        new_cls.cog_checks = []
        new_cls.cog_prerun = []
        new_cls.cog_postrun = []
        new_cls.cog_error = None
        new_cls.auto_defer = MISSING

        new_cls.description = kwargs.get("Description", None)
        if not new_cls.description:
            new_cls.description = inspect.cleandoc(cls.__doc__) if cls.__doc__ else None

        # load commands from class
        new_cls._commands = []
        new_cls._listeners = []

        for _name, val in inspect.getmembers(
            new_cls, predicate=lambda x: isinstance(x, (snek.BaseCommand, snek.Listener, Task))
        ):
            if isinstance(val, snek.BaseCommand):
                val.cog = new_cls
                val = wrap_partial(val, new_cls)

                new_cls._commands.append(val)

                if isinstance(val, snek.ModalCommand):
                    bot.add_modal_callback(val)
                elif isinstance(val, snek.ComponentCommand):
                    bot.add_component_callback(val)
                elif isinstance(val, snek.InteractionCommand):
                    bot.add_interaction(val)
                else:
                    bot.add_message_command(val)
            elif isinstance(val, snek.Listener):
                val = wrap_partial(val, new_cls)
                bot.add_listener(val)
                new_cls.listeners.append(val)
            elif isinstance(val, Task):
                wrap_partial(val, new_cls)

        log.debug(
            f"{len(new_cls._commands)} commands and {len(new_cls.listeners)} listeners"
            f" have been loaded from `{new_cls.name}`"
        )

        new_cls.extension_name = inspect.getmodule(new_cls).__name__
        new_cls.bot.cogs[new_cls.name] = new_cls
        return new_cls

    @property
    def __name__(self) -> str:
        return self.name

    @property
    def commands(self) -> List["BaseCommand"]:
        """Get the commands from this Cog."""
        return self._commands

    @property
    def listeners(self) -> List["Listener"]:
        """Get the listeners from this Cog."""
        return self._listeners

    @property
    def name(self) -> str:
        """Get the name of this Cog."""
        return self.__name

    def shed(self) -> None:
        """Called when this Cog is being removed."""
        for func in self._commands:
            if isinstance(func, snek.ModalCommand):
                for listener in func.listeners:
                    # noinspection PyProtectedMember
                    self.bot._modal_callbacks.pop(listener)
            elif isinstance(func, snek.ComponentCommand):
                for listener in func.listeners:
                    # noinspection PyProtectedMember
                    self.bot._component_callbacks.pop(listener)
            elif isinstance(func, snek.InteractionCommand):
                for scope in func.scopes:
                    if self.bot.interactions.get(scope):
                        self.bot.interactions[scope].pop(func.resolved_name, [])
            elif isinstance(func, snek.MessageCommand):
                if self.bot.commands[func.name]:
                    self.bot.commands.pop(func.name)
        for func in self.listeners:
            self.bot.listeners[func.event].remove(func)

        self.bot.cogs.pop(self.name, None)
        log.debug(f"{self.name} has been shed")

    def add_cog_auto_defer(self, ephemeral: bool = False, time_until_defer: float = 0.0) -> None:
        """
        Add a auto defer for all commands in this cog.

        Args:
            ephemeral: Should the command be deferred as ephemeral
            time_until_defer: How long to wait before deferring automatically

        """
        self.auto_defer = snek.AutoDefer(enabled=True, ephemeral=ephemeral, time_until_defer=time_until_defer)

    def add_cog_check(self, coroutine: Callable[["Context"], Awaitable[bool]]) -> None:
        """
        Add a coroutine as a check for all commands in this cog to run. This coroutine must take **only** the parameter `context`.

        ??? Hint "Example Usage:"
            ```python
            def __init__(self, bot):
                self.add_cog_check(self.example)

            @staticmethod
            async def example(context: Context):
                if context.author.id == 123456789:
                    return True
                return False
            ```
        Args:
            coroutine: The coroutine to use as a check

        """
        if not asyncio.iscoroutinefunction(coroutine):
            raise TypeError("Check must be a coroutine")

        if not self.cog_checks:
            self.cog_checks = []

        self.cog_checks.append(coroutine)

    def add_cog_prerun(self, coroutine: Callable[..., Coroutine]) -> None:
        """
        Add a coroutine to be run **before** all commands in this Cog.

        Note:
            Pre-runs will **only** be run if the commands checks pass

        ??? Hint "Example Usage:"
            ```python
            def __init__(self, bot):
                self.add_cog_prerun(self.example)

            async def example(self, context: Context):
                await ctx.send("I ran first")
            ```

        Args:
            coroutine: The coroutine to run

        """
        if not asyncio.iscoroutinefunction(coroutine):
            raise TypeError("Callback must be a coroutine")

        if not self.cog_prerun:
            self.cog_prerun = []
        self.cog_prerun.append(coroutine)

    def add_cog_postrun(self, coroutine: Callable[..., Coroutine]) -> None:
        """
        Add a coroutine to be run **after** all commands in this Cog.

        ??? Hint "Example Usage:"
            ```python
            def __init__(self, bot):
                self.add_cog_postrun(self.example)

            async def example(self, context: Context):
                await ctx.send("I ran first")
            ```

        Args:
            coroutine: The coroutine to run

        """
        if not asyncio.iscoroutinefunction(coroutine):
            raise TypeError("Callback must be a coroutine")

        if not self.cog_postrun:
            self.cog_postrun = []
        self.cog_postrun.append(coroutine)

    def add_cog_error(self, coroutine: Callable[..., Coroutine]) -> None:
        """
        Add a coroutine to handle any exceptions raised in this cog.

        ??? Hint "Example Usage:"
            ```python
            def __init__(self, bot):
                self.set_cog_error(self.example)

        Args:
            coroutine: The coroutine to run

        """
        if not asyncio.iscoroutinefunction(coroutine):
            raise TypeError("Callback must be a coroutine")

        if self.cog_error:
            log.warning("Cog error callback has been overridden!")
        self.cog_error = coroutine
