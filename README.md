# Envify

![CI](https://github.com/illuin-tech/envify/workflows/CI/badge.svg)
[![codecov](https://codecov.io/gh/illuin-tech/envify/branch/main/graph/badge.svg)](https://codecov.io/gh/illuin-tech/envify)


## Description

Envify let you simply create dataclasses from environment variable.

Supported types are : 
* int
* float
* str
* bool
* optional
* list
* enum (with int or string values only)
* `@attr` annotated class
* `@dataclasses.dataclass` annotated class

# Example

With following environment variables :
```bash
DATABASE_CONFIG_USERNAME=postgres
DATABASE_CONFIG_PASSWORD=password
DATABASE_CONFIG_HOST=127.0.0.1
DATABASE_CONFIG_PORT=5432
DATABASE_CONFIG_DATABASE_NAME=appdb
```

You can parse environment variable with :
```python
import dataclasses
from envify import Envify

@dataclasses.dataclass
class DatabaseConfig:
    username: str
    password: str
    host: str
    port: int
    database_name: str

db_config = Envify().envify("DATABASE_CONFIG", DatabaseConfig)
print(db_config)
```

You should get the following result :
```
DatabaseConfig(username='postgres', password='password', host='127.0.0.1', port=5432, database_name='appdb')
```

For more example see the [test folder](./tests).