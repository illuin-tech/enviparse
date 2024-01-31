import dataclasses
import os
from typing import Type, Optional, TypeVar, List, get_args, Union, get_origin, Callable, Tuple, Dict

try:
    import attr

    ATTR_AVAILABLE = True
except ImportError:
    ATTR_AVAILABLE = False

ClassType = TypeVar("ClassType")


# TODO move exception to error.py
class EnvifyError(Exception):
    pass


class UnexpectedTypeError(EnvifyError):
    def __init__(self, type: str, path: str):
        super().__init__(f'Unsupported type "{type}" for property at path "{path}"')


class UnknownTypeError(EnvifyError):
    def __init__(self, path: str):
        super().__init__(f'Unknown generic type for property at path "{path}"')


class MissingEnvironmentVariableError(EnvifyError):
    def __init__(self, env_var_name: str):
        super().__init__(f"Environment variable '{env_var_name}' is not set.")


class CastError(EnvifyError):
    def __init__(self, env_var_name: str, data_type: str):
        super().__init__(f"Failed to convert '{env_var_name}' to {data_type}.")


class Envify:
    def __init__(self,
                 concat_env_name_func: Optional[Callable[[str, str], str]] = None,
                 ):
        self._concat_env_name_func = (concat_env_name_func
                                      or (lambda prefix, suffix: f"{prefix.upper()}_{suffix.upper()}"))

    def envify(
            self,
            prefix: str,
            t_type: Type[ClassType],
            default_value: Optional[ClassType] = None
    ) -> ClassType:
        if t_type in (int, float, str):
            return self._get_primitive_type_from_env(
                prefix,
                t_type,
                default_value
            )
        if t_type == bool:
            return self._get_bool_type_from_env(prefix, default_value)
        if self._is_list_type(t_type):
            return self._get_list_type_from_env(prefix, t_type, default_value)
        if self._is_optional_type(t_type):
            return self._get_optional_type_from_env(prefix, t_type, default_value)
        if dataclasses.is_dataclass(t_type):
            return self._get_dataclass_from_env(prefix, t_type, default_value)
        if ATTR_AVAILABLE and hasattr(t_type, "__attrs_attrs__"):
            return self._get_attr_class_from_env(prefix, t_type, default_value)
        raise UnexpectedTypeError(t_type.__name__, prefix)

    @staticmethod
    def _is_list_type(t_class: Type[ClassType]) -> bool:
        return get_origin(t_class) == list

    @staticmethod
    def _is_optional_type(t_class: Type[ClassType]) -> bool:
        # Optional[T] is an alias for Union[T, None]
        type_args = get_args(t_class)
        return (
                get_origin(t_class) == Union
                and len(type_args) == 2
                and any(type_arg == type(None) for type_arg in type_args)
        )

    @staticmethod
    def _has_env_var_with_prefix(prefix: str) -> bool:
        return any(env_name for env_name in os.environ if env_name.startswith(prefix))

    @staticmethod
    def _get_primitive_type_from_env(
            prefix: str,
            data_type: Type[int | float | str],
            default_value: Optional[int | float | str]
    ) -> int | float | str:
        env_var_name = f"{prefix}"
        env_var_value = os.environ.get(env_var_name)

        if env_var_value is not None:
            try:
                return data_type(env_var_value)
            except ValueError as error:
                raise CastError(env_var_name, data_type.__name__) from error
        elif default_value is not None:
            return default_value
        raise MissingEnvironmentVariableError(env_var_name)

    @staticmethod
    def _get_bool_type_from_env(
            prefix: str,
            default_value: Optional[bool]
    ) -> bool:
        env_var_name = f"{prefix}"
        env_var_value = os.environ.get(env_var_name)

        if env_var_value is not None:
            if env_var_value.upper() == "FALSE":
                return False
            if env_var_value.upper() == "TRUE":
                return True
            raise CastError(env_var_name, bool.__name__)
        if default_value is not None:
            return default_value
        raise MissingEnvironmentVariableError(env_var_name)

    def _get_list_type_from_env(
            self,
            prefix: str,
            attr_class: Type[List[ClassType]],
            default_value: Optional[List[ClassType]]
    ) -> List[ClassType]:
        type_hints = get_args(attr_class)
        if len(type_hints) == 0:
            raise UnknownTypeError(prefix)
        list_item_type = type_hints[0]

        values = []
        index = 0
        while self._has_env_var_with_prefix(self._concat_env_name_func(prefix, str(index))):
            list_item_env_var_name_prefix = self._concat_env_name_func(prefix, str(index))
            item_env_var_value = self.envify(list_item_env_var_name_prefix, list_item_type)
            if item_env_var_value is not None:
                values.append(item_env_var_value)
                index += 1
            else:
                break
        if len(values) > 0:
            return values
        elif default_value is not None:
            return default_value
        else:
            return []

    def _get_optional_type_from_env(
            self,
            prefix: str,
            attr_class: Type[Optional[ClassType]],
            default_value: Optional[ClassType]
    ) -> Optional[ClassType]:
        type_hints = get_args(attr_class)
        if len(type_hints) == 0:
            raise UnknownTypeError(prefix)
        optional_type = type_hints[0]
        try:
            return self.envify(prefix, optional_type, default_value)
        except MissingEnvironmentVariableError:
            return default_value

    def _get_dataclass_from_env(
            self,
            prefix: str,
            attr_class: Type[ClassType],
            default_value: Optional[ClassType]
    ) -> ClassType:
        fields = dataclasses.fields(attr_class)
        # if there is environment variable with prefix,
        # we will try to create a dataclass instance from environment
        # variable or default
        if self._has_env_var_with_prefix(self._concat_env_name_func(prefix, "")):
            field_values = {}
            for field in fields:
                field_env_var_prefix = self._concat_env_name_func(prefix, field.name)
                if default_value is not None:
                    field_env_var_default_value = getattr(default_value, field.name)
                elif field.default is not None and field.default is not dataclasses.MISSING:
                    field_env_var_default_value = field.default
                else:
                    field_env_var_default_value = None

                if self._has_env_var_with_prefix(field_env_var_prefix) or self._is_optional_type(field.type):
                    field_values[field.name] = self.envify(
                        prefix=field_env_var_prefix, t_type=field.type, default_value=field_env_var_default_value
                    )
                elif field_env_var_default_value is not None:
                    field_values[field.name] = field_env_var_default_value
                else:
                    raise ValueError(f'No value for property "{field_env_var_prefix}"')
            return attr_class(**field_values)

        # otherwise if a default value has been given, fallback to defaut value
        if default_value is not None:
            return default_value

        # otherwise, let's check if the dataclass can be creating using default fields
        default_data_class_value = self._create_data_class_using_default(fields, attr_class)
        if default_data_class_value is not None:
            return default_data_class_value

        # otherwise, we cannot create it & raise an error
        raise MissingEnvironmentVariableError(prefix)

    def _create_data_class_using_default(
            self,
            fields: Tuple[dataclasses.Field],
            data_class: Type[ClassType]
    ) -> Optional[ClassType]:
        field_values = {}
        for field in fields:
            if field.default is not None and field.default is not dataclasses.MISSING:
                field_values[field.name] = field.default
            elif self._is_optional_type(field.type):
                field_values[field.name] = None
            else:
                return None
        return data_class(**field_values)

    def _get_attr_class_from_env(
            self,
            prefix: str,
            attr_class: Type[ClassType],
            default_value: Optional[ClassType]
    ) -> ClassType:
        field_dict = attr.fields_dict(attr_class)
        # if variable exist with prefix, let's try to create the attr class
        if self._has_env_var_with_prefix(self._concat_env_name_func(prefix, "")):
            field_values = {}
            for field_name, field in field_dict.items():
                field_env_var_prefix = self._concat_env_name_func(prefix, field_name)
                if default_value is not None:
                    field_env_var_default_value = getattr(default_value, field_name)
                elif field.default is not None and field.default is not attr.NOTHING:
                    field_env_var_default_value = field.default
                else:
                    field_env_var_default_value = None

                if self._has_env_var_with_prefix(field_env_var_prefix) or self._is_optional_type(field.type):
                    field_values[field_name] = self.envify(
                        prefix=field_env_var_prefix, t_type=field.type, default_value=field_env_var_default_value
                    )
                elif field_env_var_default_value is not None:
                    field_values[field_name] = field_env_var_default_value
                else:
                    raise ValueError(f'No value for property "{field_env_var_prefix}"')
            return attr_class(**field_values)

        # if a default value was given, use it
        if default_value is not None:
            return default_value

        # otherwise, try to create attr class using default fields
        default_data_class_value = self._create_attr_class_using_default(field_dict, attr_class)
        if default_data_class_value is not None:
            return default_data_class_value

        # otherwise, raise an error
        raise MissingEnvironmentVariableError(prefix)

    def _create_attr_class_using_default(
            self,
            field_dict: Dict[str, "attr.Attribute"],
            data_class: Type[ClassType]
    ) -> Optional[ClassType]:
        field_values = {}
        for field_name, field in field_dict.items():
            if field.default is not None and field.default is not attr.NOTHING:
                field_values[field_name] = field.default
            elif self._is_optional_type(field.type):
                field_values[field_name] = None
            else:
                return None
        return data_class(**field_values)
