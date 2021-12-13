# Logging

Prefect has its own logging framework and is
not affected by python loggers globally:

>Prefect's log levels are governed by prefect.config.logging.level, which defaults to INFO. However, this setting only affects "Prefect" loggers, not Python loggers globally.

To change it, they suggest changing the environment variable:

```bash
$ PREFECT__LOGGING__LEVEL=DEBUG python flows/test/template.py
```

If you need the variable to persist even after
the execution of the python command, you may
want to export the variable.

```bash
$ export PREFECT__LOGGING__LEVEL=INFO 
$ python flows/test/template.py
$ export PREFECT__LOGGING__LEVEL=DEBUG
```

Basically we persist the variable value using export,
then we run the python command, then we unset the
variable if you want to test the scheduling.

> Pro-Tip: Some IDEs provide a way to make this
> environment variable by default on every run
> that way you don't have to worry about 
> exporting variables or trying to remember
> what variables are even needed.

## Access the logging class

To log from a task generated with a `@task` decorator,
access the logger from context while your task is running:

```python
import prefect

@task
def my_task():
    logger = prefect.context.get("logger")

    logger.info("An info message.")
    logger.warning("A warning message.")
```

THIS WILL NOT WORK:

```python
logger = prefect.context.get("logger")

@task
def my_task():

    logger.info("An info message.")
    logger.warning("A warning message.")
```

THIS WILL NOT WORK EITHER:

```python
from prefect import context

@task
def my_task():
    logger = context.get("logger") # will not work
    logger.info("An info message.")
    logger.warning("A warning message.")
```

## Logging to STDOUT

Prefect tasks natively support forwarding the output of
stdout to a logger. This can be enabled by setting
`log_stdout=True` on your task.

```python
@task(log_stdout=True)
def log_my_stdout():
    print("I will be logged!")
```

## 3rd Party Loggers

Other frameworks and libraries may have their own
logging methods, if that is so you may want to
continue reading the documentation on Prefect:

https://docs.prefect.io/core/concepts/logging.html#extra-loggers

## Sources

Logging:
- https://docs.prefect.io/core/concepts/logging.html
- https://docs.prefect.io/core/concepts/logging.html#extra-loggers
