#!/usr/bin/env python

"""
Name: Test Flow
Description: This is a test flow that demonstrates how to run multiple tasks.
Schedule: None
Labels: test
"""

import prefect
from prefect import Flow, task
from prefect.run_configs import LocalRun


@task(name="First")
def first():
    logger = prefect.context.get("logger")
    logger.info("One!")


@task(name="Second")
def second():
    logger = prefect.context.get("logger")
    logger.info("Two!")


@task(name="Third")
def third():
    logger = prefect.context.get("logger")
    logger.info("Three!")


# Next, we define the flow (equivalent to a DAG).
# Notice we use the label "test" to match this flow to an agent.
with Flow(
    "hello-test",
    run_config=LocalRun(labels=["test"])
) as flow:
    flow.add_edge(first, second)
    flow.add_edge(second, third)

# Run only if this is the main file
if __name__ == "__main__":
    flow.run()
