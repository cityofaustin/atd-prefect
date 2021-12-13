# Notifications and Error Handling

## Notifications and State Handlers
In prefect, notifications are written using state
handlers. These are functions which retrieve the object,
old state and new state of execution.

>Alerts, notifications, and dynamically responding to task state are
> important features of any workflow tool. Using Prefect primitives,
> users can create Tasks that send notifications after certain tasks
> run or fail using Prefect's trigger logic. This will work, but
> does not cover more subtle uses of notification logic (e.g.,
> receiving a notification if a task retries). For this reason,
> Prefect introduces a flexible concept called "state handlers",
> which can be attached to individual tasks or flows. At a high
> level, a state handler is a function that is called on every change
> of state for the underlying object; these can be used for sending
> alerts upon failure, emails upon success, or more nuanced handling
> based on the information contained in both the old and new states.

>In addition to working with the state_handler API directly, Prefect
> provides higher level wrappers for implementing common use cases
> such as failure callbacks.

A basic state handler looks like this:

```python
def state_handler(obj: Union[Task, Flow], old_state: State, new_state: State) -> Optional[State]:
    """
    Any function with this signature can serve as a state handler.

    Args:
        - obj (Union[Task, Flow]): the underlying object to which this state handler
            is attached
        - old_state (State): the previous state of this object
        - new_state (State): the proposed new state of this object

    Returns:
        - Optional[State]: the new state of this object (typically this is just `new_state`)
    """
    pass
```

The concept of states is covered in more depth in [this page](https://docs.prefect.io/core/concepts/states.html),
but as a summary, they describe that it is often desirable
to take action when a certain event happens, for example
when a task fails. Prefect provides state_handlers for this
purpose. Flows and Tasks may have one or more state handler
functions that are called whenever the task's state changes.

An example looks like this:

```python
from prefect.engine import state

def notify_on_retry(task, old_state, new_state):
    if isinstance(new_state, state.Retrying):
        send_notification() # function that sends a notification
    return new_state

task_that_notifies = Task(state_handlers=[notify_on_retry])
```

>Whenever the task's state changes, the handler will be called
> with the task itself, the old (previous) state, and the new
> (current) state. The handler must return a State object,
> which is used as the task's new state. This provides an
> opportunity to either react to certain states or even modify
> them. If multiple handlers are provided, then they are called
> in sequence with the state returned by one becoming the
> new_state value of the next.

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
States:
	https://docs.prefect.io/core/concepts/states.html
Notification Tasks
	https://docs.prefect.io/core/concepts/notifications.html#sending-a-simple-notification
	https://docs.prefect.io/api/latest/tasks/notifications.html#notification-tasks
SlackTask:
	https://docs.prefect.io/api/latest/tasks/notifications.html#slacktask
EmailTask:
	https://docs.prefect.io/api/latest/tasks/notifications.html#emailtask
