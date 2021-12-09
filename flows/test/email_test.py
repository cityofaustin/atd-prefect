#!/usr/bin/env python

"""
Name: Send an email
Description: A test on how to send an email
Schedule: None
Labels: test
"""

from prefect import Flow, config
from prefect.run_configs import LocalRun

# E-Mail
from prefect.tasks.notifications.email_task import EmailTask



"""
Task for sending email from an authenticated email service over SMTP.
For this task to function properly you must have the "EMAIL_USERNAME" and "EMAIL_PASSWORD" set in Prefect.
"""
email_task = EmailTask(
    name="email_task",
    subject="Test from ATD",
    msg="Hello this is a test from atd!",
    email_to=None,  # <- Type your email here!
    email_from=config.email.email_from,
    smtp_server=config.email.smtp_server,
    smtp_port=config.email.smtp_port,
    smtp_type=config.email.smtp_type,
    attachments=None
)


# Create the flow
with Flow(
    "email-test",
    run_config=LocalRun(labels=["test"])
) as flow:
    # Chain the two tasks
    flow.add_task(email_task)

if __name__ == "__main__":
    flow.run()
