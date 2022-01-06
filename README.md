# Prefect

Initial documentation of our new ETL process. 

## Development

The code in this repo will run in many machines, in order to avoid
conflicts it will be ideal to have some loosely held expecations
in terms of runtime environment and dependencies: 

- Python 3.8.X 
- Pip 21.1.X
- VirtualEnv

Pyenv is recommended to work with multiple versions
of python in your system.

## Getting started

There are two ways to run an ETL, the first is by running the
python ETL script locally, and the second is by running
prefect cloud agents.

First, we must install our requirements:

```bash
# 1. Create a virtual environment
$ virtualenv venv

# 2. Source the virtual environment
$ source venv/bin/activate

# 3. Install the requirements for local development
$ pip install -r requirements.txt
```

#### Running ETL locally

After you have installed the requirements above,
you may now run it using python:

```bash
# Run the ETL locally
$ python flows/test/test.py
```

#### Using cloud agents

Running ETLs with cloud agents requires you to register
the flow first using labels. Prefect uses labels to match
python scripts to running agents.  The file
`flows/test/test.py` is already labeled and registered
for  your convenience, and all you have to do is continue
with the instructions.

1. To run an agent in your machine, be sure you export
the API key in order to connect the agent to the account
by running.

```bash
$ export PREFECT_KEY="YOUR_PREFECT_API_KEY"
- or -
$ prefect auth login --key "YOUR_PREFECT_API_KEY"
```

You can retrieve your API key by going to the prefect
cloud account, [following this link](https://cloud.prefect.io/user/keys).

2. Once exported the key, you may run this:

```bash
$ prefect agent local start -l test
```

Note: `-l` stands for label, and the example above uses the
`test` label for which the above ETL is registered.

3. Go to [Prefect Cloud](https://cloud.prefect.io), then click
Dashboard > Flows > "hello-test" > Quick Run (at the top right).

It will look something like this:

```
❯ prefect agent local start -l test
[2021-12-06 23:40:47,475] INFO - agent | Registering agent...
[2021-12-06 23:40:47,719] INFO - agent | Registration successful!

 ____            __           _        _                    _
|  _ \ _ __ ___ / _| ___  ___| |_     / \   __ _  ___ _ __ | |_
| |_) | '__/ _ \ |_ / _ \/ __| __|   / _ \ / _` |/ _ \ '_ \| __|
|  __/| | |  __/  _|  __/ (__| |_   / ___ \ (_| |  __/ | | | |_
|_|   |_|  \___|_|  \___|\___|\__| /_/   \_\__, |\___|_| |_|\__|
                                           |___/

[2021-12-06 23:40:47,899] INFO - agent | Starting LocalAgent with labels ['test']
[2021-12-06 23:40:47,900] INFO - agent | Agent documentation can be found at https://docs.prefect.io/orchestration/
[2021-12-06 23:40:47,900] INFO - agent | Waiting for flow runs...
[2021-12-06 23:41:46,365] INFO - agent | Deploying flow run 11111111-1111-1111-1111-111111111111 to execution environment...
[2021-12-06 23:41:46,884] INFO - agent | Completed deployment of flow run 11111111-1111-1111-1111-111111111111
```

Notice the success message "Completed deployment of flow run" which
means the flow has been deployed and run. The output of the ETL has
been sent back to prefect cloud.
