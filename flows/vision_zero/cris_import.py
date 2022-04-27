import os
from prefect import task, Flow
import sysrsync
import tempfile
import time

SFTP_ENDPOINT = os.getenv('SFTP_ENDPOINT')

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
  for filename in os.listdir(zip_tmpdir):
    print("File:", filename)
    with tempfile.TemporaryDirectory() as extract_tmpdir:
    unzip_command = f'7za -y -p{ZIP_PASSWORD} -o"{extract_tmpdir}" x "{zip_tmpdir}"




  # 7za -y -p$CRIS_PASSWORD -o"/root/automated-tasks/extracts" x "/home/txdot/*.zip";
