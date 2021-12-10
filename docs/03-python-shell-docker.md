# Flows with Python, Shell & Docker

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

[1] https://docs.prefect.io/api/latest/tasks/shell.html#shelltask

[2] https://docs.prefect.io/api/latest/tasks/docker.html#startcontainer
