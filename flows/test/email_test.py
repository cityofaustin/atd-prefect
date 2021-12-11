#!/usr/bin/env python

"""
Name: Send an email
Description: A test on how to send an email
Schedule: None
Labels: test
"""

from prefect import Flow
from prefect.backend import get_key_value
from prefect.run_configs import UniversalRun

# E-Mail
from prefect.tasks.notifications.email_task import EmailTask

# Retrieve the email configuration
email_config = get_key_value(key="email_config")

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
    "email-test",
    run_config=UniversalRun(labels=["test"])
) as flow:
    # Chain the two tasks
    flow.add_task(email_task)

if __name__ == "__main__":
    flow.run()
