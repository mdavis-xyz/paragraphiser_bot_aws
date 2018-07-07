import time
import logging
import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import json
#import errors

def unit_tests():
    print('No unit tests to run')

def lambda_handler(event,context):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if ('unitTest' in event) and event['unitTest']:
        logger.info('Running unit tests')
        unit_tests()
        get_stats(event,context,dry_run=True)
        return()
    else:
        logger.info('Running main (non-test) handler')
        return(errors.capture_err(get_stats,event,context))

def get_stats(dry_run=False):

    client = boto3.client('dynamodb')

    table_name = os.environ['post_history_table']

    data = {}

    response = client.describe_table(
        TableName=table_name
    )

    data['num_comments'] = response['Table']['ItemCount']

    data['num_updated'] = num_updated()

    data['frac_updated'] = (data['num_updated'] / data['num_comments'])
    data['frac_not_updated'] = 1 - data['frac_updated']

    data['num_not_update'] = data['num_comments'] - data['num_updated']

    # TODO: query dynamo for min timestamp
    first_reply = 1518953631

    now = time.time()

    SEC_PER_DAY = 60*60*24

    days_since = (now - first_reply) / SEC_PER_DAY

    data['comments_per_day'] = data['num_comments'] / days_since

    return(data)

def num_updated():

    table_name = os.environ['post_history_table']

    dynamodb = boto3.resource('dynamodb')
    # doing resource and table instead of client
    # because boto can't do a client query properly
    table = dynamodb.Table(table_name)

    cond=Attr('data').contains('\"updated_reply\"')


    response = table.scan(
        Select='COUNT',
        FilterExpression=cond,
    )

    count = response['Count']

    while ( 'LastEvaluatedKey' in response):
       response = table.scan(
          Select='COUNT',
          FilterExpression=cond,
          ExclusiveStartKey=response['LastEvaluatedKey']
       )
       count += response['Count']


    return(count)

if __name__ == '__main__':
    print('triggered __main__')
    os.environ['post_history_table'] = 'paragraphiser-stack-postHistoryTable-132NV22648DXY'
    data = get_stats(dry_run=False)
    pp.pprint(data)
