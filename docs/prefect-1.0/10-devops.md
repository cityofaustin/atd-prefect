# DevOps

The workflow of this repository is not set in
stone, it is mostly an experiment, and it is
bound to be revised and to change a lot.

### Creating a new flow

Before you create a new flow, be sure you have
identified to what project this flow belongs.
This is necessary because in order to register
a flow, it must belong to a project. If this is
an existing project, simply find the folder in
the flows directory and create a new file there.
If this is a brand new project, be sure to
first create the project in Prefect, then create
a folder in the flows directory.


There are a few examples that demonstrate how
different features work in Prefect within this
repository. For example, one will demonstrate
how to send an email, another how to run a
python script, another how to run a docker
container, etc.

You are welcome to implement the flow from
the ground up, or you can copy from any of the
test files or any of the existing flows.

Be sure whenever you declare the flow, to
provide the correct path value in the GitHub
storage class constructor:

```python
with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"template_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/YOUR PROJECT/YOUR FILE.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(
        labels=[current_environment, "atd-data02"]
    ),
    # Schedule:
    #   When developing or troubleshooting a flow with a schedule
    #   you may want to disable it by exporting the global variable before execution:
    #       $ PREFECT__FLOWS__RUN_ON_SCHEDULE=false python flows/test/template.py
    #   Alternatively, you can do something like this:
    #       flow.run(run_on_schedule=False)
    schedule=Schedule(clocks=[CronClock("*/5 * * * *")])
```

Also check your cron expression to match the
timing you want the flow to run with. After this
you can start creating tasks.

### How to develop and test a flow

To test your flow, simply run within python
in your local environment:

```shell
$ python flow/your_project/your_file.py
```

You may want to specify `flow.run(run_on_schedule=False)`
so that you don't have to wait if you are using
a CRON calendar.

### How to create a branch and PR for review

Once fully tested locally, create a branch,
commit your changes to that branch and then
create a PR. It should be deployed under staging.

### Reviewing a PR/branch locally

Simply check out the branch and run locally.

```shell
$ python flow/your_project/your_file.py
```

You may want to specify `flow.run(run_on_schedule=False)`
so that you don't have to wait if you are using
a CRON calendar.

### How are staging and production separated?

The branches are separated in the servers running
agents. The agents run in separate folders in
the file system, both updating/cloning from github every
5 minutes. One folder is for production, the other
for staging. One agent will run within the
production github folder, and the other in staging's. 

Another factor separating the two is by running
the agents with the specific use of labels,
namely the the `production` label and/or the `staging`
label.

### How agents are run (ctm, aws, etc)

The same two-directory pattern is followed in the cloud (AWS).
and it even uses the same label strategy; however,
aws will have another set of labels: `atd-prefect-01`
while ctm will have some something like `atd-data02`.

### How to target specific servers

To target a specific server, make use of the server
label (`atd-prefect-01`, or `atd-data02`, etc.) within the
Flow declaration:

```python
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
```

Notice the `run_config` argumenrt passing the atd-prefect-01 label to run
the flow in the AWS instance.