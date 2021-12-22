# Prefect Basics

This is a compendium of Prefect's documentation. The intention is to help
anyone familiar with Python to write automated tasks on our platform. 
After finishing this documentation, you really should read Prefect's.

## Configuration

The first thing you will need is a configuration file that
contains some secrets. It's a toml configuration file that
is currently stored in 1Password.

1. Search for it in 1Password under "Prefect Configuration"
2. Copy contents to clipboard
3. Save it in this exact location in your machine:
```~/.prefect/config.toml```

The next thing you will need is a prefect api key. To
get one you can visit this link, and click "+ Create API Key":

https://cloud.prefect.io/user/keys

Whenever you have a key, you will need to export it like so:

```shell
$ export PREFECT__CLOUD__API_KEY="<YOUR-KEY>"
```

If you will be using agents, you may want to run this command:

```shell
$ prefect auth login --key <YOUR-KEY>
```

For more info on keys, visit [this page](https://docs.prefect.io/orchestration/concepts/api_keys.html#using-api-keys).

## Environment

Make sure you have prefect installed:

```bash
# 1. Create a virtual environment
$ virtualenv venv

# 2. Source the virtual environment
$ source venv/bin/activate

# 3. Install the requirements for local development
$ pip install -r requirements.txt
```

## Repo File Structure

The repository contains the following file structure:

```
docs: (documentation)
flows/
└── test (example flows)
    └── scripts
        └── example.py
    └── test.py
    └── template.py
    ...
```

- `flows`: Contains all the projects
- `test`: "test" is the name of the project in Prefect
- `test.py`: The flow to be deployed (registered) in Prefect
- `scripts`: Any helper scripts for this flow.

## Development

The development and testing happens entirely in the
local environment (in your computer). 

#### Syntax

This is the basic syntax for a flow:

```python
# 1. Make your includes
import prefect
from prefect import Flow, task
from prefect.run_configs import LocalRun

# 2. Create your tasks
@task(name="my_task")
def my_task():
    logger = prefect.context.get("logger")
    logger.info("my_task!")
    
# 4. Create the flow
with Flow(
    "my_flow",
    run_config=LocalRun(labels=["test"])
) as flow:
    flow.add_task(my_task)
    

# GitHub Actions is programmed to look for this line.
# If it is missing, it will not deploy it to Prefect:
if __name__ == "__main__":
    flow.run()
```

You don't have to run the above file right now, it is
only meant to show and explain the basic syntax.

#### Running a flow (locally)

The next step is to actually run the flow. For this,
we are going to use an existing flow:

```bash
$ python flow/test/test.py
```

## Environments

The main branch contains the staging environment,
while production contains all work in production.

A single machine (either on AWS or CTM) will likely
be running two agents, one for staging and another
for production, each with labels that signal what
processes they will be running.

For more information on this, read page no. 5 of
this documentation to learn how the agents are run.

## Flow Register

After you are happy with your prefect flow,
you have the option to register the flow directly
from your machine, or you can let the GitHub Actions
do it for you.

What happens when you register a flow? From Prefect, we can read:

> When you register a Flow, your code is securely stored on your infrastructure — your code never leaves your execution environment and is never sent to Prefect Cloud. Instead, Flow metadata is sent to Prefect Cloud for scheduling and orchestration.

To let GH actions register the file just merge
your file into the github main branch. For specific
details about how to work the branches and PRs world
go to the DevOps section of this documentation.

To register the flow yourself, there is the `prefect register` command:

```bash
$ prefect register -h
Usage: prefect register [OPTIONS] COMMAND [ARGS]...

  Register one or more flows into a project.

  Flows with unchanged metadata will be skipped as registering again will only
  change the version number.

Options:
  --project TEXT              The name of the Prefect project to register this
                              flow in. Required.
  -p, --path TEXT             A path to a file or a directory containing the
                              flow(s) to register. May be passed multiple
                              times to specify multiple paths.
  -m, --module TEXT           A python module name containing the flow(s) to
                              register. May be the full import path to a flow.
                              May be passed multiple times to specify multiple
                              modules.
  -j, --json TEXT             A path or URL to a JSON file created by `prefect
                              build` containing the flow(s) to register. May
                              be passed multiple times to specify multiple
                              paths. Note that this path may be a remote url
                              (e.g. https://some-url/flows.json).
  -n, --name TEXT             The name of a flow to register from the
                              specified paths/modules. If provided, only flows
                              with a matching name will be registered. May be
                              passed multiple times to specify multiple flows.
                              If not provided, all flows found on all
                              paths/modules will be registered.
  -l, --label TEXT            A label to add on all registered flow(s). May be
                              passed multiple times to specify multiple
                              labels.
  -f, --force                 Force flow registration, even if the flow's
                              metadata is unchanged.
  --watch                     If set, the specified paths and modules will be
                              monitored and registration re-run upon changes.
  --schedule / --no-schedule  Toggles the flow schedule upon registering. By
                              default, the flow's schedule will be activated
                              and future runs will be created. If disabled,
                              the schedule will still be attached to the flow
                              but no runs will be created until it is
                              activated.
  -h, --help                  Show this message and exit.

 Examples:

   Register all flows found in a directory.

     $ prefect register --project my-project -p myflows/

   Register a flow named "example" found in `flow.py`.

     $ prefect register --project my-project -p flow.py -n "example"

   Register all flows found in a module named `myproject.flows`.

     $ prefect register --project my-project -m "myproject.flows"

   Register a flow in variable `flow_x` in a module `myproject.flows`.

     $ prefect register --project my-project -m "myproject.flows.flow_x"

   Register all pre-built flows from a remote JSON file.

     $ prefect register --project my-project --json https://some-
  url/flows.json

   Register all flows in python files found recursively using globbing

     $ prefect register --project my-project --path "**/*"

   Watch a directory of flows for changes, and re-register flows upon
  change.

     $ prefect register --project my-project -p myflows/ --watch

   Register a flow found in `flow.py` and disable its schedule.

     $ prefect register --project my-project -p flow.py --no-schedule

```

## Prefect's architecture overview

>Prefect's unique hybrid execution model keeps your code and data completely private while taking full advantage of our managed orchestration service.

![](https://docs.prefect.io/prefect_architecture_overview.png)

## Storage

The documentation is not very clear as to what exactly
the registration does other than to generate metadata about
the flow. However, it is clear that it doesn't store
the python code into their cloud.

For Prefect Cloud to run code it uses the Storage class:

>The Prefect Storage interface encapsulates logic for storing flows. Each storage unit is able to store multiple flows (with the constraint of name uniqueness within a given unit).

The storage class needs to be defined for the flow,
this tells the running agent where the code to the
flow can be found:

```python
from prefect.storage import Local

# Run only if this is the main file
if __name__ == "__main__":
    flow.storage = Local(directory=".")
    flow.run()
```

With the code above, the flow can be executed
with python locally, or with an agent running
in this repo's root directory (wherever it is
located in the agent's file system).

There are other storage classes, including GitHub
repository and AWS S3.

The two require more configuration, but essentially
it looks like this for GitHub:

```python
from prefect.storage import GitHub

# Run only if this is the main file
if __name__ == "__main__":
    flow.storage = GitHub(repo="coa/repo_name", path="/flows/test/flow.py")
    flow.run()
```

#### Why do we use GitHub storage?

It may seem counterproductive to use the GitHub
storage class, but it turns out to be effective.

For one, it enables us to specify in what repository
the code lives, and also the branch. This is helpful
because it downloads the file from the repo/branch
before execution. While downloading the file is
not necessary for us, it makes it very helful when
running in remote/cloud environments.

For us to use the class, we simply declare the
`storage=` argument in the Flow class constructor:

```python
with Flow(
    f"slack-test_{current_environment}",
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/test/slack.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    run_config=UniversalRun(labels=[current_environment, "atd-prefect-01"])
```

In the GitHub class constructor, the repo argument
will likely never change, as it will almost always be
the same. Ref will always be production, or main, so
this one too will never change. However, `path` must
always have the name of this file. At some point
I attempted to automate each of those values, but
I always ended up having problems when registering 
the flows I ended up keeping them like that.

#### Why doesn't Local storage work?

When registering a flow, the register command captures
the context of the file, including where in the
file system it lives. This is presents a problem
when you need to distribute flows to cloud servers
that have little configuration or where the file system
looks very different from local.

Unfortunately, using the local storage class is a 
bit cumbersome and difficult to work with. One
attempt I made to make it work was to develop
a docker container that makes the deployment
of flows more uniform. While this worked whenever
a flow was being registered, it didn't work
when the flows were executed because the running
agents were having trouble finding the files
in the local file system.

It may still be possible to make local work,
but that will have to wait for more testing.


## Sources
Flow:
- https://docs.prefect.io/core/getting_started/basic-core-flow.html
- https://docs.prefect.io/core/concepts/flows.html#overview

Tasks:
- https://docs.prefect.io/core/concepts/tasks.html#overview

Storage:
- https://docs.prefect.io/api/latest/storage.html