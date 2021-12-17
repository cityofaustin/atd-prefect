#!/usr/bin/env python

"""
Name: Test Slack Notification
Description: This is a test flow that demonstrates how to send a notification.
Schedule: None
Labels: test
"""

import os
from prefect import Flow, task
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun
from prefect.engine.state import Failed
from prefect.utilities.notifications import slack_notifier
from prefect.tasks.notifications.slack_task import SlackTask

from datetime import datetime

# First, we must always define the current environment, and default to staging:
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

# We can call it early
handler = slack_notifier(only_states=[Failed])


@task(name="slack-test-succeed", state_handlers=[handler])
def succeed():
    pass


@task(name="slack-test-fail", state_handlers=[handler])
def fail():
    raise Exception("Fail through a custom exception!")


# Custom Message
custom_slack_message = SlackTask(message="""
{emoji} {message}
*Task*: {task}  
*Flow*: {flow} 
*Execution Time*: {exec_date}  
""".format(
    message="Custom message",
    emoji=":sunny:",
    task="SlackTask",
    flow="test/slack",
    exec_date=datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
))


# Next, we define the flow (equivalent to a DAG).
# Notice we use the label "test" to match this flow to an agent.
with Flow(
    f"slack-test_{current_environment}",
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/test/slack.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    run_config=UniversalRun(labels=[current_environment, "atd-prefect-01"])
) as flow:
    flow.add_edge(succeed, custom_slack_message)
    flow.add_edge(succeed, fail)


if __name__ == "__main__":
    flow.run()
