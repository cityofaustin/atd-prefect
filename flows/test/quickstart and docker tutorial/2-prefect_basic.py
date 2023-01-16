from prefect import task, Flow


@task
def add_one(val):
    return val + 1


@task
def print_res(val):
    print(f"Our result is: {val}")


with Flow("2-prefect_basic") as flow:
    val = add_one(1)
    print_res(val)

flow.run()
