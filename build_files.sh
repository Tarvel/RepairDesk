#!/bin/bash
# build_files.sh

# Install dependencies
python3 -m pip install -r requirements.txt

# Run collectstatic to gather static files
python3 manage.py collectstatic --noinput --clear
