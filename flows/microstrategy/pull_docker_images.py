from prefect import task, Flow, Parameter, unmapped
from prefect.run_configs import UniversalRun
from prefect.storage import Docker, GitHub
from prefect.tasks.docker import PullImage

ENV = "test"

@task(
    name="pull_docker_image",
)
def pull_docker_image(image):
    client = docker.from_env()
    client.images.pull(image, all_tags=True)
    logger.info(docker_env)
    return

with Flow(
    f"pull_docker_image_{ENV}",
    schedule=None,
    run_config=UniversalRun(labels=[ENV, "atd-data02"]),
     storage=GitHub(
         repo="cityofaustin/atd-prefect",
         path="flows/microstrategy/pull_docker_images.py",
         ref="microstrategy-reports",  # The branch name
     ),
    ) as flow:
    imgs = Parameter("images", default=["atddocker/atd-microstrategy:test"], required=True)
    pull_docker_image.map(imgs)


flow.run(parameters={"images": ["atddocker/atd-microstrategy:test"]})


