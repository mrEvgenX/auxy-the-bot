#!/bin/bash

# NB: For now is supposed only one container instance and migrations never run concurrently
python -u -m alembic upgrade head
python -u -m auxy.main
