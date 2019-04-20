#!/bin/bash

# Usage: 1st argument is the data directory

set -e # exit if a single command fails

# check number of arguments
if [ "$#" -ne 1 ] || ! [ -d "$1" ]; then
  echo "Usage: $0 libdir" >&2
  exit 1
fi

# if ! [[ -z "$VIRTUAL_ENV" ]]; then
#     echo "VIRTUAL_ENV is set"
#     exit 1
# fi

rm -rf env
virtualenv -p /usr/bin/python3.6 ./env
. env/bin/activate
# pip install nose
pip install boto3
pip install praw
pip install mako # dependency of common.py
pip install certifi beautifulsoup4

rm -rf include
mkdir include
cp $1/credentials/praw.ini include/praw.ini
cp $1/util/common.py include/common.py
for DEP in common.py errors.py  template.md templateTest.md
do
    cp $1/util/$DEP include/$DEP 
done
deactivate

echo 'makescript returning sucessfully'
