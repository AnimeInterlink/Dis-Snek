from typing import TYPE_CHECKING, Any, List, Optional

import discord_typings

from dis_snek.client.const import MISSING
from ..route import Route

__all__ = ("StickerRequests",)


if TYPE_CHECKING:
    from aiohttp import FormData
    from dis_snek.models.discord.snowflake import Snowflake_Type


class StickerRequests:
    request: Any

    async def get_sticker(self, sticker_id: "Snowflake_Type") -> discord_typings.StickerData:
        """
        Get a specific sticker.

        Args:
            sticker_id: The id of the sticker

        Returns:
            Sticker or None

        """
        return await self.request(Route("GET", f"/stickers/{sticker_id}"))

    async def list_nitro_sticker_packs(self) -> List[discord_typings.StickerPackData]:
        """
        Gets the list of sticker packs available to Nitro subscribers.

        Returns:
            List of sticker packs

        """
        return await self.request(Route("GET", "/sticker-packs"))

    async def list_guild_stickers(self, guild_id: "Snowflake_Type") -> List[discord_typings.StickerData]:
        """
        Get the stickers for a guild.

        Args:
            guild_id: The guild to get stickers from

        Returns:
            List of Stickers or None

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/stickers"))

    async def get_guild_sticker(
        self, guild_id: "Snowflake_Type", sticker_id: "Snowflake_Type"
    ) -> discord_typings.StickerData:
        """
        Get a sticker from a guild.

        Args:
            guild_id: The guild to get stickers from
            sticker_id: The sticker to get from the guild

        Returns:
            Sticker or None

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/stickers/{sticker_id}"))

    async def create_guild_sticker(
        self, payload: "FormData", guild_id: "Snowflake_Type", reason: Optional[str] = MISSING
    ) -> discord_typings.StickerData:
        """
        Create a new sticker for the guild. Requires the MANAGE_EMOJIS_AND_STICKERS permission.

        Args:
            payload: the payload to send.
            guild_id: The guild to create sticker at.
            reason: The reason for this action.

        Returns:
            The new sticker data on success.

        """
        return await self.request(Route("POST", f"/guild/{guild_id}/stickers"), data=payload, reason=reason)

    async def modify_guild_sticker(
        self, payload: dict, guild_id: "Snowflake_Type", sticker_id: "Snowflake_Type", reason: Optional[str] = MISSING
    ) -> discord_typings.StickerData:
        """
        Modify the given sticker. Requires the MANAGE_EMOJIS_AND_STICKERS permission.

        Args:
            payload: the payload to send.
            guild_id: The guild of the target sticker.
            sticker_id:  The sticker to modify.
            reason: The reason for this action.

        Returns:
            The updated sticker data on success.

        """
        return await self.request(
            Route("PATCH", f"/guild/{guild_id}/stickers/{sticker_id}"), data=payload, reason=reason
        )

    async def delete_guild_sticker(
        self, guild_id: "Snowflake_Type", sticker_id: "Snowflake_Type", reason: Optional[str] = MISSING
    ) -> None:
        """
        Delete the given sticker. Requires the MANAGE_EMOJIS_AND_STICKERS permission.

        Args:
            guild_id: The guild of the target sticker.
            sticker_id:  The sticker to delete.
            reason: The reason for this action.

        Returns:
            Returns 204 No Content on success.

        """
        return await self.request(Route("DELETE", f"/guild/{guild_id}/stickers/{sticker_id}"), reason=reason)
