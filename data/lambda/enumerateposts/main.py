import json
import logging
import pprint as pp

def lambda_handler(event, context):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logger.info('event: ' + str(event))

    logger.info('hello world')

    return('OK')
