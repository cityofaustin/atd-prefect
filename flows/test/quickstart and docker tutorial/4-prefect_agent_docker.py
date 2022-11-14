from prefect import task, Flow
from prefect.run_configs import DockerRun
from prefect.storage import Docker

# Now we're including a library that is not included
# in our install of Prefect
import pandas as pd


# NOW, Start your DOCKER agent with:
# prefect agent docker start -l youragentname -l docker
youragentname = "charliesmacbook"

URL = "https://data.austintexas.gov/resource/p53x-x73x.csv?$limit=10"


@task
def download_data():
    df = pd.read_csv(URL)
    return df


@task(log_stdout=True)
def print_res(df):
    print(f"Count of signals is: {len(df.index)}")


with Flow(
    "4-prefect_agent_docker", run_config=DockerRun(labels=[youragentname, "docker"])
) as flow:
    df = download_data()
    print_res(df)

flow.storage = Docker(python_dependencies=["pandas"])

# flow.run()
flow.register("test")
# Can also be completed in command line with:
# prefect register --project test -p 4-prefect_agent_docker.py -f

# Follow the URL in the console or go to cloud.prefect.io
# To find and run your flow manually
