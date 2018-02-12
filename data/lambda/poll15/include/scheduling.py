import pprint as pp
import boto3
import os
import time
import random

# maximum delay for an SQS message is 15 minutes
max_delay = 15*60
SEC_PER_MIN = 60
MIN_PER_H = 60
S_PER_H = SEC_PER_MIN * MIN_PER_H
H_PER_DAY = 24
SEC_PER_H = H_PER_DAY * SEC_PER_H

# Apparently you can't have a dynamo table with just a
# sort key. So I'll add a hash key, which will only have
# one value of 0
hash_key_val = 'data'

#
def new_posts(post_ids):


    # seconds
    delays = [
       30,
       1*SEC_PER_MIN, # 1 minute
       2*SEC_PER_MIN,
       4*SEC_PER_MIN,
       7*SEC_PER_MIN,
       10*SEC_PER_MIN,
       20*SEC_PER_MIN,
       30*SEC_PER_MIN,
       45*SEC_PER_MIN,
       1*SEC_PER_H, # 1 hour
       1.5*SEC_PER_H,
       2*SEC_PER_H,
       3*SEC_PER_H,
       4*SEC_PER_H,
       5*SEC_PER_H,
       7*SEC_PER_H,
       10*SEC_PER_H,
       14*SEC_PER_H,
       18*SEC_PER_H,
       SEC_PER_DAY, # 1 day
       1.5*SEC_PER_DAY,
       2*SEC_PER_DAY,
       3*SEC_PER_DAY,
       5*SEC_PER_DAY,
       8*SEC_PER_DAY,
       10*SEC_PER_DAY,
       20*SEC_PER_DAY,
       30*SEC_PER_DAY, # 1 month
       50*SEC_PER_DAY,
       100*SEC_PER_DAY,
       365*SEC_PER_DAY # 1 year
    ]


    delays = [int(x) for x in delays] # rounding
    immediates = [x for x in delays if x < max_delay]
    later = [x for x in delays if x not in immediates]

    send_immediates(immediates,post_ids)
    print('Finished sending immediate SQS messages')
    print('Scheduling later messages')
    send_later(immediates,post_ids)
    print('Finished scheduling messages for later')

def get_queue_url():
    queue_name = os.environ['delay_queue']
    response = client.get_queue_url(
        QueueName=queue_name
    )
    url = response['QueueUrl']
    return(url)

def send_immediates(delays,post_ids):
    now = int(time.time())

    bot_name = os.environ['bot_name']

    queue_url = get_queue_url()

    for delay in delays:
        for post_id in post_ids:
            send_message(post_id,delay,url=queue_url)

def send_message(post_id,delay,url=None):
    if url == None:
        url = get_queue_url()

    client = boto3.client('sqs')

    payload = {
        'post_id': post_id
    }

    print('Sending SQS message to %s for post %s with delay of %d' % (url,post_id,delay))
    response = client.send_message(
        QueueUrl=url,
        MessageBody=json.dumps(),
        DelaySeconds=delay
    )

def send_later(immediates,post_ids):
    client = boto3.client('dynamodb')

    table_name = os.environ['delay_table']

    for delay in delays:
        now = int(time.time())

        # to avoid everything being triggered at exactly midnight or whatever
        fuzz = 30
        then = now + delay + random.randint(-fuzz,fuzz)

        client.update_item(
            TableName=table_name,
            Key={'time':{'N':then},'hash':hash_key_val},
            UpdateExpression="ADD post_ids :element",
            ExpressionAttributeValues={":element":{"SS":post_ids}}
        )

        # dynamo limit is 5 per second for this table
        # Halving that frequency, just to be sure
        time.sleep(2/5)

# fetch the batch of entries in the dynamodb table
# with timestamps covering the next 15 minutes
def fetch_15():
    time_until = int(time.time.now() + max_delay*SEC_PER_MIN - 1)
    print('Fetching all dynamodb entries <= %d' % time_until)
    items = table_query_unpaginated(time_until)

    print('Found %d timestamps' % len(items))
    print('That includes %d items' % sum([len(item['post_ids']['SS']) for item in items]))
    queue_url = get_queue_url()

    for item in items:
        for post_id in item['post_ids']['SS']:
            now = int(time.time())
            time_to_execute = int(item['time'])
            delay = time_to_execute - now
            print('Sending SQS message for post %s with delay %d' % (post_id,delay))
            send_message(post_id,delay,url=queue_url)

    print('Deleting those items from dynamodb table')
    for item in items:
        delete_items(items)

        # dynamo limit is 5 per second for this table
        # slowing that down a lot, just to be sure
        time.sleep(4/5)

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
        KeyConditionExpression='time <= %d' % time_until
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
                'N': item['time']['N']
            }
        }
    )
