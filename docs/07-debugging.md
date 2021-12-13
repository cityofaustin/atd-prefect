# Local Debugging

Aside from your standard tools such as [PDB](https://docs.python.org/3/library/pdb.html) and
[pytest](https://docs.pytest.org/en/6.2.x/), there are other tools that can help you 
debug your Prefect Flows.

## Direct debug
Prefect will by default trap exceptions and use its
built-in error-handling mechanisms. Sometimes,
we will want to debug the exceptions directly.

This is provided through the `raise_on_exception` context manager:

```python
from prefect import Flow, task
from prefect.utilities.debug import raise_on_exception


@task
def div(x):
    return 1 / x

with Flow("My Flow") as f:
    val = div(0)

with raise_on_exception():
    f.run()

---------------------------------------------------------------------------

ZeroDivisionError                         Traceback (most recent call last)

<ipython-input-1-82c40dd24406> in <module>()
     11
     12 with raise_on_exception():
---> 13     f.run()


... # the full traceback is long

<ipython-input-1-82c40dd24406> in div(x)
      5 @task
      6 def div(x):
----> 7     return 1 / x
      8
      9 with Flow("My Flow") as f:


ZeroDivisionError: division by zero
```

## Disable Schedules

Prefect recommends "stateless execution" of flows
by disabling schedules.

>If your problem is related to retries, or if
> you want to run your flow off-schedule, you
> might first consider rerunning your flow with
> `run_on_schedule=False`. This can be accomplished
> via environment variable `PREFECT__FLOWS__RUN_ON_SCHEDULE=false`
> or keyword `flow.run(run_on_schedule=False)`.
 
### Example using the environment variable

Example 1:

```bash
$ PREFECT__FLOWS__RUN_ON_SCHEDULE=false python flows/test/template.py
```

The above command is simpler because the context of the variable
ends whenever the command is finished.

> Pro-Tip: Some IDEs provide a way to make this
> environment variable by default on every run
> that way you don't have to worry about 
> exporting variables or trying to remember
> what variables are even needed.

Example 2:

If you need the variable to persist even after
the execution of the python command, you may
want to export the variable.

```bash
$ export PREFECT__FLOWS__RUN_ON_SCHEDULE=false 
$ python flows/test/template.py
$ unset PREFECT__FLOWS__RUN_ON_SCHEDULE
```

Basically we persist the variable value using export,
then we run the python command, then we unset the
variable if you want to test the scheduling.

## Post-hoc Exception handling

It is possible to capture the failed state post-hoc by
checking the resulting state and re-raising an exception:

```python
[...]
    flow.run()

failed_state = state.result[gotcha]
raise failed_state.result
```

Example:

```python
rom prefect import Flow, task


@task
def gotcha():
    tup = ('a', ['b'])
    try:
        tup[1] += ['c']
    except TypeError:
        assert len(tup[1]) == 1


flow = Flow(name="tuples", tasks=[gotcha])

state = flow.run()
state.result # {<Task: gotcha>: Failed("Unexpected error: AssertionError()")}

failed_state = state.result[gotcha]
raise failed_state.result

---------------------------------------------------------------------------

TypeError                                 Traceback (most recent call last)

<ipython-input-50-8efcdf8dacda> in gotcha()
      7     try:
----> 8         tup[1] += ['c']
      9     except TypeError:

TypeError: 'tuple' object does not support item assignment

During handling of the above exception, another exception occurred:

AssertionError                            Traceback (most recent call last)
<ipython-input-1-f0f986d2f159> in <module>
     22
     23 failed_state = state.result[gotcha]
---> 24 raise failed_state.result

~/Developer/prefect/src/prefect/engine/runner.py in inner(self, state, *args, **kwargs)
     58
     59         try:
---> 60             new_state = method(self, state, *args, **kwargs)
     61         except ENDRUN as exc:
     62             raise_end_run = True

~/Developer/prefect/src/prefect/engine/task_runner.py in get_task_run_state(self, state, inputs, timeout_handler)
    697             self.logger.info("Running task...")
    698             timeout_handler = timeout_handler or main_thread_timeout
--> 699             result = timeout_handler(self.task.run, timeout=self.task.timeout, **inputs)
    700
    701         # inform user of timeout

~/Developer/prefect/src/prefect/utilities/executors.py in multiprocessing_timeout(fn, timeout, *args, **kwargs)
     68
     69     if timeout is None:
---> 70         return fn(*args, **kwargs)
     71     else:
     72         timeout_length = timeout.total_seconds()

<ipython-input-1-f0f986d2f159> in gotcha()
      9         tup[1] += ['c']
     10     except TypeError:
---> 11         assert len(tup[1]) == 1
     12
     13

AssertionError:

%debug # using the IPython magic method to start a pdb session
```

## Sources

https://docs.prefect.io/core/advanced_tutorials/local-debugging.html

https://docs.prefect.io/api/latest/utilities/debug.html#functions