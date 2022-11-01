from prefect import task, Flow
from prefect.run_configs import LocalRun

# Start your local agent with:
# prefect agent local start -l youragentname -l local

youragentname = "charliesmacbook"


@task
def add_one(val):
    return val + 1


@task(log_stdout=True)
def print_res(val):
    print(f"Our result is: {val}")


with Flow(
    "3-prefect_basic_agent", run_config=LocalRun(labels=[youragentname, "local"])
) as flow:
    val = add_one(1)
    print_res(val)

# flow.run()
flow.register("test")
# Can also be completed in command line with:
# prefect register --project test -p 3-prefect_basic_agent.py -f

# Follow the URL in the console or go to cloud.prefect.io
# To find and run your flow manually
