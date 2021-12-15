# Flow Control

To control the flow or design and manipulate
the ETL graph there are several methods included
in Prefect, including these:

```python
    a = Task()
    b = Task()
    c = Task()
    
    # Using flow.chain
    flow.chain(a,b,c)
    
    # Using flow.add_edge,
    flow.add_edge(a, b)
    flow.add_edge(b, c)
    
    # Using flow.add_task (does not chain tasks but executes in order)
    flow.add_task(a)
    flow.add_task(b)
    flow.add_task(c)
    
    # Via task.set_upstream
    b.set_upstream(a)
    c.set_upstream(b)
    
    # Via task.set_downstream
    a.set_downstream(b)
    b.set_downstream(c)

    # Via task.set_dependencies
    b.set_dependencies(upstream_tasks=[a], downstream_tasks=[c], flow=flow)
    
    # Via Merge (merges all tasks into a single task run in order)
    merge([hello_task, hello_task_two, hello_task_three], flow=flow)

    
```

There is no strong preference, most of our ETL or DAGs
currently in Airflow do not have a complex graph.

## Tasks

>A Task represents a discrete action in a Prefect workflow. 
A task is like a function: it optionally takes inputs,
performs an action, and produces an optional result.
In fact, the easiest way to create a task is by decorating
a Python function:

```python
from prefect import task

@task
def plus_one(x):
    return x + 1
```

The task decorator (and class) has the following parameters:

```python
Task(
    name=None,
    slug=None,
    tags=None,
    max_retries=None,
    retry_delay=None,
    timeout=None,
    state_handlers=None,
    on_failure=None,
    log_stdout=False,
    trigger=None,
    skip_on_upstream_skip=True,
    cache_for=None,
    cache_validator=None,
    cache_key=None,
    checkpoint=None,
    result=None,
    target=None,
    task_run_name=None,
    nout=None
)
```


For in-depth customization, it is possible to
extend the Task class like this:

```python
from prefect import Task

class HTTPGetTask(Task):

    def __init__(self, username, password, **kwargs):
        self.username = username
        self.password = password
        super().__init__(**kwargs)

    def run(self, url):
        return requests.get(url, auth=(self.username, self.password))
```

Another example of task extension (notice the class
must have a run method):

```python
class AddTask(Task):
    def run(self, x, y):
        return x + y

a = AddTask()

with Flow("My Flow") as f:
    t1 = a(1, 2) # t1 != a
    t2 = a(5, 7) # t2 != a
```

## Conditional Tasks

https://docs.prefect.io/core/examples/conditional.html

## Sources

Flow:
- https://docs.prefect.io/api/latest/core/flow.html

Flow Control:
- https://docs.prefect.io/api/latest/tasks/control_flow.html

Task:
- https://docs.prefect.io/api/latest/core/task.html
- https://docs.prefect.io/core/concepts/tasks.html#overview