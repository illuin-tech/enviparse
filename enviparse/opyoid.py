from typing import Type, Optional

from opyoid import Provider

from .enviparse import ClassTypeT, Enviparse


def enviparse_provider(prefix: str, config_type: Type[ClassTypeT]) -> Type[Provider[ClassTypeT]]:
    class EnviparseProvider(Provider[ClassTypeT]):
        def __init__(self, enviparse: Optional[Enviparse] = None):
            self._parser = enviparse or Enviparse()

        def get(self) -> ClassTypeT:
            return self._parser.parse(prefix, config_type)

    return EnviparseProvider
