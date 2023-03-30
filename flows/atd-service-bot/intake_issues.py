"""
Name: ATD Service Bot: Intake Issues
Description: Sends new issue data from our service portal (knack) to our Github
Schedule: */3 * * * * (AKA once every 3 minutes)
Work queue concurrency limit: 1
prefect deployment build flows/atd-service-bot/intake_issues.py:intake \
    --cron "*/3 * * * *" --pool atd-data-03 -q atd-service-bot \
    --name "Service Bot: Intake Issues" -o "deployments/atd_service_bot_intake/staging.yaml" \
    -sb github/atd-service-bot-staging --skip-upload \
    --description "Repo: https://github.com/cityofaustin/atd-service-bot, Sends new issue data from our service portal (knack) to our Github"
"""

import docker

# Prefect
from prefect import flow, task, get_run_logger

from helpers import get_env_vars, pull_docker_image

# Knack Issues to Github
@task(name="intake_new_issues", timeout_seconds=60)
def intake_new_issues(environment_variables, docker_image):
    logger = get_run_logger()

    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-service-bot/intake.py",
            environment=environment_variables,
            volumes=None,
            remove=True,
            detach=False,
            stdout=True,
        )
        .decode("utf-8")
    )
    logger.info(response)
    return response


@flow(name="Service Bot: Intake Issues")
def intake(docker_tag="production", env="production"):
    """Intakes new issues from Knack to Github

    Keyword arguments:
    docker_tag -- the docker tag to use (default "production")
    env -- the environment to use (default "production")
    """
    # 1. Get secrets from Prefect KV Store
    environment_variables = get_env_vars(env)

    # 2. Pull latest docker image
    docker_image = pull_docker_image(docker_tag)

    # 3. Intake new issues to github
    intake_new_issues(environment_variables, docker_image)


if __name__ == "__main__":
    intake()
