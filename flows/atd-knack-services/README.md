## knack_services.py

This flow uses the docker image automatically created by [this repo](https://github.com/cityofaustin/atd-knack-services). When it is run, it will pull the latest docker image and then run a series of commands inside that container.

***

Primary tasks:
- pull_docker_image: pretty straightforward, pulls the latest docker image for `atd-knack-services`
- get_last_exec_time: Uses Prefect's key value storage to get the last date this flow was run, and passes this value onto all downstream tasks. If it is on the 15th of a month, all data will automatically get replaced. If the `Replace all Data` parameter is set to `True` then it will replace all data.
- records_to_postgrest: Downloads knack records and sends them to a postgres DB
- records_to_agol: (optional) Sends data from postgrest to AGOL
- records_to_socrata: (optional) Sends data from postgrest to Socrata
- agol_build_markings_segment_geometries: (optional) For markings work orders, builds geometry in AGOL based on provided street segments
- records_to_knack: (optional) Send data from one knack app to a destination knack app
- update_last_exec_time: If all upstream tasks were successful, update the date for last execution value storage in Prefect with the current date

Maintenance Tasks:
- knack_street_seg_updater updates segment data in a knack dataset with data that is stored in an AGOL layer.
- knack_location_updater updates location data in knack with information stored in various AGOL layers such as what council district each asset is in. 

***

Parameters:
- App Name (str): The name of the source knack app (ex: "data-tracker")
- Knack Container (str): The "view" name of the container in knack (ex: "view_3628")
- Records to Knack: App Name Destination (str): If provided, will send data from the source knack app to the destination knack app in `records_to_knack`. Providing an empty string will skip this task.
- AGOL Build Segment Geometry Layer (str): The name of the layer in the `CONFIG` of `agol_build_markings_segment_geometries.py` to build the geometry of. Providing an empty string will skip this task.
- Replace all Data (bool): A flag if True to replace all data and ignore typical modified date constraints 
- Send data to Socrata (bool): A flag if True to send data to the provided Socrata dataset
- Send data to AGOL (bool): A flag if True to send data to the provided AGOL layer

***

Secrets:

The primary storage for all knack services scripts is in the `atd-knack-services` JSON block in Prefect. This block's JSON schema is based on what knack app you are using. A special key is also set aside for storing when each flow was last executed successfully, called `PREV-EXECS`.
```
{
	"data-tracker":
	{
		"secret_1":"abc",
		"secret_2":"xyz"
	},
	"signs-markings":
	{
		"secret_3":"def",
		"secret_4":"uvw"
	},
	"PREV-EXECS":
	{
		"Knack Services 1": "2023-03-23",
    	"Knack Services 2": "2023-03-28"
	}
}
```

