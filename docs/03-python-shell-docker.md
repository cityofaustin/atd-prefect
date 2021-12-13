# Flows with Python, Shell & Docker

## Shell

Prefect has a simple implementation called `ShellTask`
which can be used as easily as follows:

```python
from prefect.tasks.shell import ShellTask

environment_variables = {
    "MESSAGE": "HELLO WORLD"
}

shell_task = ShellTask(
    name="shell_task",
    command='echo "MESSAGE: ${MESSAGE}"',
    env=environment_variables,
    stream_output=True
)

[...]

    flow.add_task(shell_task)
```


## Python

Running python is not as different, we use 
the same ShellTask class and we mix it up:

```python
from prefect.tasks.shell import ShellTask

environment_variables = {
    "MESSAGE": "HELLO WORLD"
}

python_task = ShellTask(
    name="python_task",
    command='python3 /static/path/of/example.py',
    env=environment_variables,
    stream_output=True
)

[...]

    flow.add_task(python_task)
```

This is assuming that there is a known static location
of the `/static/path/of/example.py` python file.

## Docker

Running docker tasks using Prefect's library is
much different that it is in Airflow, unfortunately.

To make the transition to Prefect as easy as possible,
we can use the included docker-py library, like so:

```python
# Running a Docker task with docker-py
import prefect, docker

environment_variables = {
    "MESSAGE": "HELLO WORLD"
}

@task(name="docker_with_api")
def docker_with_api():
    client = docker.from_env()

    response = client.containers.run(
        image="python:alpine",
        working_dir="/app",
        command="echo $MESSAGE",
        environment=environment_variables,
        volumes=None,
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")

    logger = prefect.context.get("logger")
    logger.info(response)

    return response
```

For more details on how to run docker using the api
follow docker-py's documentation.

https://docker-py.readthedocs.io/en/stable/


## Sources

Shell Task:
- https://docs.prefect.io/api/latest/tasks/shell.html#shelltask

Docker:
- https://docker-py.readthedocs.io/
- https://docs.prefect.io/api/latest/tasks/docker.html#startcontainer
