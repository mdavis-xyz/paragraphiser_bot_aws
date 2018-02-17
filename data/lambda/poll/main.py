import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
import json
import common

def lambda_handler(event,contex):
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        common.unit_tests()
        check_latest_batch(dry_run=True)
    else:
        print('Running main (non-test) handler')
        return(check_latest_batch())

def check_latest_batch(dry_run=False):
    post_ids = fetch_next()

    if len(post_ids) == 0:
        print('Nothing scheduled. Exiting without doing anything')
        return()

    client = boto3.client('lambda')

    handler_lambda_arn = os.environ['checkOldArn']

    if dry_run and (len(post_ids) == 0):
        post_ids = ['test_only'] # won't be executed, so can be whatever
                                 # but should be something, so we check the permissions

    for post_id in post_ids:

        payload = {'post_id':post_id}

        # 'Event' means async
        invocationType = 'DryRun' if dry_run else 'Event'

        print('Triggering check for post %s' % post_id)
        response = client.invoke(
            FunctionName=handler_lambda_arn,
            InvocationType=invocationType,
            Payload=json.dumps(post_id).encode(),
            Qualifier='string'
        )

        print('Invoked %s with payload %s' % (handler_lambda_arn,str(payload)))

    print('Invoked lambdas to handle those posts')
    print('done')

# fetch the batch of entries in the dynamodb table
# with timestamps covering the next n seconds
# returns a set of post_ids
def fetch_next(seconds=60):
    time_until = int(time.time() + seconds - 1)
    print('Fetching all dynamodb entries <= %d' % time_until)
    items = table_query_unpaginated(time_until) 

    print('Found %d timestamps' % len(items))
    print('That includes %d items' % sum([len(item['post_ids']['SS']) for item in items]))
    queue_url = get_queue_url()

    post_ids = set()

    for item in items:
        # add contents of item['post_ids']['SS'] to the set
        post_ids |= item['post_ids']['SS']

    print('Deleting those items from dynamodb table')
    for item in items:
        delete_items(items)

        # dynamo limit is 5 per second for this table
        # slowing that down a lot, just to be sure
        time.sleep(4/5)

    return(post_ids)
# performs a dynamodb query for all items with key 'time'
# of value time_until or less
# handles pagination issues
def table_query_unpaginated(time_until):
    client = boto3.client('dynamodb')

    table_name = os.environ['delay_table']

    response = client.query(
        TableName=table_name,
        IndexName='time',
        Select='ALL_ATTRIBUTES',
        # Limit=123,
        ConsistentRead=True,
        ScanIndexForward=True, # ascending
        ReturnConsumedCapacity='NONE',
        KeyConditionExpression='time <= :%d' % time_until
#        KeyConditionExpression=Key('time').lte(time_until)
    )

    items = response['Items']

    while 'LastEvaluatedKey' in response:
        response = client.query(
            TableName=table_name,
            IndexName='time',
            Select='ALL_ATTRIBUTES',
            # Limit=123,
            ExclusiveStartKey=response['LastEvaluatedKey'],
            ConsistentRead=True,
            ScanIndexForward=True, # ascending
            ReturnConsumedCapacity='NONE',
            KeyConditionExpression='time <= %d' % time_until
        )
        items.extend(response['Items'])

    return(items)

def delete_item(item):
    client = boto3.client('dynamodb')

    table_name = os.environ['delay_table']

    response = client.delete_item(
        TableName=table_name,
        Key={
            'hash': {
                'S': hash_key_val
            },
            'time': {
                'N': str(item['time']['N'])
            }
        }
    )


