import praw
import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
import json
import common
import scheduling

def lambda_handler(event,contex):
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        return(common.unit_tests())
    else:
        print('Running main (non-test) handler')
        return(check_old(event))

def check_old(event):
    print('Event:')
    pp.pprint(event)
