# Agents

Not yet written.


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