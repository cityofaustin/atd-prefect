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

Done.

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
$ python flow/test/test/py
```

#### Environments

For now, the main branch is both staging and production.

## Task Register

After you are  happy with your prefect flow,
you have the option to register the flow directly
from your machine, or you should let github
actions do that for you.

To let GH actions register the file just merge
your file into the github action and merge to main.

Alternatively, you may run the register command:

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