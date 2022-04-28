import os
from prefect import task, Flow
import sysrsync
import tempfile
import time
import pprint

SFTP_ENDPOINT = os.getenv('SFTP_ENDPOINT')
ZIP_PASSWORD = os.getenv('ZIP_PASSWORD')

pp = pprint.PrettyPrinter(indent=2)

def download_extract_archives():
  with tempfile.TemporaryDirectory() as zip_tmpdir:
    sysrsync.run(
      verbose=True,
      options=['-a'],
      source_ssh=SFTP_ENDPOINT,
      source='/home/txdot/*zip',
      sync_source_contents=False,
      destination=zip_tmpdir
      )
    print("Temp Directory:", zip_tmpdir)
    time.sleep(5)
  return(zip_tmpdir)

def unzip_archives(archives_directory):
  extracted_csv_directories = []
  for filename in os.listdir(archives_directory):
    print("File:", filename)
    with tempfile.TemporaryDirectory() as extract_tmpdir:
      unzip_command = f'7za -y -p{ZIP_PASSWORD} -o"{extract_tmpdir}" x "{archives_directory}/{filename}"'
      print("Unzip command:", unzip_command)
      os.system(unzip_command)
      extracted_csv_directories.append(extract_tmpdir)
  return(extracted_csv_directories)

with Flow("VZ Ingest") as f:
  zip_location = download_extract_archives()
  print("got zip location:", zip_location, "sleeping 60")
  time.sleep(60)
  extracts = unzip_archives(zip_location)
  pp.pprint(extracts)
  

f.run()
