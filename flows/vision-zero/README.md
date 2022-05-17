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
```

## Environment Configuration

Environment variables are defined via an environemnt file that is passed to docker when the container is started and which is specificed in the `docker-compose.yml` file. Ultimately, these need to be refactored into a single JSON blob and defined for each deployment phase in the application life cycle (dev, staging, production). This work should be done in conjunction with deploying this code once the group is in agreement over the methods used in this flow/agent setup.

## Non-checked-in files

### Environment variable file, discussed above

* `atd-prefect/flows/vision-zero/prefect_agent_environment_variables.env`

### Public / private key defining SSH identity and client configuration used to auth to SFTP endpoint
* `atd-prefect/flows/vision-zero/prefect_bootstrap/id_rsa`
* `atd-prefect/flows/vision-zero/prefect_bootstrap/id_rsa.pub`
* `atd-prefect/flows/vision-zero/prefect_bootstrap/ssh_config`
