import dataclasses
import os
import unittest
from typing import Optional, List

import attr

from envify import Envify, CastError, MissingEnvironmentVariableError, UnexpectedTypeError


class TestEnvVars(unittest.TestCase):
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

    def test_envify_with_attr_class_should_return_using_attr_default_value_if_none(self):
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

    def test_envify_with_attr_class_should_return_using_attr_with_optional(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            b: Optional[str]

        self.assertEqual(AttrClass(b=None), self.envify.envify(self.TEST_PREFIX, AttrClass))

    def test_envify_with_attr_class_should_return_using_attr_with_optional_and_not_optional(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            a: str
            b: Optional[str]

        os.environ[f"{self.TEST_PREFIX}_A"] = "Hello"
        self.assertEqual(AttrClass(a="Hello", b=None), self.envify.envify(self.TEST_PREFIX, AttrClass))

    def test_envify_should_return_from_optional_type_when_set(self):
        os.environ[f"{self.TEST_PREFIX}_VALUE"] = "hello world"
        self.assertEqual("hello world", self.envify.envify(f"{self.TEST_PREFIX}_VALUE", Optional[str]))

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
        with self.assertRaises(CastError):
            self.envify.envify(f"{self.TEST_PREFIX}_BOOL", bool)
        os.environ[f"{self.TEST_PREFIX}_INT"] = "str"
        with self.assertRaises(CastError):
            self.envify.envify(f"{self.TEST_PREFIX}_INT", int)

    def test_should_raise_missing_env_error_if_env_var_is_not_set(self):
        with self.assertRaises(MissingEnvironmentVariableError):
            self.envify.envify(f"{self.TEST_PREFIX}_BOOL", bool)
        with self.assertRaises(MissingEnvironmentVariableError):
            self.envify.envify(f"{self.TEST_PREFIX}_INT", int)

        @attr.s(auto_attribs=True)
        class AttrClass:
            a: int

        with self.assertRaises(MissingEnvironmentVariableError):
            self.envify.envify(f"{self.TEST_PREFIX}_ATTR_CLASS", AttrClass)

    def test_should_return_from_list_type(self):
        os.environ[f"{self.TEST_PREFIX}_0"] = "str 1"
        os.environ[f"{self.TEST_PREFIX}_1"] = "str 2"
        self.assertEqual(["str 1", "str 2"], self.envify.envify(self.TEST_PREFIX, List[str]))

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

    def test_should_use_default_value_even_if_attr_has_default(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            a: bool = False

        default_value = AttrClass(a=True)
        self.assertEqual(default_value, self.envify.envify(self.TEST_PREFIX, AttrClass, default_value))

    def test_should_return_attr_class_if_only_default_field(self):
        @attr.s(auto_attribs=True)
        class AttrClass:
            a: bool = False

        self.assertEqual(AttrClass(), self.envify.envify(self.TEST_PREFIX, AttrClass))

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

        with self.assertRaises(MissingEnvironmentVariableError):
            self.envify.envify(f"{self.TEST_PREFIX}_ATTR_CLASS", DataClass)

    def test_should_return_optional_of_dataclass_class(self):
        @dataclasses.dataclass
        class DataClass:
            a: int

        self.assertEqual(None, self.envify.envify(self.TEST_PREFIX, Optional[DataClass]))

    def test_should_use_default_value_even_if_dataclass_has_default(self):
        @dataclasses.dataclass
        class DataClass:
            a: bool = False

        default_value = DataClass(a=True)
        self.assertEqual(default_value, self.envify.envify(self.TEST_PREFIX, DataClass, default_value))

    def test_should_return_dataclass_class_if_only_default_field(self):
        @dataclasses.dataclass
        class DataClass:
            a: bool = False

        self.assertEqual(DataClass(), self.envify.envify(self.TEST_PREFIX, DataClass))

    def test_envify_on_unsupported_class_should_raise_error(self):
        class NoDataClass:
            pass

        with self.assertRaises(UnexpectedTypeError):
            self.envify.envify(self.TEST_PREFIX, NoDataClass)
