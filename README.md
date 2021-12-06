# Prefect

Initial documentation of our new ETL process. 

## Development

The code in this repo will run in many machines, in order to avoid
conflicts it will be ideal to have some loosely held expecations
in terms of runtime environment and dependencies: 

- Python 3.8.X 
- Pip 21.1.X
- VirtualEnv

Pyenv is recommended to work with multiple versions
of python in your system.

## Getting started

```bash
# 1. Create a virtual environment
$ virtualenv venv

# 2. Source the virtual environment
$ source venv/bin/activate

# 3. Install the requirements for local development
$ pip install -r requirements.txt

# 4. Run the example flow file
$ python example/flow.py
```
