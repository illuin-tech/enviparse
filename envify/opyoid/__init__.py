from typing import Type, Optional

from opyoid import Provider

from ..envify import ClassType, Envify


def envify_provider(prefix: str, config_type: Type[ClassType]) -> Type[Provider[ClassType]]:
    class EnvifyProvider(Provider[ClassType]):
        def __init__(self, envify: Optional[Envify]):
            self._envify = envify or Envify()

        def get(self) -> ClassType:
            return self._envify.envify(prefix, config_type)

    return EnvifyProvider
