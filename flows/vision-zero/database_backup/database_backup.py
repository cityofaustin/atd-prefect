import os
import subprocess
from datetime import datetime

def get_current_datetime():
  current_datetime = datetime.now()
  date = current_datetime.strftime("%Y-%m-%d")
  time = current_datetime.strftime("%H-%M")
  print("Making backup for",  date, "at", time)
  return date, time

def make_backup_directory(date):
  path = ("./tmp/" + date + "/hello")
  os.makedirs(path, exist_ok=True)

def 

date, time = get_current_datetime()
make_backup_directory(date)