import dataclasses
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
    TEST_PREFIX = "TEST_ENV_VARS"

    def setUp(self) -> None:
        self.clear_test_env_vars()
        self.envify = Envify()

    def tearDown(self) -> None:
        self.clear_test_env_vars()

    def clear_test_env_vars(self) -> None:
        for env in os.environ.keys():
            if env.startswith(self.TEST_PREFIX):
                del os.environ[env]

    def test_envify_with_attr_class_should_return_using_attr_field_default_value_if_none_env_var(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            a: int
            b: int = 5

        os.environ[f"{self.TEST_PREFIX}_A"] = "1"
        self.assertEqual(
            AttrClass(
                a=1,
                b=5,
            ),
            self.envify.envify(self.TEST_PREFIX, AttrClass),
        )

    def test_envify_should_return_with_nested_attr_class(self):
        @attr.s(auto_attribs=True)
        class ChildClass:
            field: str

        @attr.s(auto_attribs=True)
        class ParentClass:
            child: ChildClass

        os.environ[f"{self.TEST_PREFIX}_CHILD_FIELD"] = "value"
        self.assertEqual(
            ParentClass(child=ChildClass(field="value")), self.envify.envify(self.TEST_PREFIX, ParentClass)
        )

    def test_envify_with_attr_class_should_return_using_attr_with_nested_list(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            b: List[str] = None

        os.environ[f"{self.TEST_PREFIX}_B_0"] = "value 1"
        os.environ[f"{self.TEST_PREFIX}_B_1"] = "value 2"
        self.assertEqual(
            AttrClass(
                b=[
                    "value 1",
                    "value 2",
                ]
            ),
            self.envify.envify(self.TEST_PREFIX, AttrClass),
        )

    def test_envify_with_attr_class_should_return_using_field_with_optional(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            b: Optional[str]

        self.assertEqual(AttrClass(b=None), self.envify.envify(self.TEST_PREFIX, AttrClass))

    def test_envify_with_attr_class_should_return_using_optional_field_with_default_value(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            b: Optional[str] = attr.Factory(lambda: "value")

        self.assertEqual(AttrClass(b=None), self.envify.envify(self.TEST_PREFIX, AttrClass))

    def test_envify_with_attr_class_should_return_using_attr_with_optional_and_not_optional(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            a: str
            b: Optional[str]

        os.environ[f"{self.TEST_PREFIX}_A"] = "Hello"
        self.assertEqual(AttrClass(a="Hello", b=None), self.envify.envify(self.TEST_PREFIX, AttrClass))

    def test_envify_should_return_for_primitive_types(self):
        os.environ[f"{self.TEST_PREFIX}_BOOL_TRUE"] = "true"
        self.assertEqual(True, self.envify.envify(f"{self.TEST_PREFIX}_BOOL_TRUE", bool))
        os.environ[f"{self.TEST_PREFIX}_BOOL_FALSE"] = "false"
        self.assertEqual(False, self.envify.envify(f"{self.TEST_PREFIX}_BOOL_FALSE", bool))
        os.environ[f"{self.TEST_PREFIX}_STR"] = "str"
        self.assertEqual("str", self.envify.envify(f"{self.TEST_PREFIX}_STR", str))
        os.environ[f"{self.TEST_PREFIX}_INT"] = "1993"
        self.assertEqual(1993, self.envify.envify(f"{self.TEST_PREFIX}_INT", int))
        os.environ[f"{self.TEST_PREFIX}_FLOAT"] = "3.14"
        self.assertEqual(3.14, self.envify.envify(f"{self.TEST_PREFIX}_FLOAT", float))

    def test_envify_should_raise_cast_error_for_primitive_type_if_no_cast(self):
        os.environ[f"{self.TEST_PREFIX}_BOOL"] = "unknown"
        with self.assertRaises(CastError) as expected:
            self.envify.envify(f"{self.TEST_PREFIX}_BOOL", bool)
        self.assertEqual(f"Failed to convert '{self.TEST_PREFIX}_BOOL' to bool.", str(expected.exception))
        os.environ[f"{self.TEST_PREFIX}_INT"] = "str"
        with self.assertRaises(CastError) as expected:
            self.envify.envify(f"{self.TEST_PREFIX}_INT", int)
        self.assertEqual(f"Failed to convert '{self.TEST_PREFIX}_INT' to int.", str(expected.exception))

    def test_should_raise_missing_env_error_if_env_var_is_not_set(self):
        with self.assertRaises(MissingEnvironmentVariableError) as expected:
            self.envify.envify(f"{self.TEST_PREFIX}_BOOL", bool)
        self.assertEquals(f"Environment variable '{self.TEST_PREFIX}_BOOL' is not set.", str(expected.exception))
        with self.assertRaises(MissingEnvironmentVariableError) as expected:
            self.envify.envify(f"{self.TEST_PREFIX}_INT", int)
        self.assertEquals(f"Environment variable '{self.TEST_PREFIX}_INT' is not set.", str(expected.exception))

        @attr.s(auto_attribs=True)
        class AttrClass:
            a: int

        with self.assertRaises(NestedMissingEnvironmentVariableError) as expected:
            self.envify.envify(f"{self.TEST_PREFIX}_ATTR_CLASS", AttrClass)
        self.assertEquals(
            f"Environment variable '{self.TEST_PREFIX}_ATTR_CLASS_A' is not set.", str(expected.exception)
        )

        @dataclasses.dataclass
        class DataClass:
            a: int

        with self.assertRaises(NestedMissingEnvironmentVariableError) as expected:
            self.envify.envify(f"{self.TEST_PREFIX}_DATA_CLASS", DataClass)
        self.assertEquals(
            f"Environment variable '{self.TEST_PREFIX}_DATA_CLASS_A' is not set.", str(expected.exception)
        )

    def test_should_return_from_list_type(self):
        os.environ[f"{self.TEST_PREFIX}_0"] = "str 1"
        os.environ[f"{self.TEST_PREFIX}_1"] = "str 2"
        self.assertEqual(["str 1", "str 2"], self.envify.envify(self.TEST_PREFIX, List[str]))

    def test_should_return_empty_list(self):
        self.assertEqual([], self.envify.envify(self.TEST_PREFIX, List[int]))
        self.assertEqual([], self.envify.envify(self.TEST_PREFIX, List[bool]))
        self.assertEqual([], self.envify.envify(self.TEST_PREFIX, List[Optional[int]]))

        @attr.s(auto_attribs=True)
        class AttrClass:
            a: int

        self.assertEqual([], self.envify.envify(self.TEST_PREFIX, List[AttrClass]))

        @dataclasses.dataclass
        class DataClass:
            a: int

        self.assertEqual([], self.envify.envify(self.TEST_PREFIX, List[DataClass]))

    def test_should_return_with_optional_unset(self):
        self.assertEqual(None, self.envify.envify(self.TEST_PREFIX, Optional[str]))

    def test_should_return_with_optional_set(self):
        os.environ[f"{self.TEST_PREFIX}"] = "str"
        self.assertEqual("str", self.envify.envify(self.TEST_PREFIX, Optional[str]))

    def test_should_return_optional_of_attr_class(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            a: int

        self.assertEqual(None, self.envify.envify(self.TEST_PREFIX, Optional[AttrClass]))

    def test_should_return_attr_class_with_default_field(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            a: bool = False

        self.assertEqual(AttrClass(), self.envify.envify(self.TEST_PREFIX, AttrClass))

    def test_should_return_option_list(self):
        self.assertIsNone(self.envify.envify(self.TEST_PREFIX, Optional[List]))

    def test_envify_with_dataclass_class_should_return_using_dataclass_default_value_if_none(self):
        @dataclasses.dataclass
        class DataClass:
            a: int
            b: int = 5

        os.environ[f"{self.TEST_PREFIX}_A"] = "1"
        self.assertEqual(
            DataClass(
                a=1,
                b=5,
            ),
            self.envify.envify(self.TEST_PREFIX, DataClass),
        )

    def test_envify_should_return_with_nested_dataclass_class(self):
        @dataclasses.dataclass
        class ChildClass:
            field: str

        @dataclasses.dataclass
        class ParentClass:
            child: ChildClass

        os.environ[f"{self.TEST_PREFIX}_CHILD_FIELD"] = "value"
        self.assertEqual(
            ParentClass(child=ChildClass(field="value")), self.envify.envify(self.TEST_PREFIX, ParentClass)
        )

    def test_envify_with_dataclass_class_should_return_using_dataclass_with_nested_list(self):
        @dataclasses.dataclass
        class DataClass:
            b: List[str] = None

        os.environ[f"{self.TEST_PREFIX}_B_0"] = "value 1"
        os.environ[f"{self.TEST_PREFIX}_B_1"] = "value 2"
        self.assertEqual(
            DataClass(
                b=[
                    "value 1",
                    "value 2",
                ]
            ),
            self.envify.envify(self.TEST_PREFIX, DataClass),
        )

    def test_envify_with_dataclass_class_should_return_using_dataclass_with_optional(self):
        @dataclasses.dataclass
        class DataClass:
            b: Optional[str]

        self.assertEqual(DataClass(b=None), self.envify.envify(self.TEST_PREFIX, DataClass))

    def test_envify_with_dataclass_class_should_return_using_dataclass_with_optional_and_not_optional(
        self,
    ):
        @dataclasses.dataclass
        class DataClass:
            a: str
            b: Optional[str]

        os.environ[f"{self.TEST_PREFIX}_A"] = "Hello"
        self.assertEqual(DataClass(a="Hello", b=None), self.envify.envify(self.TEST_PREFIX, DataClass))

    def test_should_raise_missing_env_error_if_env_var_is_not_set_in_dataclass(self):
        @dataclasses.dataclass
        class DataClass:
            a: int

        with self.assertRaises(NestedMissingEnvironmentVariableError) as expected:
            self.envify.envify(f"{self.TEST_PREFIX}_ATTR_CLASS", DataClass)
        self.assertEquals(
            f"Environment variable '{self.TEST_PREFIX}_ATTR_CLASS_A' is not set.", str(expected.exception)
        )

    def test_should_raise_error_if_partial_env_var_found_for_data_class(self):
        @dataclasses.dataclass
        class DataClass:
            a: int
            b: int

        os.environ[f"{self.TEST_PREFIX}_A"] = "5"

        with self.assertRaises(NestedMissingEnvironmentVariableError) as expected:
            self.envify.envify(self.TEST_PREFIX, DataClass)
        self.assertEquals(f"Environment variable '{self.TEST_PREFIX}_B' is not set.", str(expected.exception))

    def test_should_return_optional_of_dataclass_class(self):
        @dataclasses.dataclass
        class DataClass:
            a: int

        self.assertEqual(None, self.envify.envify(self.TEST_PREFIX, Optional[DataClass]))

    def test_should_return_dataclass_class_if_only_default_field(self):
        @dataclasses.dataclass
        class DataClass:
            a: bool = False

        self.assertEqual(DataClass(), self.envify.envify(self.TEST_PREFIX, DataClass))

    def test_envify_on_unsupported_class_should_raise_error(self):
        class NotADataClass:
            pass

        with self.assertRaises(UnexpectedTypeError) as expected:
            self.envify.envify(self.TEST_PREFIX, NotADataClass)
        self.assertEquals(
            'Unsupported type "NotADataClass" for property at path "TEST_ENV_VARS"', str(expected.exception)
        )

    def test_envify_list_of_dataclass_should_raise_error_on_nested_missing_variable(self):
        @dataclasses.dataclass
        class DataClass:
            a: bool
            b: int

        os.environ[f"{self.TEST_PREFIX}_0_A"] = "TRUE"

        with self.assertRaises(NestedMissingEnvironmentVariableError) as expected:
            self.envify.envify(self.TEST_PREFIX, List[DataClass])
        self.assertEquals(f"Environment variable '{self.TEST_PREFIX}_0_B' is not set.", str(expected.exception))

    def test_envify_should_return_error_if_encounter_list_without_generic_arg(self):
        with self.assertRaises(UnknownTypeError) as expected:
            self.envify.envify(self.TEST_PREFIX, List)
        self.assertEqual(f'Unknown generic type for property at path "{self.TEST_PREFIX}"', str(expected.exception))
