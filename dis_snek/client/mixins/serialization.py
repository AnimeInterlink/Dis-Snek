import logging
from typing import Any, Dict, List, Type

import attrs

import dis_snek.client.const as const
from dis_snek.client.utils.attr_utils import define
import dis_snek.client.utils.serializer as serializer

__all__ = ("DictSerializationMixin",)

log = logging.getLogger(const.logger_name)


@define(slots=False)
class DictSerializationMixin:
    @classmethod
    def _get_keys(cls) -> frozenset:
        if (keys := getattr(cls, "_keys", None)) is None:
            keys = frozenset(field.name for field in attrs.fields(cls))
            setattr(cls, "_keys", keys)
        return keys

    @classmethod
    def _get_init_keys(cls) -> frozenset:
        if (init_keys := getattr(cls, "_init_keys", None)) is None:
            init_keys = frozenset(field.name.removeprefix("_") for field in attrs.fields(cls) if field.init)
            setattr(cls, "_init_keys", init_keys)
        return init_keys

    @classmethod
    def _filter_kwargs(cls, kwargs_dict: dict, keys: frozenset) -> dict:
        if const.kwarg_spam:
            unused = {k: v for k, v in kwargs_dict.items() if k not in keys}
            log.debug(f"Unused kwargs: {cls.__name__}: {unused}")  # for debug
        return {k: v for k, v in kwargs_dict.items() if k in keys}

    @classmethod
    def _process_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process dictionary data received from discord api. Does cleanup and other checks to data.

        Args:
            data: The dictionary data received from discord api.

        Returns:
            The processed dictionary. Ready to be converted into object class.

        """
        return data

    @classmethod
    def from_dict(cls: Type[const.T], data: Dict[str, Any]) -> const.T:
        """
        Process and converts dictionary data received from discord api to object class instance.

        Args:
            data: The json data received from discord api.

        Returns:
            The object class instance.

        """
        if isinstance(data, cls):
            return data
        data = cls._process_dict(data)
        return cls(**cls._filter_kwargs(data, cls._get_init_keys()))

    @classmethod
    def from_list(cls: Type[const.T], datas: List[Dict[str, Any]]) -> List[const.T]:
        """
        Process and converts list data received from discord api to object class instances.

        Args:
            data: The json data received from discord api.

        Returns:
            List of object class instances.

        """
        return [cls.from_dict(data) for data in datas]

    def update_from_dict(self: Type[const.T], data: Dict[str, Any]) -> const.T:
        """
        Updates object attribute(s) with new json data received from discord api.

        Args:
            data: The json data received from discord api.

        Returns:
            The updated object class instance.

        """
        data = self._process_dict(data)
        for key, value in self._filter_kwargs(data, self._get_keys()).items():
            # todo improve
            setattr(self, key, value)

        return self

    def _check_object(self) -> None:
        """Logic to check object properties just before export to json data for sending to discord api."""

    def to_dict(self) -> Dict[str, Any]:
        """
        Exports object into dictionary representation, ready to be sent to discord api.

        Returns:
            The exported dictionary.

        """
        self._check_object()
        return serializer.to_dict(self)
