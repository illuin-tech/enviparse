# Envify

## Description

Envify let you simply create dataclasses from environment variable.

Supported types are : 
* int
* float
* str
* bool
* optional
* list
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
import os

os.environ["DATABASE_CONFIG_USERNAME"]="postgres"
os.environ["DATABASE_CONFIG_PASSWORD"]="password"
os.environ["DATABASE_HOST"]="127.0.0.1"
os.environ["DATABASE_PORT"]="5432"
os.environ["DATABASE_NAME"]="appdb"

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