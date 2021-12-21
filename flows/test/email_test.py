#!/usr/bin/env python

"""
Name: Send an email
Description: A test on how to send an email
Schedule: None
Labels: test
"""

import os
from prefect import Flow
from prefect.storage import GitHub
from prefect.backend import get_key_value
from prefect.run_configs import UniversalRun

# E-Mail
from prefect.tasks.notifications.email_task import EmailTask

# First, we must always define the current environment, and default to staging:
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

# Retrieve the email configuration
email_config = get_key_value(key="aws_email_config")

"""
Task for sending email from an authenticated email service over SMTP.
For this task to function properly you must have the "EMAIL_USERNAME" and "EMAIL_PASSWORD" set in Prefect.
"""
email_task = EmailTask(
    name="email_task",
    subject="Test from ATD",
    msg="Hello this is a test from atd!",
    email_to=email_config["test_email"],  # <- Type your email here
    email_from=email_config["email_from"],
    smtp_server=email_config["smtp_server"],
    smtp_port=email_config["smtp_port"],
    smtp_type=email_config["smtp_type"],
    attachments=None
)


# Create the flow
with Flow(
    f"email-test_{current_environment}",
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/test/email_test.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    run_config=UniversalRun(labels=[current_environment, "atd-prefect-01"])
) as flow:
    # Chain the two tasks
    flow.add_task(email_task)

if __name__ == "__main__":
    flow.run()
