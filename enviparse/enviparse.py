import dataclasses
import enum
import os
from typing import Type, Optional, TypeVar, List, get_args, Union, get_origin, Callable

from .errors import (
    UnexpectedTypeError,
    CastError,
    MissingEnvironmentVariableError,
    UnknownTypeError,
    NestedMissingEnvironmentVariableError,
)

try:
    import attr

    ATTR_AVAILABLE = True
except ImportError:
    ATTR_AVAILABLE = False

ClassTypeT = TypeVar("ClassTypeT")


class Enviparse:
    def __init__(
        self,
        concat_env_name_func: Optional[Callable[[str, str], str]] = None,
    ):
        self._concat_env_name_func = concat_env_name_func or (
            lambda prefix, suffix: f"{prefix.upper()}_{suffix.upper()}"
        )

    def parse(  # pylint: disable=too-many-return-statements
        self,
        prefix: str,
        t_type: Type[ClassTypeT],
    ) -> ClassTypeT:
        if t_type in (int, float, str):
            return self._get_primitive_type_from_env(
                prefix,
                t_type,
            )
        if t_type == bool:
            return self._get_bool_type_from_env(prefix)
        if self._is_list_type(t_type):
            return self._get_list_type_from_env(prefix, t_type)
        if self._is_optional_type(t_type):
            return self._get_optional_type_from_env(prefix, t_type)
        if dataclasses.is_dataclass(t_type):
            return self._get_dataclass_from_env(prefix, t_type)
        if ATTR_AVAILABLE and hasattr(t_type, "__attrs_attrs__"):
            return self._get_attr_class_from_env(prefix, t_type)
        if self._is_enum_type(t_type):
            return self._get_enum_from_env(prefix, t_type)
        raise UnexpectedTypeError(t_type.__name__, prefix)

    @staticmethod
    def _is_list_type(t_class: Type[ClassTypeT]) -> bool:
        return get_origin(t_class) == list

    @staticmethod
    def _is_optional_type(t_class: Type[ClassTypeT]) -> bool:
        # Optional[T] is an alias for Union[T, None]
        type_args = get_args(t_class)
        return (
            get_origin(t_class) == Union
            and len(type_args) == 2
            and any(type_arg == type(None) for type_arg in type_args)
        )

    @staticmethod
    def _is_enum_type(t_class: Type[ClassTypeT]) -> bool:
        if not issubclass(t_class, enum.Enum):
            return False

        # for now only int or string enum are supported
        for enum_value in t_class:
            if not isinstance(enum_value.value, int) and not isinstance(enum_value.value, str):
                return False
        return True

    @staticmethod
    def _has_env_var_with_prefix(prefix: str) -> bool:
        return any(env_name for env_name in os.environ if env_name.startswith(prefix))

    @staticmethod
    def _get_primitive_type_from_env(
        prefix: str,
        data_type: Type[Union[int, float, str]],
    ) -> Union[int, float, str]:
        env_var_name = f"{prefix}"
        env_var_value = os.environ.get(env_var_name)

        if env_var_value is not None:
            try:
                return data_type(env_var_value)
            except ValueError as error:
                raise CastError(env_var_name, data_type.__name__) from error
        raise MissingEnvironmentVariableError(env_var_name)

    @staticmethod
    def _get_bool_type_from_env(
        prefix: str,
    ) -> bool:
        env_var_name = f"{prefix}"
        env_var_value = os.environ.get(env_var_name)

        if env_var_value is not None:
            if env_var_value.upper() == "FALSE":
                return False
            if env_var_value.upper() == "TRUE":
                return True
            raise CastError(env_var_name, bool.__name__)
        raise MissingEnvironmentVariableError(env_var_name)

    def _get_list_type_from_env(
        self,
        prefix: str,
        attr_class: Type[List[ClassTypeT]],
    ) -> List[ClassTypeT]:
        type_hints = get_args(attr_class)
        if len(type_hints) == 0:
            raise UnknownTypeError(prefix)
        list_item_type = type_hints[0]

        values = []
        index = 0
        while self._has_env_var_with_prefix(self._concat_env_name_func(prefix, str(index))):
            list_item_env_var_name_prefix = self._concat_env_name_func(prefix, str(index))
            item_env_var_value = self.parse(list_item_env_var_name_prefix, list_item_type)
            values.append(item_env_var_value)
            index += 1
        return values

    def _get_optional_type_from_env(
        self,
        prefix: str,
        attr_class: Type[Optional[ClassTypeT]],
    ) -> Optional[ClassTypeT]:
        type_hints = get_args(attr_class)
        optional_type = type_hints[0]
        if self._has_env_var_with_prefix(prefix):
            return self.parse(prefix, optional_type)
        return None

    def _get_dataclass_from_env(
        self,
        prefix: str,
        attr_class: Type[ClassTypeT],
    ) -> ClassTypeT:
        fields = dataclasses.fields(attr_class)
        field_values = {}
        for field in fields:
            field_env_var_prefix = self._concat_env_name_func(prefix, field.name)

            try:
                field_values[field.name] = self.parse(prefix=field_env_var_prefix, t_type=field.type)
            except MissingEnvironmentVariableError as error:
                if field.default is not None and field.default is not dataclasses.MISSING:
                    field_values[field.name] = field.default
                else:
                    raise NestedMissingEnvironmentVariableError(field_env_var_prefix) from error
        return attr_class(**field_values)

    def _get_attr_class_from_env(
        self,
        prefix: str,
        attr_class: Type[ClassTypeT],
    ) -> ClassTypeT:
        field_dict = attr.fields_dict(attr_class)
        # if variable exist with prefix, let's try to create the attr class
        field_values = {}
        for field_name, field in field_dict.items():
            field_env_var_prefix = self._concat_env_name_func(prefix, field_name)

            try:
                field_values[field_name] = self.parse(prefix=field_env_var_prefix, t_type=field.type)
            except MissingEnvironmentVariableError as error:
                if field.default is not None and field.default is not attr.NOTHING:
                    field_values[field_name] = field.default
                else:
                    raise NestedMissingEnvironmentVariableError(field_env_var_prefix) from error
        return attr_class(**field_values)

    @staticmethod
    def _get_enum_from_env(prefix: str, enum_class: Type[enum.Enum]) -> enum.Enum:
        env_var_value = os.environ.get(prefix)
        if env_var_value is None:
            raise MissingEnvironmentVariableError(prefix)

        for enum_value in enum_class:
            if str(enum_value.value) == env_var_value:
                return enum_value
        raise CastError(prefix, enum_class.__name__)
