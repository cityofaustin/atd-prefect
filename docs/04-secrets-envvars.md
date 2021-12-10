# Secrets and Environment Varibles

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


## Sources

[1] https://docs.prefect.io/api/latest/tasks/secrets.html#prefectsecret

[2] https://docs.prefect.io/api/latest/tasks/secrets.html#envvarsecret
