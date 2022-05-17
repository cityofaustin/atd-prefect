# Vision Zero Agent and Flows

## Description

This directory contains an initial flow which has been created to support the [Vision Zero Crash Data System](https://github.com/cityofaustin/atd-vz-data). The flow's python library requirements are provided by a docker image defined by the `Dockerfile` and orchestrated via `docker-compose`. Development may be conducted while attached to the container running the agent to ease any potential mismatch of python package availability between the flow at registration and the agent at flow invocation.

## Directions

### Agent Startup

The docker-compose system is used to set the configuration settings for the docker service to run the agent image.

```
# this will start the agent in detached mode, building it as needed.
# remove the -d flag to start the agent attached to the terminal.
$ docker-compose up -d 
```

There are a number of volumes which are mounted on the running container, including access to the server's `/tmp` directory, the support files for the agent's execution, the various flows that may be run by the agent and the actual docker socket file. This file provides for "docker inception" where you may have a container containing the docker client software that is able to start a "sibling" container to itself as if it were it's own child container.

NB: The image is configured to `restart: always` which will instruct the docker daemon to restart the container (read: agent) if it ever crashes.


### Development Process

The same docker image is used to develop the flows. Because the image is built to include the libraries that the project's flows may require, there is a intrinisic guarentee that if the flow's package needs are met during development, they will be similarly met during agent execution. This docker contained development execution mechanism also sidesteps the need to define and manage a Flow storage solution allowing the registration process to convey the actual code to be run directly to the agent via the default local storage.

```
# you can connect to the agent / flow development container 
$ docker exec -it prefect-agent-vz bash


