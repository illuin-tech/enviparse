from typing import Type, Optional

from opyoid import Provider

from .envify import ClassTypeT, Envify


def envify_provider(prefix: str, config_type: Type[ClassTypeT]) -> Type[Provider[ClassTypeT]]:
    class EnvifyProvider(Provider[ClassTypeT]):
        def __init__(self, envify: Optional[Envify] = None):
            self._envify = envify or Envify()

        def get(self) -> ClassTypeT:
            return self._envify.envify(prefix, config_type)

    return EnvifyProvider
