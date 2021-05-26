#!/bin/bash

# NB: For now three will be only one container instance and migrations never run concurrently
python -u -m alembic upgrade head
python -u -m auxy.bot
