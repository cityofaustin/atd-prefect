# Error Handling

We observed in the previous section that prefect
has its own mechanism for handling exceptions. This
is part of how it detects the state of a task and
based on the state (success, failure, etc.) it
makes a decision on what happens next, to either
stop the execution, run a notification, execute
a different task, etc.

While in the previous section we learned how to 
turn that off, we need to learn how to use the
error-handling methods within Prefect.

Example Code:

https://github.com/PrefectHQ/prefect/blob/master/examples/tutorial/04_handle_failures.py

## Error Handling at the Task level

### Max-Retry, Retry-Delay

Tasks provide a couple ways to deal with errors,
the first one is via `max_retries`, and the `retry_delay`
parameters:

```python
@task(max_retries=3, retry_delay=timedelta(seconds=10))
def extract_reference_data():
    # same as before ...
```

### Triggers

There are ways to manipulate what specific tasks
get executed if one fails or provides a specific
status we are looking for.

For example:

```python
import random

from prefect.triggers import all_successful, all_failed
from prefect import task, Flow


@task(name="Task A")
def task_a():
    if random.random() > 0.5:
        raise ValueError("Non-deterministic error has occured.")

@task(name="Task B", trigger=all_successful)
def task_b():
    # do something interesting
    pass

@task(name="Task C", trigger=all_failed)
def task_c():
    # do something interesting
    pass


with Flow("Trigger example") as flow:
    success = task_b(upstream_tasks=[task_a])
    fail = task_c(upstream_tasks=[task_a])

## note that as written, this flow will fail regardless of the path taken
## because *at least one* terminal task will fail;
## to fix this, we want to set Task B as the "reference task" for the Flow
## so that it's state uniquely determines the overall Flow state
flow.set_reference_tasks([success])

flow.run()
```

More information can be [found here](https://docs.prefect.io/core/concepts/execution.html#triggers).


## Sources

Handling Failure:
- https://docs.prefect.io/core/tutorial/04-handling-failure.html

Execution:
- https://docs.prefect.io/core/concepts/execution.html#triggers