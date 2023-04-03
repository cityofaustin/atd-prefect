# Secrets, Environment Variables and KV Store

From prefect, there are two important considerations:

>1. Secrets are resolved locally first, falling back to Prefect Cloud (if supported). If you're using Prefect Server, only local secrets are supported

>2. We recommend using secrets stored in Prefect Cloud when possible, as these can be accessed in deployed flows in a uniform manner. Local secrets also work fine, but may require more work to deploy to remote environments.

Where are secrets stored?

- Locally: they are stored in the configuration file: `~/.prefect/config.toml`

- In Prefect: They are in Teams -> Secrets

## Creating Secrets

Locally, open the file `~/.prefect/config.toml` and if it
exists, it should look something like this:

```toml
[context.secrets]
MYSECRET = "MY SECRET VALUE"
```

In Prefect, visit the secrets page in Team -> Secrets
https://docs.prefect.io/orchestration/ui/team-settings.html#secrets

## Using Secrets

### 1. Pass secrets as task arguments

From Prefect's documentation we read:
>Where it makes sense, we recommend making the secret name configurable in your components (e.g. passed in as a parameter, perhaps with a default value) to support changing the secret name without changing the code. 

This is their suggested pattern:

```python
from prefect import task, Flow
from prefect.tasks.secrets import PrefectSecret

@task
def my_task(credentials):
    """A task that requires credentials to access something. Passing the
    credentials in as an argument allows you to change how/where the
    credentials are loaded (though we recommend using `PrefectSecret` tasks to
    load them."""
    pass

with Flow("example") as flow:
    my_secret = PrefectSecret("MYSECRET")
    res = my_task(credentials=my_secret)
```

### 2. Retrieve secrets directly:

There is also a direct way to retrieve secrets, and 
while they do not recommend this approach for tasks,
nothing is stopping us from using it outside of them
and use them as global variables:

```python
from prefect.client import Secret

# Load the value of `MYSECRET`
my_secret_value = Secret("MYSECRET").get()
```

## Key-Value Store

Another method to work with stored data is by making use
of the Key-Value store. We can set the values from the UI
or it can be done programmatically in Python.

From Prefect we read:

>Key Value Store is a managed metadata database for Prefect Cloud.
>Keys are strings. Values are JSON blobs.

> The number of key value pairs allowed is limited by license, starting with 10 pairs on the Free tier. Values are limited to 10 KB in size.

> Key value pairs can be configured via the Prefect CLI, Python library, API, and UI.

### Example Uses with Python

Setting Values: 

```python
from prefect.backend import set_key_value
key_value_uuid = set_key_value(key="foo", value="bar")
```

Getting values:

```python
from prefect.backend import get_key_value
value = get_key_value(key="foo")
```

Deleting Values:

```python
from prefect.backend import delete_key
success = delete_key(key="foo")
```

Listing Values:

```python
from prefect.backend import list_keys
my_keys = list_keys()
```

### Using a KV store in a flow

```python
from datetime import datetime, timedelta
import prefect
from prefect import task, Flow
from prefect.backend import set_key_value, get_key_value

LAST_EXECUTED_KEY = 'my-flow-last-executed'

@task
def get_last_execution_date():
    last_executed = get_key_value(LAST_EXECUTED_KEY)
    return datetime.strptime(last_executed, "%Y-%m-%d")

@task
def run_etl(start_date):
    logger = prefect.context.get("logger")
    while start_date <= datetime.today():
        logger.info(f"Running ETL for date {start_date.strftime('%Y-%m-%d')}")
        # do some etl
        start_date += timedelta(days=1)
    return start_date.strftime('%Y-%m-%d')

@task
def set_last_execution_date(date):
    set_key_value(key=LAST_EXECUTED_KEY, value=date)

with Flow('my-flow') as flow:
    last_executed_date = get_last_execution_date()
    final_execution_date = run_etl(last_executed_date)
    set_last_execution_date(final_execution_date)
```

## Sources

Secrets
- https://docs.prefect.io/api/latest/tasks/secrets.html#prefectsecret

Env Vars:
- https://docs.prefect.io/api/latest/tasks/secrets.html#envvarsecret

KV Store:
- https://docs.prefect.io/orchestration/concepts/kv_store.html
