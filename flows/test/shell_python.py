#!/usr/bin/env python

"""
Name: Shell and python tests
Description: This is a test on how to run shell and python commands
Schedule: None
Labels: test
"""
from prefect import Flow
from prefect.storage import Local
from prefect.run_configs import UniversalRun

# Shell
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

python_task = ShellTask(
    name="python_task",
    command='python3 ./flows/test/scripts/example.py',
    env=environment_variables,
    stream_output=True
)


# Create the flow
with Flow(
    "shell-python-test",
    run_config=UniversalRun(labels=["test"])
) as flow:
    # Chain the two tasks
    flow.chain(shell_task, python_task)

if __name__ == "__main__":
    flow.storage = Local(directory=".")
    flow.run()
