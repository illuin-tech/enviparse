class EnviparseError(Exception):
    pass


class UnexpectedTypeError(EnviparseError):
    def __init__(self, used_type: str, path: str):
        super().__init__(f'Unsupported type "{used_type}" for property at path "{path}"')


class UnknownTypeError(EnviparseError):
    def __init__(self, path: str):
        super().__init__(f'Unknown generic type for property at path "{path}"')


class MissingEnvironmentVariableError(EnviparseError):
    def __init__(self, env_var_name: str):
        super().__init__(f"Environment variable '{env_var_name}' is not set.")


class NestedMissingEnvironmentVariableError(EnviparseError):
    def __init__(self, env_var_name: str):
        super().__init__(f"Environment variable '{env_var_name}' is not set.")


class CastError(EnviparseError):
    def __init__(self, env_var_name: str, data_type: str):
        super().__init__(f"Failed to convert '{env_var_name}' to {data_type}.")
