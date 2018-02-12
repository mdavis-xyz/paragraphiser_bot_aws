import pprint as pp
import boto3
import json


def lambda_handler(event,contex):
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        return(common.unit_tests())
    else:
        print('Running main (non-test) handler')
        pp.pprint(event)
        phone_number = os.environ['phone_number']
        print('Would handle errors to %s' % phone_number)
