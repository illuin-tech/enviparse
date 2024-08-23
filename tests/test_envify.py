import dataclasses
import enum
import os
import unittest
from typing import Optional, List

import attr

from envify import Envify
from envify.errors import (
    CastError,
    MissingEnvironmentVariableError,
    UnexpectedTypeError,
    UnknownTypeError,
    NestedMissingEnvironmentVariableError,
)


class TestEnvify(unittest.TestCase):
    test_prefix = "TEST_ENV_VARS"

    def setUp(self) -> None:
        self.clear_test_env_vars()
        self.envify = Envify()

    def tearDown(self) -> None:
        self.clear_test_env_vars()

    def clear_test_env_vars(self) -> None:
        for env in os.environ:
            if env.startswith(self.test_prefix):
                del os.environ[env]

    def test_envify_with_attr_class_should_return_using_attr_field_default_value_if_none_env_var(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            a: int
            b: int = 5

        os.environ[f"{self.test_prefix}_A"] = "1"
        self.assertEqual(
            AttrClass(
                a=1,
                b=5,
            ),
            self.envify.envify(self.test_prefix, AttrClass),
        )

    def test_envify_should_return_with_nested_attr_class(self):
        @attr.s(auto_attribs=True)
        class ChildClass:
            field: str

        @attr.s(auto_attribs=True)
        class ParentClass:
            child: ChildClass

        os.environ[f"{self.test_prefix}_CHILD_FIELD"] = "value"
        self.assertEqual(
            ParentClass(child=ChildClass(field="value")), self.envify.envify(self.test_prefix, ParentClass)
        )

    def test_envify_with_attr_class_should_return_using_attr_with_nested_list(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            b: List[str] = None

        os.environ[f"{self.test_prefix}_B_0"] = "value 1"
        os.environ[f"{self.test_prefix}_B_1"] = "value 2"
        self.assertEqual(
            AttrClass(
                b=[
                    "value 1",
                    "value 2",
                ]
            ),
            self.envify.envify(self.test_prefix, AttrClass),
        )

    def test_envify_with_attr_class_should_return_using_field_with_optional(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            b: Optional[str]

        self.assertEqual(AttrClass(b=None), self.envify.envify(self.test_prefix, AttrClass))

    def test_envify_with_attr_class_should_return_using_optional_field_with_default_value(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            b: Optional[str] = attr.Factory(lambda: "value")

        self.assertEqual(AttrClass(b=None), self.envify.envify(self.test_prefix, AttrClass))

    def test_envify_with_attr_class_should_return_using_attr_with_optional_and_not_optional(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            a: str
            b: Optional[str]

        os.environ[f"{self.test_prefix}_A"] = "Hello"
        self.assertEqual(AttrClass(a="Hello", b=None), self.envify.envify(self.test_prefix, AttrClass))

    def test_envify_should_return_for_primitive_types(self):
        os.environ[f"{self.test_prefix}_BOOL_TRUE"] = "true"
        self.assertEqual(True, self.envify.envify(f"{self.test_prefix}_BOOL_TRUE", bool))
        os.environ[f"{self.test_prefix}_BOOL_FALSE"] = "false"
        self.assertEqual(False, self.envify.envify(f"{self.test_prefix}_BOOL_FALSE", bool))
        os.environ[f"{self.test_prefix}_STR"] = "str"
        self.assertEqual("str", self.envify.envify(f"{self.test_prefix}_STR", str))
        os.environ[f"{self.test_prefix}_INT"] = "1993"
        self.assertEqual(1993, self.envify.envify(f"{self.test_prefix}_INT", int))
        os.environ[f"{self.test_prefix}_FLOAT"] = "3.14"
        self.assertEqual(3.14, self.envify.envify(f"{self.test_prefix}_FLOAT", float))

    def test_envify_should_raise_cast_error_for_primitive_type_if_no_cast(self):
        os.environ[f"{self.test_prefix}_BOOL"] = "unknown"
        with self.assertRaises(CastError) as expected:
            self.envify.envify(f"{self.test_prefix}_BOOL", bool)
        self.assertEqual(f"Failed to convert '{self.test_prefix}_BOOL' to bool.", str(expected.exception))
        os.environ[f"{self.test_prefix}_INT"] = "str"
        with self.assertRaises(CastError) as expected:
            self.envify.envify(f"{self.test_prefix}_INT", int)
        self.assertEqual(f"Failed to convert '{self.test_prefix}_INT' to int.", str(expected.exception))

    def test_should_raise_missing_env_error_if_env_var_is_not_set(self):
        with self.assertRaises(MissingEnvironmentVariableError) as expected:
            self.envify.envify(f"{self.test_prefix}_BOOL", bool)
        self.assertEqual(f"Environment variable '{self.test_prefix}_BOOL' is not set.", str(expected.exception))
        with self.assertRaises(MissingEnvironmentVariableError) as expected:
            self.envify.envify(f"{self.test_prefix}_INT", int)
        self.assertEqual(f"Environment variable '{self.test_prefix}_INT' is not set.", str(expected.exception))

        @attr.s(auto_attribs=True)
        class AttrClass:
            a: int

        with self.assertRaises(NestedMissingEnvironmentVariableError) as expected:
            self.envify.envify(f"{self.test_prefix}_ATTR_CLASS", AttrClass)
        self.assertEqual(f"Environment variable '{self.test_prefix}_ATTR_CLASS_A' is not set.", str(expected.exception))

        @dataclasses.dataclass
        class DataClass:
            a: int

        with self.assertRaises(NestedMissingEnvironmentVariableError) as expected:
            self.envify.envify(f"{self.test_prefix}_DATA_CLASS", DataClass)
        self.assertEqual(f"Environment variable '{self.test_prefix}_DATA_CLASS_A' is not set.", str(expected.exception))

    def test_should_return_from_list_type(self):
        os.environ[f"{self.test_prefix}_0"] = "str 1"
        os.environ[f"{self.test_prefix}_1"] = "str 2"
        self.assertEqual(["str 1", "str 2"], self.envify.envify(self.test_prefix, List[str]))

    def test_should_return_empty_list(self):
        self.assertEqual([], self.envify.envify(self.test_prefix, List[int]))
        self.assertEqual([], self.envify.envify(self.test_prefix, List[bool]))
        self.assertEqual([], self.envify.envify(self.test_prefix, List[Optional[int]]))

        @attr.s(auto_attribs=True)
        class AttrClass:
            a: int

        self.assertEqual([], self.envify.envify(self.test_prefix, List[AttrClass]))

        @dataclasses.dataclass
        class DataClass:
            a: int

        self.assertEqual([], self.envify.envify(self.test_prefix, List[DataClass]))

    def test_should_return_with_optional_unset(self):
        self.assertEqual(None, self.envify.envify(self.test_prefix, Optional[str]))

    def test_should_return_with_optional_set(self):
        os.environ[f"{self.test_prefix}"] = "str"
        self.assertEqual("str", self.envify.envify(self.test_prefix, Optional[str]))

    def test_should_return_optional_of_attr_class(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            a: int

        self.assertEqual(None, self.envify.envify(self.test_prefix, Optional[AttrClass]))

    def test_should_return_attr_class_with_default_field(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            a: bool = False

        self.assertEqual(AttrClass(), self.envify.envify(self.test_prefix, AttrClass))

    def test_should_return_option_list(self):
        self.assertIsNone(self.envify.envify(self.test_prefix, Optional[List]))

    def test_envify_with_dataclass_class_should_return_using_dataclass_default_value_if_none(self):
        @dataclasses.dataclass
        class DataClass:
            a: int
            b: int = 5

        os.environ[f"{self.test_prefix}_A"] = "1"
        self.assertEqual(
            DataClass(
                a=1,
                b=5,
            ),
            self.envify.envify(self.test_prefix, DataClass),
        )

    def test_envify_should_return_with_nested_dataclass_class(self):
        @dataclasses.dataclass
        class ChildClass:
            field: str

        @dataclasses.dataclass
        class ParentClass:
            child: ChildClass

        os.environ[f"{self.test_prefix}_CHILD_FIELD"] = "value"
        self.assertEqual(
            ParentClass(child=ChildClass(field="value")), self.envify.envify(self.test_prefix, ParentClass)
        )

    def test_envify_with_dataclass_class_should_return_using_dataclass_with_nested_list(self):
        @dataclasses.dataclass
        class DataClass:
            b: List[str] = None

        os.environ[f"{self.test_prefix}_B_0"] = "value 1"
        os.environ[f"{self.test_prefix}_B_1"] = "value 2"
        self.assertEqual(
            DataClass(
                b=[
                    "value 1",
                    "value 2",
                ]
            ),
            self.envify.envify(self.test_prefix, DataClass),
        )

    def test_envify_with_dataclass_class_should_return_using_dataclass_with_optional(self):
        @dataclasses.dataclass
        class DataClass:
            b: Optional[str]

        self.assertEqual(DataClass(b=None), self.envify.envify(self.test_prefix, DataClass))

    def test_envify_with_dataclass_class_should_return_using_dataclass_with_optional_and_not_optional(
        self,
    ):
        @dataclasses.dataclass
        class DataClass:
            a: str
            b: Optional[str]

        os.environ[f"{self.test_prefix}_A"] = "Hello"
        self.assertEqual(DataClass(a="Hello", b=None), self.envify.envify(self.test_prefix, DataClass))

    def test_should_raise_missing_env_error_if_env_var_is_not_set_in_dataclass(self):
        @dataclasses.dataclass
        class DataClass:
            a: int

        with self.assertRaises(NestedMissingEnvironmentVariableError) as expected:
            self.envify.envify(f"{self.test_prefix}_ATTR_CLASS", DataClass)
        self.assertEqual(f"Environment variable '{self.test_prefix}_ATTR_CLASS_A' is not set.", str(expected.exception))

    def test_should_raise_error_if_partial_env_var_found_for_data_class(self):
        @dataclasses.dataclass
        class DataClass:
            a: int
            b: int

        os.environ[f"{self.test_prefix}_A"] = "5"

        with self.assertRaises(NestedMissingEnvironmentVariableError) as expected:
            self.envify.envify(self.test_prefix, DataClass)
        self.assertEqual(f"Environment variable '{self.test_prefix}_B' is not set.", str(expected.exception))

    def test_should_return_optional_of_dataclass_class(self):
        @dataclasses.dataclass
        class DataClass:
            a: int

        self.assertEqual(None, self.envify.envify(self.test_prefix, Optional[DataClass]))

    def test_should_return_dataclass_class_if_only_default_field(self):
        @dataclasses.dataclass
        class DataClass:
            a: bool = False

        self.assertEqual(DataClass(), self.envify.envify(self.test_prefix, DataClass))

    def test_envify_on_unsupported_class_should_raise_error(self):
        class NotADataClass:
            pass

        with self.assertRaises(UnexpectedTypeError) as expected:
            self.envify.envify(self.test_prefix, NotADataClass)
        self.assertEqual(
            'Unsupported type "NotADataClass" for property at path "TEST_ENV_VARS"', str(expected.exception)
        )

    def test_envify_list_of_dataclass_should_raise_error_on_nested_missing_variable(self):
        @dataclasses.dataclass
        class DataClass:
            a: bool
            b: int

        os.environ[f"{self.test_prefix}_0_A"] = "TRUE"

        with self.assertRaises(NestedMissingEnvironmentVariableError) as expected:
            self.envify.envify(self.test_prefix, List[DataClass])
        self.assertEqual(f"Environment variable '{self.test_prefix}_0_B' is not set.", str(expected.exception))

    def test_envify_should_return_error_if_encounter_list_without_generic_arg(self):
        with self.assertRaises(UnknownTypeError) as expected:
            self.envify.envify(self.test_prefix, List)
        self.assertEqual(f'Unknown generic type for property at path "{self.test_prefix}"', str(expected.exception))

    def test_envify_should_return_enum_with_str_values(self):
        class MyEnum(enum.Enum):
            VAL1 = "val1"
            VAL2 = "val2"

        os.environ[self.test_prefix] = "val1"
        self.assertEqual(MyEnum.VAL1, self.envify.envify(self.test_prefix, MyEnum))
        os.environ[self.test_prefix] = "val2"
        self.assertEqual(MyEnum.VAL2, self.envify.envify(self.test_prefix, MyEnum))

        with self.assertRaises(CastError) as expected:
            os.environ[self.test_prefix] = "unknown"
            self.envify.envify(self.test_prefix, MyEnum)
        self.assertEqual(f"Failed to convert '{self.test_prefix}' to MyEnum.", str(expected.exception))

    def test_envify_should_return_enum_with_int_values(self):
        class MyEnum(enum.Enum):
            VAL1 = 1
            VAL2 = 2

        os.environ[self.test_prefix] = "1"
        self.assertEqual(MyEnum.VAL1, self.envify.envify(self.test_prefix, MyEnum))
        os.environ[self.test_prefix] = "2"
        self.assertEqual(MyEnum.VAL2, self.envify.envify(self.test_prefix, MyEnum))

        with self.assertRaises(CastError) as expected:
            os.environ[self.test_prefix] = "3"
            self.envify.envify(self.test_prefix, MyEnum)
        self.assertEqual(f"Failed to convert '{self.test_prefix}' to MyEnum.", str(expected.exception))

    def test_envify_should_return_enum_with_auto_values(self):
        class MyEnum(enum.Enum):
            VAL1 = enum.auto()
            VAL2 = enum.auto()

        os.environ[self.test_prefix] = "1"
        self.assertEqual(MyEnum.VAL1, self.envify.envify(self.test_prefix, MyEnum))
        os.environ[self.test_prefix] = "2"
        self.assertEqual(MyEnum.VAL2, self.envify.envify(self.test_prefix, MyEnum))

        with self.assertRaises(CastError) as expected:
            os.environ[self.test_prefix] = "3"
            self.envify.envify(self.test_prefix, MyEnum)
        self.assertEqual(f"Failed to convert '{self.test_prefix}' to MyEnum.", str(expected.exception))

    def test_envify_should_raise_error_if_enum_type_values_are_not_int_or_string(self):
        class CustomObject:
            def __init__(self, value):
                self.value = value

            def __hash__(self):
                return hash(self.value)

        class MyEnum(enum.Enum):
            VALUE1 = CustomObject("a")
            VALUE2 = CustomObject("b")

        with self.assertRaises(UnexpectedTypeError) as expected:
            os.environ[self.test_prefix] = "1"
            self.envify.envify(self.test_prefix, MyEnum)
        self.assertEqual('Unsupported type "MyEnum" for property at path "TEST_ENV_VARS"', str(expected.exception))

    def test_envify_should_return_exception_if_no_env_value_when_parsing_enum(self):
        class MyEnum(enum.Enum):
            VAL1 = 1
            VAL2 = 2

        with self.assertRaises(MissingEnvironmentVariableError) as expected:
            self.envify.envify(self.test_prefix, MyEnum)
        self.assertEqual("Environment variable 'TEST_ENV_VARS' is not set.", str(expected.exception))

    def test_envify_with_nested_enum(self):
        class MyEnum(enum.Enum):
            VAL1 = 1
            VAL2 = 2

        @dataclasses.dataclass
        class DataClass:
            a: MyEnum
            b: MyEnum = MyEnum.VAL2

        os.environ[f"{self.test_prefix}_A"] = "1"
        self.assertEqual(
            DataClass(
                a=MyEnum.VAL1,
                b=MyEnum.VAL2,
            ),
            self.envify.envify(self.test_prefix, DataClass),
        )
