import os
import codecs
import csv

import boto3

print("Retrieving data from AWS S3")

s3 = boto3.client("s3")
resource = boto3.resource("s3")

my_bucket = resource.Bucket("atd-afd-incident-data")

# SO: https://stackoverflow.com/questions/45375999/how-to-download-the-latest-file-of-an-s3-bucket-using-boto3
get_last_modified = lambda obj: int(obj["LastModified"].strftime("%s"))
objs = s3.list_objects_v2(Bucket="atd-afd-incident-data")["Contents"]
last_added = [obj["Key"] for obj in sorted(objs, key=get_last_modified)][-1]

print(last_added)
import pandas

# path = "s3://atd-afd-incident-data/atd-afd/a5k8kl2ite39rut6l635bi2rts74okl1reagee81"
obj = s3.get_object(
    Bucket="atd-afd-incident-data",
    Key=last_added,
)
print(obj)
data = pandas.read_csv(obj["Body"], on_bad_lines="skip")
print(data.shape)
print(data.head(500))


# files = list(my_bucket.objects.filter(Prefix="atd-afd"))
# print(files)


# def read_csv_from_s3(bucket_name, key, column):
#     data = client.get_object(Bucket=bucket_name, Key=key)

#     for row in csv.DictReader(codecs.getreader("utf-8")(data["Body"])):
#         print(row[column])


# response = client.list_buckets()

# reponse = read_csv_from_s3(
#     "atd-afd-incident-data/atd-afd/", "a5k8kl2ite39rut6l635bi2rts74okl1reagee81"
# )
# print(response)
