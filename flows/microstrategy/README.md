# Microstrategy Reports to S3

This Prefect flow runs and then downloads a report from Microstrategy and then uploads it as a csv file in a S3 bucket. 

## Parameters

By default, two reports are defined for this flow. More can be added in the Prefect cloud management console. Two fields are required for each report: ID and name. 

- Report ID: To find report ID, go to the report in Microstrategy web then, go to Tools -> Report Details Page or Document Details Page, then click "Show Advanced Details" button at the bottom.

- Report Name: Must be unique as it is used as the file name in the S3 bucket

## Power BI

The purpose of this flow is to make it easier to access Microstrategy reports in external applications like Power BI. The URL for all objects in the S3 is default to publicly accessible. 

To access this data in Power BI, view the file in S3 and copy the URL to the object. Then, use the "Get Data" button in Power BI, and select "web" and paste in your copied URL. 

A benefit of "web" data sources in Power BI is that they can be scheduled refreshed to stay in sync with the latest data published to the S3 bucket.

## Docker Flow and Running Locally

This is the first Prefect flow in this repo that uses `DockerRun`,`Docker` storage, and a Docker Agent. This allows us to run this flow with access to our three needed python dependencies.

This cannot be run in a `local` agent, so to run this locally you must first create a docker agent on your machine.

```
$ prefect agent docker start -l label1 -l label2
```

Then, register this flow with the same `labels` as above. When the flow is registered, `docker build` is run using the defined `python_dependencies`. It should `docker push` this image to our `atddocker` dockerhub account, but if not you can also `docker push` manually after registering. Each time the flow is triggered on the docker agent, it will do a `docker pull`, so any image changes will be brought down at runtime.

Then, to run this flow on your local docker agent, use the Prefect cloud web console to run your flow and change parameters if needed.