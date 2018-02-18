import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
import json
import common

# Apparently you can't have a dynamo table with just a
# sort key. So I'll add a hash key, which will only have
# one value of 0
# TODO: move this to common?
hash_key_val = 'data'

def lambda_handler(event,contex):
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        common.unit_tests()
        check_latest_batch(dry_run=True)
    else:
        print('Running main (non-test) handler')
        return(check_latest_batch())

def check_latest_batch(dry_run=False):
    post_ids = fetch_next(dry_run=dry_run)

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
        )

        print('Invoked %s with payload %s' % (handler_lambda_arn,str(payload)))

    print('Invoked lambdas to handle those posts')
    print('done')

# fetch the batch of entries in the dynamodb table
# with timestamps covering the next n seconds
# returns a set of post_ids
def fetch_next(dry_run=False,seconds=60):
    time_until = int(time.time() + seconds - 1)
    print('Fetching all dynamodb entries <= %d' % time_until)
    items = table_query_unpaginated(time_until) 

    print('Found %d timestamps' % len(items))
    print('That includes %d items' % sum([len(item['post_ids']) for item in items]))

    # using set to merge duplicates
    post_ids = set()

    # TODO: replace this with the faster but less clear list comprehension
    for item in items:
        # add contents of item['post_ids']['SS'] to the set
        post_ids |= item['post_ids']

    print('Deleting those items from dynamodb table')
    for item in items:
        if dry_run:
            print('Would delete item')
            pp.pprint(item)
        else:
            delete_item(item)

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

    dynamodb = boto3.resource('dynamodb')
    # doing resource and table instead of client
    # because boto can't do a client query properly
    table = dynamodb.Table(table_name)

    #print('Table %s has schema: ' % table_name)
    #pp.pprint(table.key_schema)

    response = table.query(
        Select='ALL_ATTRIBUTES',
        Limit=100,
        ConsistentRead=False, # if we miss out by a few milliseconds, we'll get it again in a minute
        KeyConditionExpression=Key('hash').eq(hash_key_val) & Key('time').lte(time_until)
    )
    items = response['Items']

    while ('LastEvaluatedKey' in response) and len(response['LastEvaluatedKey'] > 0):
        response = table.query(
            Select='ALL_ATTRIBUTES',
            Limit=100,
            ConsistentRead=False, # if we miss out by a few milliseconds, we'll get it again in a minute
            KeyConditionExpression=Key('hash').eq(hash_key_val) & Key('time').lte(time_until), # Key('hash').eq(hash_key_val) & 
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response['Items'])

    return(items)

def delete_item(item):
    client = boto3.client('dynamodb')

    table_name = os.environ['delay_table']

    key = {
            'hash': {
                'S': hash_key_val
            },
            'time': {
                'N': str(int(item['time']))                                                                                                                                                   
            }
        }

    print('Deleting item using key:')
    pp.pprint(key)

    response = client.delete_item(
        TableName=table_name,
        Key=key
    )


