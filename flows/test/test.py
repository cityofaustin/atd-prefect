#!/usr/bin/env python

"""
Name: Test Flow
Description: This is a test flow that demonstrates how to run multiple tasks.
Schedule: None
Labels: test
"""

import os
import prefect
from prefect import Flow, task
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun

# First, we must always define the current environment, and default to staging:
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")


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
    f"test_{current_environment}",
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/test/test.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    run_config=UniversalRun(labels=[current_environment, "atd-prefect-01"])
) as flow:
    flow.add_edge(first, second)
    flow.add_edge(second, third)

# Run only if this is the main file
if __name__ == "__main__":
    flow.run()
