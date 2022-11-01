# Prefect Agent Quickstart with Docker

The purpose of this tutorial is for you to learn how to go turn your relatively basic python script to an ETL that can run on a schedule and/or on our on-prem devices.

## 1. Basic Python Script

This file is just a starting place, we have two functions and a main function that calls them. This is a pretty common pattern we use whenever we develop our own Python scripts.

## 2. Prefect Local Basic

This script extends our original `basic_python_script.py` to work locally with Prefect. This is also called Prefect Core where there is no "agent" involved and the script is just run immediately. Although, you could also provide a `schedule` parameter to run this locally on some interval.

Note that we've replaced the `main()` function with `with Flow() as flow` and we've left our function calls the same as we left them in `main()`. The only other change is the `@task` decorator to the top of each function we're going to call in our flow.

```
@task
def add_one(val):
    return val + 1
```

```
with Flow("2-prefect_basic") as flow:
    val = add_one(1)
    print_res(val)
```

## 3. Prefect Basic Agent

The purpose of this script is to now register our flow with a local agent we'll start. To start your local agent simply type this in your command line while in the correct Prefect environment:

```
prefect agent local start -l youragentname -l local
```

The word "local" here is slightly confusing, once you start your local agent you can receive flows that are registered to your agent from the Prefect Cloud. It is "local" because it is running your flow as if it is local to your machine's environment that your started it in. So, if you are missing any packages like `pandas`, you'll need to use the `DockerRun` option below. 

The only two changes to this script is using the `LocalRun` run config:

```
run_config=LocalRun(labels=[youragentname, "local"])
```

and that we are now registering our flow to the Prefect Cloud at the end, instead of immediately running it:

```
flow.register("test")
```

When you run this script, and it is successfully registered you should get a URL to follow to see your flow and test it similar to: `Flow URL:https://cloud.prefect.io/...`. You can also go to our [Prefect cloud account](https://cloud.prefect.io/) and search for your flow there, called `3-prefect_basic_agent`. 

Once you are on the flow page, just click the "Quick Run" button on the top right corner to test it. You can also configure a schedule there if you like.


## 4. Prefect Docker Agent

The purpose of this file is to demonstrate the `DockerRun` run config to run our flow inside a docker container that contains our needed python dependencies. 

In this case, I'm using `pandas` to download a CSV from the open data portal.

To start a Docker agent simply run this command:

```
prefect agent docker start -l youragentname -l docker
```

Change your run config to: `run_config=DockerRun(labels=[youragentname, "docker"])`

Then, provide Docker storage for your flow. Here, all I am specifying is the additional python packages (apart from the default ones installed with Prefect and python) to install. 

```
flow.storage = Docker(python_dependencies=["pandas"])
```

This will then create a docker image local to your machine that your agent will then use before running your flow.

If you'd like to run this flow on one of our machines like `atd-data03`, then you will have to push your docker image to dockerhub or something similar so `atd-data03` can pull the latest image.

```
flow.storage = Docker(
    registry_url="atddocker", # Our dockerhub account, need your computer to be authenticated
    image_name="prefect-tutorial",
    image_tag="prod",
    python_dependencies=["pandas"],
)

```

If you already have a Dockerfile, you can provide that as can argument `dockerfile = "path/to/Dockerfile"`

Testing and running or scheduling this flow is identical to the above step.
