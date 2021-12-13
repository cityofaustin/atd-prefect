# Agents

At the time of the writing of this documentation, we have
only explored [LocalRun](https://docs.prefect.io/orchestration/flow_config/run_configs.html#localrun)
and [DockerRun](https://docs.prefect.io/orchestration/flow_config/run_configs.html#dockerrun)
deployments. They are both good approaches.

###LocalRun

The local agent answers for virtually all our needs
we currently have with Airflow. It allows us to run
processes locally, as well as running dockerized
containers without too much network/volume configuration.

From [Prefect's documentation](https://docs.prefect.io/orchestration/agents/local.html)
we read:

>The local agent starts flow runs as processes
> local to the same machine it is running on.
> It's useful for running lightweight workflows
> on standalone machines, testing flows locally,
> or quickly getting acclimated with the Prefect
> API. While the local agent is fully capable of
> executing flows in conjunction with the Prefect
> API, we generally recommend using one of the
> other agents to help with modularity and scale.

When it comes to modularity and scale, it absolutely
makes more sense to use something like Docker or
Kubernetes. What this means for our team is that
we need to limit the number of scripts we write
in Python alone and that we need to dockerize everything.

Since this is already the case, we don't have to
worry too much about modularity and scale. Our
dockerized processes we will be porting from
Airflow will be nearly identical within Prefect.

```bash
$ prefect agent local start -h

Usage: prefect agent local start [OPTIONS]

  Start a local agent

Options:
  -k, --key TEXT                  A Prefect Cloud API key. If not set, the
                                  value will be inferred from the local
                                  machine.
  --tenant-id TEXT                The ID of the tenant to connect the agent
                                  to. If not set, the value will be inferred
                                  from the local machine and fallback to the
                                  default associated with the API key.
  -a, --api TEXT                  A Prefect API URL. If not set, the value in
                                  the config is used.
  --agent-config-id TEXT          An agent ID to link this agent instance with
  -n, --name TEXT                 A name to use for the agent
  -l, --label TEXT                Labels the agent will use to query for flow
                                  runs.
  -e, --env TEXT                  Environment variables to set on each
                                  submitted flow run.
  --max-polls INTEGER             Maximum number of times the agent should
                                  poll the Prefect API for flow runs. Default
                                  is no limit
  --agent-address TEXT            Address to serve internal api server at.
                                  Defaults to no server.
  --no-cloud-logs                 Turn off logging for all flows run through
                                  this agent. If not set, the Prefect config
                                  value will be used.
  --log-level [DEBUG|INFO|WARNING|ERROR]
                                  The agent log level to use. Defaults to the
                                  value configured in your environment.
  -t, --token TEXT                A Prefect Cloud API token with RUNNER scope.
                                  DEPRECATED.
  -p, --import-path TEXT          Import paths the local agent will add to all
                                  flow runs.
  -f, --show-flow-logs            Display logging output from flows run by the
                                  agent.
  --hostname-label / --no-hostname-label
                                  Add hostname to the LocalAgent's labels
  -h, --help                      Show this message and exit.
```

###DockerRun

The docker agent behaves a lot like the Local agent. Basically,
the only difference is that the flows are executed
within a container. From prefect we read:

>The Docker agent executes flow runs in individual
> Docker containers. This provides more isolation and
> control than the Local Agent, while still working
> well on a single machine.

Running our processes with the docker agent is in fact
good for isolation, but it presents some challenges with
some of our non-dockerized python code, as well as 
processes that already run in docker.

To avoid excessive configuration challenges, we will not be using
this method for now. The gains do not justify the
effort it takes to run docker tasks within a dockerized
Flow.

```bash
$ prefect agent docker start -h
Usage: prefect agent docker start [OPTIONS]

  Start a docker agent

Options:
  -k, --key TEXT                  A Prefect Cloud API key. If not set, the
                                  value will be inferred from the local
                                  machine.
  --tenant-id TEXT                The ID of the tenant to connect the agent
                                  to. If not set, the value will be inferred
                                  from the local machine and fallback to the
                                  default associated with the API key.
  -a, --api TEXT                  A Prefect API URL. If not set, the value in
                                  the config is used.
  --agent-config-id TEXT          An agent ID to link this agent instance with
  -n, --name TEXT                 A name to use for the agent
  -l, --label TEXT                Labels the agent will use to query for flow
                                  runs.
  -e, --env TEXT                  Environment variables to set on each
                                  submitted flow run.
  --max-polls INTEGER             Maximum number of times the agent should
                                  poll the Prefect API for flow runs. Default
                                  is no limit
  --agent-address TEXT            Address to serve internal api server at.
                                  Defaults to no server.
  --no-cloud-logs                 Turn off logging for all flows run through
                                  this agent. If not set, the Prefect config
                                  value will be used.
  --log-level [DEBUG|INFO|WARNING|ERROR]
                                  The agent log level to use. Defaults to the
                                  value configured in your environment.
  -t, --token TEXT                A Prefect Cloud API token with RUNNER scope.
                                  DEPRECATED.
  -b, --base-url TEXT             Docker daemon base URL.
  --no-pull                       Disable pulling images in the agent
  -f, --show-flow-logs            Display logging output from flows run by the
                                  agent.
  --volume TEXT                   Host paths for Docker bind mount volumes
                                  attached to each Flow container. Can be
                                  provided multiple times to pass multiple
                                  volumes (e.g. `--volume /volume1 --volume
                                  /volume2`)
  --network TEXT                  Add containers to existing Docker networks.
                                  Can be provided multiple times to pass
                                  multiple networks (e.g. `--network network1
                                  --network network2`)
  --no-docker-interface           Disable the check of a Docker interface on
                                  this machine. Note: This is mostly relevant
                                  for some Docker-in-Docker setups that users
                                  may be running their agent with. DEPRECATED.
  --docker-client-timeout INTEGER
                                  The timeout to use for docker API calls,
                                  defaults to 60 seconds.
  -h, --help                      Show this message and exit.
```

## Sources:

Orchestration:
- https://docs.prefect.io/orchestration/agents/overview.html