from enum import IntEnum
from typing import Optional, TYPE_CHECKING, Union, Dict, Any, List
import re

from dis_snek.client.const import MISSING, Absent
from dis_snek.client.errors import ForeignWebhookException, EmptyMessageException
from dis_snek.client.mixins.send import SendMixin
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.client.utils.serializer import to_image_data
from dis_snek.models.discord.message import process_message_payload
from dis_snek.models.discord.snowflake import to_snowflake, to_optional_snowflake
from .base import DiscordObject

if TYPE_CHECKING:
    from dis_snek.models.discord.file import UPLOADABLE_TYPE
    from dis_snek.client import Snake
    from dis_snek.models.discord.enums import MessageFlags
    from dis_snek.models.discord.snowflake import Snowflake_Type
    from dis_snek.models.discord.channel import TYPE_MESSAGEABLE_CHANNEL
    from dis_snek.models.discord.components import BaseComponent
    from dis_snek.models.discord.embed import Embed

    from dis_snek.models.discord.message import (
        AllowedMentions,
        Message,
        MessageReference,
    )
    from dis_snek.models.discord.sticker import Sticker

__all__ = ("WebhookTypes", "Webhook")


class WebhookTypes(IntEnum):
    INCOMING = 1
    """Incoming Webhooks can post messages to channels with a generated token"""
    CHANNEL_FOLLOWER = 2
    """Channel Follower Webhooks are internal webhooks used with Channel Following to post new messages into channels"""
    APPLICATION = 3
    """Application webhooks are webhooks used with Interactions"""


@define()
class Webhook(DiscordObject, SendMixin):
    type: WebhookTypes = field()
    """The type of webhook"""

    application_id: Optional["Snowflake_Type"] = field(default=None)
    """the bot/OAuth2 application that created this webhook"""

    guild_id: Optional["Snowflake_Type"] = field(default=None)
    """the guild id this webhook is for, if any"""
    channel_id: Optional["Snowflake_Type"] = field(default=None)
    """the channel id this webhook is for, if any"""
    user_id: Optional["Snowflake_Type"] = field(default=None)
    """the user this webhook was created by"""

    name: Optional[str] = field(default=None)
    """the default name of the webhook"""
    avatar: Optional[str] = field(default=None)
    """the default user avatar hash of the webhook"""
    token: str = field(default=MISSING)
    """the secure token of the webhook (returned for Incoming Webhooks)"""
    url: Optional[str] = field(default=None)
    """the url used for executing the webhook (returned by the webhooks OAuth2 flow)"""

    source_guild_id: Optional["Snowflake_Type"] = field(default=None)
    """the guild of the channel that this webhook is following (returned for Channel Follower Webhooks)"""
    source_channel_id: Optional["Snowflake_Type"] = field(default=None)
    """the channel that this webhook is following (returned for Channel Follower Webhooks)"""

    @classmethod
    def from_url(cls, url: str, client: "Snake") -> "Webhook":
        """
        Webhook object from a URL.

        Args:
            client: The client to use to make the request.
            url: Webhook URL

        Returns:
            A Webhook object.

        """
        match = re.search(r"discord(?:app)?\.com/api/webhooks/(?P<id>[0-9]{17,})/(?P<token>[\w\-.]{60,68})", url)
        if match is None:
            raise ValueError("Invalid webhook URL given.")

        data: Dict[str, Any] = match.groupdict()
        data["type"] = WebhookTypes.INCOMING
        return cls.from_dict(data, client)

    @classmethod
    async def create(
        cls,
        client: "Snake",
        channel: Union["Snowflake_Type", "TYPE_MESSAGEABLE_CHANNEL"],
        name: str,
        avatar: Absent["UPLOADABLE_TYPE"] = MISSING,
    ) -> "Webhook":
        """
        Create a webhook.

        Args:
            client: The bot's client
            channel: The channel to create the webhook in
            name: The name of the webhook
            avatar: An optional default avatar to use

        Returns:
            New webhook object

        Raises:
            ValueError: If you try to name the webhook "Clyde"

        """
        if name.lower() == "clyde":
            raise ValueError('Webhook names cannot be "Clyde"')

        if not isinstance(channel, (str, int)):
            channel = to_snowflake(channel)

        if avatar:
            avatar = to_image_data(avatar)

        data = await client.http.create_webhook(channel, name, avatar)

        new_cls = cls.from_dict(data, client)

        return new_cls

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        if data.get("user"):
            user = client.cache.place_user_data(data.pop("user"))
            data["user_id"] = user.id
        return data

    async def edit(
        self,
        name: Absent[str] = MISSING,
        avatar: Absent["UPLOADABLE_TYPE"] = MISSING,
        channel_id: Absent["Snowflake_Type"] = MISSING,
    ) -> None:
        """
        Edit this webhook.

        Args:
            name: The default name of the webhook.
            avatar: The image for the default webhook avatar.
            channel_id: The new channel id this webhook should be moved to.

        Raises:
            ValueError: If you try to name the webhook "Clyde"

        """
        if name.lower() == "clyde":
            raise ValueError('Webhook names cannot be "Clyde"')

        data = await self._client.http.modify_webhook(
            self.id, name, to_image_data(avatar), to_optional_snowflake(channel_id), self.token
        )
        self.update_from_dict(data)

    async def delete(self) -> None:
        """Delete this webhook."""
        await self._client.http.delete_webhook(self.id, self.token)

    async def send(
        self,
        content: Optional[str] = None,
        embed: Optional[Union["Embed", dict]] = None,
        embeds: Optional[Union[List[Union["Embed", dict]], Union["Embed", dict]]] = None,
        components: Optional[
            Union[List[List[Union["BaseComponent", dict]]], List[Union["BaseComponent", dict]], "BaseComponent", dict]
        ] = None,
        stickers: Optional[Union[List[Union["Sticker", "Snowflake_Type"]], "Sticker", "Snowflake_Type"]] = None,
        allowed_mentions: Optional[Union["AllowedMentions", dict]] = None,
        reply_to: Optional[Union["MessageReference", "Message", dict, "Snowflake_Type"]] = None,
        files: Optional[Union["UPLOADABLE_TYPE", List["UPLOADABLE_TYPE"]]] = None,
        file: Optional["UPLOADABLE_TYPE"] = None,
        tts: bool = False,
        suppress_embeds: bool = False,
        flags: Optional[Union[int, "MessageFlags"]] = None,
        username: str = None,
        avatar_url: str = None,
        wait: bool = False,
        thread: "Snowflake_Type" = None,
        **kwargs,
    ) -> Optional["Message"]:
        """
        Send a message as this webhook.

        Args:
            content: Message text content.
            embeds: Embedded rich content (up to 6000 characters).
            embed: Embedded rich content (up to 6000 characters).
            components: The components to include with the message.
            stickers: IDs of up to 3 stickers in the server to send in the message.
            allowed_mentions: Allowed mentions for the message.
            reply_to: Message to reference, must be from the same channel.
            files: Files to send, the path, bytes or File() instance, defaults to None. You may have up to 10 files.
            file: Files to send, the path, bytes or File() instance, defaults to None. You may have up to 10 files.
            tts: Should this message use Text To Speech.
            suppress_embeds: Should embeds be suppressed on this send
            flags: Message flags to apply.
            username: The username to use
            avatar_url: The url of an image to use as the avatar
            wait: Waits for confirmation of delivery. Set this to True if you intend to edit the message
            thread: Send this webhook to a thread channel

        Returns:
            New message object that was sent if `wait` is set to True

        """
        if not self.token:
            raise ForeignWebhookException("You cannot send messages with a webhook without a token!")

        if not content and not (embeds or embed) and not (files or file) and not stickers:
            raise EmptyMessageException("You cannot send a message without any content, embeds, files, or stickers")

        if suppress_embeds:
            if isinstance(flags, int):
                flags = MessageFlags(flags)
            flags = flags | MessageFlags.SUPPRESS_EMBEDS

        message_payload = process_message_payload(
            content=content,
            embeds=embeds or embed,
            components=components,
            stickers=stickers,
            allowed_mentions=allowed_mentions,
            reply_to=reply_to,
            files=files or file,
            tts=tts,
            flags=flags,
            username=username,
            avatar_url=avatar_url,
            **kwargs,
        )

        message_data = await self._client.http.execute_webhook(
            self.id, self.token, message_payload, wait, to_optional_snowflake(thread)
        )
        if message_data:
            return self._client.cache.place_message_data(message_data)

    async def edit_message(
        self,
        message: Union["Message", "Snowflake_Type"],
        content: Optional[str] = None,
        embeds: Optional[Union[List[Union["Embed", dict]], Union["Embed", dict]]] = None,
        components: Optional[
            Union[List[List[Union["BaseComponent", dict]]], List[Union["BaseComponent", dict]], "BaseComponent", dict]
        ] = None,
        stickers: Optional[Union[List[Union["Sticker", "Snowflake_Type"]], "Sticker", "Snowflake_Type"]] = None,
        allowed_mentions: Optional[Union["AllowedMentions", dict]] = None,
        reply_to: Optional[Union["MessageReference", "Message", dict, "Snowflake_Type"]] = None,
        files: Optional[Union["UPLOADABLE_TYPE", List["UPLOADABLE_TYPE"]]] = None,
        file: Optional["UPLOADABLE_TYPE"] = None,
        tts: bool = False,
        flags: Optional[Union[int, "MessageFlags"]] = None,
    ) -> Optional["Message"]:
        """
        Edit a message as this webhook.

        Args:
            message: Message to edit
            content: Message text content.
            embeds: Embedded rich content (up to 6000 characters).
            components: The components to include with the message.
            stickers: IDs of up to 3 stickers in the server to send in the message.
            allowed_mentions: Allowed mentions for the message.
            reply_to: Message to reference, must be from the same channel.
            files: Files to send, the path, bytes or File() instance, defaults to None. You may have up to 10 files.
            file: Files to send, the path, bytes or File() instance, defaults to None. You may have up to 10 files.
            tts: Should this message use Text To Speech.
            flags: Message flags to apply.

        Returns:
            Updated message object that was sent if `wait` is set to True

        """
        message_payload = process_message_payload(
            content=content,
            embeds=embeds,
            components=components,
            stickers=stickers,
            allowed_mentions=allowed_mentions,
            reply_to=reply_to,
            files=files or file,
            tts=tts,
            flags=flags,
        )
        msg_data = await self._client.http.edit_webhook_message(
            self.id, self.token, to_snowflake(message), message_payload
        )
        if msg_data:
            return self._client.cache.place_message_data(msg_data)
