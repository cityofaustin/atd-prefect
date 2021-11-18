#!/usr/bin/env python

import prefect
from prefect import Flow, task
from prefect.run_configs import LocalRun
from prefect.engine.state import Failed

@task(name="First")
def hello_task():
    logger = prefect.context.get("logger")
    logger.info("One!")

@task(name="Second")
def hello_task_two():
    logger = prefect.context.get("logger")
    logger.info("Two!")

@task(name="Third")
def hello_task_three():
    logger = prefect.context.get("logger")
    logger.info("Three!")


flow = Flow(
        "hello-test",
        run_config=LocalRun(labels=["test"])
) as flow:
    hello_task_two.set_upstream(hello_task)
    hello_task_three.set_upstream(hello_task_two)




flow.visualize()