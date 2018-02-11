import pprint as pp
import boto3
import os
import time
import random

# maximum delay for an SQS message is 15 minutes
max_delay = 15*60

#
def new_posts(post_ids):


    # seconds
    delays = [
       30,
       1*60, # 1 minute
       2*60,
       4*60,
       7*60,
       10*60,
       20*60,
       30*60,
       45*60,
       60*60, # 1 hour
       1.5*60*60,
       2*60*60,
       3*60*60,
       4*60*60,
       5*60*60,
       7*60*60,
       10*60*60,
       14*60*60,
       18*60*60,
       24*60*60, # 1 day
       1.5*24*60*60,
       2*24*60*60,
       3*24*60*60,
       5*24*60*60,
       8*24*60*60,
       10*24*60*60,
       20*24*60*60,
       30*24*60*60, # 1 month
       50*24*60*60,
       100*24*60*60,
       365*24*60*60 # 1 year
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
        fuzz = 30 # to avoid everything being triggered at exactly midnight or whatever
        then = now + delay + random.randint(-fuzz,fuzz)
        client.update_item(
            TableName=table_name,
            Key={'time':{'N':then}},
            UpdateExpression="ADD post_ids :element",
            ExpressionAttributeValues={":element":{"SS":post_ids}}
        )
