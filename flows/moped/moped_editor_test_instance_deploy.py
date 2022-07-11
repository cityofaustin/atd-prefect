#!/usr/bin/env python

"""
Name: Moped Editor Test Instance Deployment
Description: Build and deploy the resources needed to test
    a feature branch of the Moped Editor application
Schedule: TBD
Labels: TBD
"""

import os
import json
import boto3
import prefect

# Prefect
from prefect import Flow, task


AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
VPC_SUBNET_A = os.environ["VPC_SUBNET_A"]
VPC_SUBNET_B = os.environ["VPC_SUBNET_B"]
ELB_SECURITY_GROUP = os.environ["ELB_SECURITY_GROUP"]
TASK_ROLE_ARN = os.environ["TASK_ROLE_ARN"]


# Logger instance
logger = prefect.context.get("logger")

# Frontend:
# 1. When feature PR is opened, a deploy preview spins up and is linked in PR
# 2. Env vars are available to introspect PR # and context (CONTEXT = deploy-preview)
#    https://docs.netlify.com/configure-builds/environment-variables/?utm_campaign=devex-tzm&utm_source=blog&utm_medium=blog&utm_content=env-vars&_gl=1%2agvssna%2a_gcl_aw%2aR0NMLjE2NTQ1NDAxNzcuQ2p3S0NBand5X2FVQmhBQ0Vpd0EySUhIUUFud3NXc1ltbXJybGs5SnVfWTJlazlkUF9hVmM4WVZuTjR5Zk5QR0Y2U2ZOLTMycl93ekFCb0M2Y0lRQXZEX0J3RQ..&_ga=2.210432213.1131530997.1654540177-2032963523.1654540177&_gac=1.123937528.1654540177.CjwKCAjwy_aUBhACEiwA2IHHQAnwsWsYmmrrlk9Ju_Y2ek9dP_aVc8YVnN4yfNPGF6SfN-32r_wzABoC6cIQAvD_BwE#read-only-variables

# Considerations:
# 1. Auth (use staging user pool) needs a callback URL set in the user pool. How does this work
#    for the deploy previews? (I know that we can't use SSO)
#    - Just do whatever deploy previews do for auth

# Questions:
# 1. What S3 bucket does current moped-test use for file uploads?

# Database and GraphQL engine tasks
@task
def create_database():
    # Use psycopg2 to connect to RDS
    # Need to think about how to prevent staging or prod DBs from being touched
    # Create ephemeral DB with name tied to PR # so it is easy to identify later
    # Stretch goal: replicate prod data
    logger.info("creating database")
    return True


@task
def remove_database():
    # Use psycopg2 to connect to RDS
    # Remove ephemeral DB
    # When PR is closed? When inactive for certain amount of time?
    logger.info("removing database")
    return True

@task
def create_ecs_cluster(basename):
    # Deploy ECS cluster
    logger.info("Creating ECS cluster")

    ecs = boto3.client("ecs", region_name="us-east-1")
    create_cluster_result = ecs.create_cluster(clusterName=basename)

    logger.info("Cluster ARN: " + create_cluster_result["cluster"]["clusterArn"])

    return create_cluster_result


@task
def remove_ecs_cluster(cluster):
    # Remove ECS cluster
    logger.info("removing ECS cluster")

    ecs = boto3.client("ecs", region_name="us-east-1")
    delete_cluster_result = ecs.delete_cluster(cluster=cluster["cluster"]["clusterName"])

    return delete_cluster_result

@task
def create_load_balancer(basename):

    logger.info("Creating Load Balancer")
    elb = boto3.client('elbv2')

    create_elb_result = elb.create_load_balancer(
        Name = basename,
        Subnets = [ VPC_SUBNET_A, VPC_SUBNET_B ],
        SecurityGroups = [ ELB_SECURITY_GROUP ],
        Scheme = 'internet-facing',
        Tags = [
            {
                'Key': 'name',
                'Value': basename,
            },
        ],
        Type='application',
        IpAddressType='ipv4',
        )

    return create_elb_result

@task
def remove_load_balancer(load_balancer):
    logger.info("removing Load Balancer")
    
    elb = boto3.client('elbv2')
    delete_elb_result = elb.delete_load_balancer(
        LoadBalancerArn = load_balancer["LoadBalancers"][0]["LoadBalancerArn"]
        )

    return delete_elb_result

@task
def create_task_definition(basename):
    logger.info("Adding task definition")
    ecs = boto3.client("ecs", region_name="us-east-1")

    response = ecs.register_task_definition(
        family='moped-graphql-endpoint-' + basename,
        executionRoleArn=TASK_ROLE_ARN,
        networkMode='awsvpc',
        requiresCompatibilities=['FARGATE'],
        cpu='256',
        memory='1024',
        containerDefinitions=[
            {
                'name': 'graphql-engine',
                'image': 'hasura/graphql-engine:latest',
                'cpu': 256,
                'memory': 512,
                'portMappings': [
                    {
                        'containerPort': 8080,
                        'hostPort': 8080,
                        'protocol': 'tcp'
                    },
                ],
                'essential': True,
                'environment': [
                    {
                        'name': 'HASURA_GRAPHQL_ENABLE_CONSOLE',
                        'value': 'true',
                    },
                    {
                        'name': 'HASURA_GRAPHQL_ENABLE_TELEMETRY',
                        'value': 'false',
                    },
                ],
                'logConfiguration': {
                    'logDriver': 'awslogs',
                    'options': {
                        'awslogs-group': 'moped-test',
                        'awslogs-region': 'us-east-1',
                        'awslogs-stream-prefix': basename,
                    },
                },
            },
        ],
        )

    return response

@task
def remove_task_definition(task_definition):
    logger.info("removing task definition")

    ecs = boto3.client("ecs", region_name="us-east-1")
    response = ecs.deregister_task_definition(
        taskDefinition=task_definition["taskDefinition"]["taskDefinitionArn"]
        )

    return response

# Activity log (SQS & Lambda) tasks

@task
def create_service(basename, load_balancer):
    # Create ECS service
    logger.info("Creating ECS service")

    ecs = boto3.client("ecs", region_name="us-east-1")
    create_service_result = ecs.create_service(
        cluster=basename,
        serviceName=basename,
        taskDefinition=basename,
        desiredCount=1,
        placementStrategy=[
            {
                'type': 'spread',
                'field': 'attribute:ecs.availability-zone',
            },
        ],
        loadBalancers=[
            {
                'targetGroupArn': 'arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/' + basename + '/1a2b3c4d5e6f7g',
                'containerName': 'graphql-engine',
                'containerPort': 8080,
            },
        ],
        healthCheckGroup={
            'healthCheckGroupName': basename,
            'healthCheckType': 'ECS',
            'interval': '30',
            'timeout': '5',
            'unhealthyThreshold': '3',
            'healthyThreshold': '5',
        },
        tags=[
            {
                'Key': 'name',
                'Value': basename,
            },
        ],
        )

    return create_service_result

@task
def create_activity_log_sqs():
    # Use boto3 to create SQS
    logger.info("creating activity log SQS")
    return True


@task
def create_activity_log_lambda():
    # Use boto3 to create activity log event lambda
    logger.info("creating activity log Lambda")
    return True


@task
def remove_activity_log_sqs():
    # Use boto3 to remove SQS
    logger.info("removing activity log SQS")
    return True


@task
def remove_activity_log_lambda():
    # Use boto3 to remove activity log event lambda
    logger.info("removing activity log Lambda")
    return True




# Moped API tasks


@task
def create_moped_api():
    # Deploy moped API using Zappa or the CloudFormation template that it generates
    logger.info("creating Moped API Lambda")
    return True


@task
def remove_moped_api():
    # Remove CloudFormation stack that create_moped_api deployed with boto3
    return True


with Flow(
    "Create Moped Environment"
  ) as flow:
    # Calls tasks
    logger.info("Calling tasks")

    basename = 'test-ecs-cluster'

    #cluster = {'cluster': {'clusterName': basename}}
    #remove_ecs_cluster(cluster)

    cluster = create_ecs_cluster(basename=basename)
    load_balancer = create_load_balancer(basename=basename)
    task_definition = create_task_definition(basename=basename)
    service = create_service(basename=basename)

    #TODO: These removal tasks should each be modified to take either the response object or the name of the resource
    #remove_task_definition = remove_task_definition(task_definition)
    #remove_load_balancer(load_balancer)
    #remove_ecs_cluster(cluster)


if __name__ == "__main__":
    flow.run()
