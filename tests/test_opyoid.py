import os
import unittest

from envify.opyoid import envify_provider


class TestEnvifyOpyoidProviderFactory(unittest.TestCase):
    test_prefix = "TEST_ENV_VARS"

    def setUp(self) -> None:
        self.clear_test_env_vars()

    def tearDown(self) -> None:
        self.clear_test_env_vars()

    def clear_test_env_vars(self) -> None:
        for env in os.environ:
            if env.startswith(self.test_prefix):
                del os.environ[env]

    def test_should_provide(self):
        os.environ[self.test_prefix] = "value"
        provider_type = envify_provider(self.test_prefix, str)
        self.assertEqual("value", provider_type().get())
