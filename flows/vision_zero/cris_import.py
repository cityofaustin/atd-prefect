import os
from prefect import task, Flow
import sysrsync
import tempfile
import time

SFTP_ENDPOINT = os.getenv('SFTP_ENDPOINT')
ZIP_PASSWORD = os.getenv('ZIP_PASSWORD')

#for filename in os.listdir(zip_tmpdir):
  #print("File:", filename)

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
  return(zip_tmpdir)

def unzip_archive(archive):
  with tempfile.TemporaryDirectory() as extract_tmpdir:
    unzip_command = f'7za -y -p{ZIP_PASSWORD} -o"{extract_tmpdir}" x "{zip_tmpdir}/{filename}"'
    print("Unzip command:", unzip_command)
    unzip_result = os.system(unzip_command)
    return extract_tmpdir;
