import os
import unittest

from envify.opyoid import envify_provider


class TestEnvifyOpyoidProviderFactory(unittest.TestCase):
    TEST_PREFIX = "TEST_ENV_VARS"

    def setUp(self) -> None:
        self.clear_test_env_vars()

    def tearDown(self) -> None:
        self.clear_test_env_vars()

    def clear_test_env_vars(self) -> None:
        for env in os.environ.keys():
            if env.startswith(self.TEST_PREFIX):
                del os.environ[env]

    def test_should_provide(self):
        os.environ[self.TEST_PREFIX] = "value"
        provider_type = envify_provider(self.TEST_PREFIX, str)
        self.assertEquals("value", provider_type().get())
