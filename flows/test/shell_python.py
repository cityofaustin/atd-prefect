#!/usr/bin/env python

"""
Name: Shell and python tests
Description: This is a test on how to run shell and python commands
Schedule: None
Labels: test
"""

import os
from prefect import Flow
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun

# Shell
from prefect.tasks.shell import ShellTask

# First, we must always define the current environment, and default to staging:
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

environment_variables = {
    "MESSAGE": "HELLO WORLD"
}

shell_task = ShellTask(
    name="shell_task",
    command='echo "MESSAGE: ${MESSAGE}"',
    env=environment_variables,
    stream_output=True
)

python_task = ShellTask(
    name="python_task",
    command='python3 ./flows/test/scripts/example.py',
    env=environment_variables,
    stream_output=True
)


# Create the flow
with Flow(
    "shell-python-test",
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/test/shell_python.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    run_config=UniversalRun(labels=[current_environment, "atd-prefect-01"])
) as flow:
    # Chain the two tasks
    flow.chain(shell_task, python_task)

if __name__ == "__main__":
    flow.run()
