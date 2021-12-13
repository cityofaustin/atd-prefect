# Flow Control

To control the flow or design and manipulate
the ETL graph there are several methods included
in Prefect, including these:

```python
    a = Task()
    b = Task()
    c = Task()
    
    # Using flow.chain
    flow.chain(a,b,c)
    
    # Using flow.add_edge,
    flow.add_edge(a, b)
    flow.add_edge(b, c)
    
    # Using flow.add_task (does not chain tasks but executes in order)
    flow.add_task(a)
    flow.add_task(b)
    flow.add_task(c)
    
    # Via task.set_upstream
    b.set_upstream(a)
    c.set_upstream(b)
    
    # Via task.set_downstream
    a.set_downstream(b)
    b.set_downstream(c)

    # Via task.set_dependencies
    b.set_dependencies(upstream_tasks=[a], downstream_tasks=[c], flow=flow)
    
    # Via Merge (merges all tasks into a single task run in order)
    merge([hello_task, hello_task_two, hello_task_three], flow=flow)

    
```

There is no strong preference, most of our ETL or DAGs
currently in Airflow do not have a complex graph.


## Conditional Tasks

https://docs.prefect.io/core/examples/conditional.html

## Sources

Flow:
- https://docs.prefect.io/api/latest/core/flow.html

Flow Control:
- https://docs.prefect.io/api/latest/tasks/control_flow.html