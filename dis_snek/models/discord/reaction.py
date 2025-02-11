from asyncio import QueueEmpty
from collections import namedtuple
from typing import TYPE_CHECKING, List, Optional

from dis_snek.client.const import MISSING
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.models.discord.emoji import PartialEmoji
from dis_snek.models.discord.snowflake import to_snowflake
from dis_snek.models.misc.iterator import AsyncIterator
from .base import ClientObject

if TYPE_CHECKING:
    from dis_snek.models.discord.snowflake import Snowflake_Type
    from dis_snek.models import Message, TYPE_ALL_CHANNEL
    from dis_snek.models.discord.user import User

__all__ = ("ReactionUsers", "Reaction")


class ReactionUsers(AsyncIterator):
    """
    An async iterator for searching through a channel's history.

    Attributes:
        reaction: The reaction to search through
        limit: The maximum number of users to return (set to 0 for no limit)
        after: get users after this message ID

    """

    def __init__(self, reaction: "Reaction", limit: int = 50, after: Optional["Snowflake_Type"] = None) -> None:
        self.reaction: "Reaction" = reaction
        self.after: "Snowflake_Type" = after
        self._more = True
        super().__init__(limit)

    async def fetch(self) -> List["User"]:
        """
        Gets all the users who reacted to the message. Requests user data from discord API if not cached.

        Returns:
            A list of users who reacted to the message.

        """
        if self._more:
            expected = self.get_limit

            if self.after and not self.last:
                self.last = namedtuple("temp", "id")
                self.last.id = self.after

            users = await self.reaction._client.http.get_reactions(
                self.reaction._channel_id,
                self.reaction._message_id,
                self.reaction.emoji.req_format,
                limit=expected,
                after=self.last.id or MISSING,
            )
            if not users:
                raise QueueEmpty
            self._more = len(users) == expected
            return [self.reaction._client.cache.place_user_data(u) for u in users]
        else:
            raise QueueEmpty


@define()
class Reaction(ClientObject):
    count: int = field()
    """times this emoji has been used to react"""
    me: bool = field(default=False)
    """whether the current user reacted using this emoji"""
    emoji: "PartialEmoji" = field(converter=PartialEmoji.from_dict)
    """emoji information"""

    _channel_id: "Snowflake_Type" = field(converter=to_snowflake)
    _message_id: "Snowflake_Type" = field(converter=to_snowflake)

    def users(self, limit: int = 0, after: "Snowflake_Type" = None) -> ReactionUsers:
        """Users who reacted using this emoji."""
        return ReactionUsers(self, limit, after)

    @property
    def message(self) -> "Message":
        """The message this reaction is on."""
        return self._client.cache.get_message((self._channel_id, self._message_id))

    @property
    def channel(self) -> "TYPE_ALL_CHANNEL":
        """The channel this reaction is on."""
        return self._client.cache.get_channel(self._channel_id)

    async def remove(self) -> None:
        """Remove all this emoji's reactions from the message."""
        await self._client.http.clear_reaction(self._channel_id, self._message_id, self.emoji.req_format)
