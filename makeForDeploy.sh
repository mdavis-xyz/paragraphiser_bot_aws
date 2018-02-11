#!/bin/bash
set -e # exit if a single command fails

rm -rf env
python3 -m virtualenv --python=$(which python3.6) env
. env/bin/activate
# pip install nose
pip install boto3
pip install praw
pip install mako
