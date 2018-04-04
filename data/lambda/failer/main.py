import logging
import os
import pprint as pp
import boto3
import json
import errors

def unit_tests():
    print('No unit tests to run')

def lambda_handler(event,context):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if ('unitTest' in event) and event['unitTest']:
        logger.info('Running unit tests')
        unit_tests()
        return()
    else:
        logger.info('Running main (non-test) handler')
        return(errors.capture_err(main,event,context))

def main(event,context):
        assert(False)
