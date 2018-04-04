import logging
import os
import pprint as pp
import boto3
import json

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
        assert(False)
