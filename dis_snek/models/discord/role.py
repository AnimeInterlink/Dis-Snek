from functools import partial, total_ordering
from typing import Any, Dict, Optional, TYPE_CHECKING, Union

import attrs

from dis_snek.client.const import MISSING, Absent, T
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.client.utils.attr_converters import optional as optional_c
from dis_snek.client.utils.serializer import dict_filter_missing
from dis_snek.models.discord.asset import Asset
from dis_snek.models.discord.emoji import PartialEmoji
from dis_snek.models.discord.color import Color
from dis_snek.models.discord.enums import Permissions
from .base import DiscordObject

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord.guild import Guild
    from dis_snek.models.discord.user import Member
    from dis_snek.models.discord.snowflake import Snowflake_Type

__all__ = ("Role",)


def sentinel_converter(value: Optional[bool | T], sentinel: T = attrs.NOTHING) -> bool:
    if value is sentinel:
        return False
    elif value is None:
        return True
    return value


@define()
@total_ordering
class Role(DiscordObject):
    _sentinel = object()

    name: str = field(repr=True)
    color: "Color" = field(converter=Color)
    hoist: bool = field(default=False)
    position: int = field(repr=True)
    permissions: "Permissions" = field(converter=Permissions)
    managed: bool = field(default=False)
    mentionable: bool = field(default=True)
    premium_subscriber: bool = field(default=_sentinel, converter=partial(sentinel_converter, sentinel=_sentinel))
    _icon: Optional[Asset] = field(default=None)
    _unicode_emoji: Optional[PartialEmoji] = field(default=None, converter=optional_c(PartialEmoji.from_str))
    _guild_id: "Snowflake_Type" = field()
    _bot_id: Optional["Snowflake_Type"] = field(default=None)
    _integration_id: Optional["Snowflake_Type"] = field(default=None)  # todo integration object?

    def __lt__(self: "Role", other: "Role") -> bool:
        if not isinstance(self, Role) or not isinstance(other, Role):
            return NotImplemented

        if self._guild_id != other._guild_id:
            raise RuntimeError("Unable to compare Roles from different guilds.")

        if self.id == self._guild_id:  # everyone role
            # everyone role is on the bottom, so check if the other role is, well, not it
            # because then it must be higher than it
            return other.id != self.id

        if self.position < other.position:
            return True

        if self.position == other.position:
            # if two roles have the same position, which can happen thanks to discord, then
            # we can thankfully use their ids to determine which one is lower
            return self.id < other.id

        return False

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data.update(data.pop("tags", {}))

        if icon_hash := data.get("icon"):
            data["icon"] = Asset.from_path_hash(client, f"role-icons/{data['id']}/{{}}", icon_hash)

        return data

    async def fetch_bot(self) -> Optional["Member"]:
        """
        Fetch the bot associated with this role if any.

        Returns:
            Member object if any

        """
        if self._bot_id is None:
            return None
        return await self._client.cache.fetch_member(self._guild_id, self._bot_id)

    def get_bot(self) -> Optional["Member"]:
        """
        Get the bot associated with this role if any.

        Returns:
            Member object if any

        """
        if self._bot_id is None:
            return None
        return self._client.cache.get_member(self._guild_id, self._bot_id)

    @property
    def guild(self) -> "Guild":
        """The guild object this role is from."""
        return self._client.cache.get_guild(self._guild_id)

    @property
    def default(self) -> bool:
        """Is this the `@everyone` role."""
        return self.id == self._guild_id

    @property
    def bot_managed(self) -> bool:
        """Is this role owned/managed by a bot."""
        return self._bot_id is not None

    @property
    def mention(self) -> str:
        """Returns a string that would mention the role."""
        return f"<@&{self.id}>" if self.id != self._guild_id else "@everyone"

    @property
    def integration(self) -> bool:
        """Is this role owned/managed by an integration."""
        return self._integration_id is not None

    @property
    def members(self) -> list["Member"]:
        """List of members with this role"""
        return [member for member in self.guild.members if member.has_role(self)]

    @property
    def icon(self) -> Optional[Asset | PartialEmoji]:
        """
        The icon of this role

        Note:
            You have to use this method instead of the `_icon` attribute, because the first does account for unicode emojis
        """
        return self._icon or self._unicode_emoji

    @property
    def is_assignable(self) -> bool:
        """
        Can this role be assigned or removed by this bot?

        Note:
            This does not account for permissions, only the role hierarchy

        """
        return (self.default or self.guild.me.top_role > self) and not self.managed

    async def delete(self, reason: str = None) -> None:
        """
        Delete this role.

        Args:
            reason: An optional reason for this deletion

        """
        await self._client.http.delete_guild_role(self._guild_id, self.id, reason)

    async def edit(
        self,
        name: Absent[str] = MISSING,
        permissions: Absent[str] = MISSING,
        color: Absent[Union[int, Color]] = MISSING,
        hoist: Absent[bool] = MISSING,
        mentionable: Absent[bool] = MISSING,
    ) -> "Role":
        """
        Edit this role, all arguments are optional.

        Args:
            name: name of the role
            permissions: New permissions to use
            color: The color of the role
            hoist: whether the role should be displayed separately in the sidebar
            mentionable: whether the role should be mentionable

        Returns:
            Role with updated information

        """
        if isinstance(color, Color):
            color = color.value

        payload = dict_filter_missing(
            {"name": name, "permissions": permissions, "color": color, "hoist": hoist, "mentionable": mentionable}
        )

        r_data = await self._client.http.modify_guild_role(self._guild_id, self.id, payload)
        r_data["guild_id"] = self._guild_id
        return self.from_dict(r_data, self._client)
