import os
from prefect import task, Flow
import sysrsync
import tempfile
import time

SFTP_ENDPOINT = os.getenv('SFTP_ENDPOINT')

with tempfile.TemporaryDirectory() as tmpdir:
  sysrsync.run(
    verbose=True,
    options=['-a'],
    source_ssh=SFTP_ENDPOINT,
    source='/home/txdot/*zip',
    sync_source_contents=False,
    destination=tmpdir
    )
  print("Temp Directory:", tmpdir)
  for filename in os.listdir(tmpdir):
    print("File:", filename)




  # 7za -y -p$CRIS_PASSWORD -o"/root/automated-tasks/extracts" x "/home/txdot/*.zip";
