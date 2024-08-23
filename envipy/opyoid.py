from typing import Type, Optional

from opyoid import Provider

from .envipy import ClassTypeT, Envipy


def envipy_provider(prefix: str, config_type: Type[ClassTypeT]) -> Type[Provider[ClassTypeT]]:
    class EnvipyProvider(Provider[ClassTypeT]):
        def __init__(self, envipy: Optional[Envipy] = None):
            self._envipy = envipy or Envipy()

        def get(self) -> ClassTypeT:
            return self._envipy.envipy(prefix, config_type)

    return EnvipyProvider
