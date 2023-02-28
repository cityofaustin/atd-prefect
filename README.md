# Prefect
 

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

#### Using Prefect Cloud

After developing and testing your flow, create a deployment file to connect it with our Prefect cloud instance. 

```bash
$ prefect cloud login
```
 
 The command will prompt you to log in via the browser or with an api key. 

 Use the transportation.data email address to log in to the cloud instance, app.prefect.cloud. Our workspace is named `atdprefect`. 

 Connecting the flow you are working on involves creating and applying a deployment configuration. You can create the deployment file from the command line, here is an example with the flags we use.

 ```
 prefect deployment build \
flows/knack/knack_banner.py:knack_hr_banner_flow \
-t production \
--cron "45 13 * * *" \
-q atd-data-03 \
--name "HR Knack Banner" \
-o "deployments/knack_banner.yaml" \
-sb github/atd-prefect-main-branch \
--skip-upload \
```

- After `prefect deployment build` include the following
- path/to/flow.py:functionname 
- -q: work queue name (the agent that runs the flow). required.`atd-data-03` is our main agent that runs on atd-data03 in a conda environment. 
- -t: optional tags you want to add to the flow
- --cron: schedule for the flow to run, optional but if you don't set this
- --name: the deployments name
- -o: where the deployment file will be stored after creation. If this is blank, the file is created in the root directory with an automated name. Use the deployments folder and name your deployment file the same as your flow file
- -sb: storage block. Where Prefect knows to look for your flow's code. The `github/atd-prefect-main-branch` is a block that points to the main branch of this repo. You can create temporary blocks to point to branches, but please delete them when you are done using them.
- --skip-upload: Prefect's default is to upload a flows files to the storage block. Use this flag to skip this step since our workflow is to add to github and PR with approvals before merging. 

The next step after building your deployment specification is to apply it. Once your flow has been approved and merged to main, run this command

```bash
$ prefect deployment apply deployments/knack_banner.yaml
```


