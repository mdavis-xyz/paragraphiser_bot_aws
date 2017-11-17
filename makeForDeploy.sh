#!/bin/bash
set -e # exit if a single command fails

rm -rf env
virtualenv -p /usr/bin/python3 ./env
. env/bin/activate
# pip install nose
pip install boto3
pip install praw
pip install mako
