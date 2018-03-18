import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
import json
import common


def lambda_handler(event,contex):
    print('Warning: this function doesnt work as lambda. It takes to long')
    print('TODO: rewrite this to paginate dynamodb calls, then invoke itself')
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        #common.unit_tests()
        #recheck_all(dry_run=True)
    else:
        print('Running main (non-test) handler')
        assert(NotImplementedError)
        return(recheck_all(dry_run=False))

def recheck_all(dry_run=False):
    post_ids = fetch_all()

    print('There are %d posts to recheck' % len(post_ids))

    #print('They are: %s' % post_ids)

    # minutes
    delay = 0

    for post_id in post_ids:
        schedule_check(post_id,delay,dry_run)
        delay += 0.5 # check 2 posts per minute, to avoid api congestion
        # dynamo limit is 5 per second for this table
        # Halving that frequency, just to be sure
        time.sleep(2/5) # python 3 does this as a float

    print('done')

# delay is measured in minutes
def schedule_check(post_id,delay,dry_run):

    client = boto3.client('dynamodb')

    table_name = os.environ['schedule_table']

    now = int(time.time())

    SEC_PER_MIN = 60

    then = now + delay*SEC_PER_MIN

    if dry_run:
        print('Would schedule post %s for delay %.1f minutes' % (post_id,delay))
    else:
        print('scheduling post %s for delay %.1f minutes' % (post_id,delay))
        client.update_item(
            TableName=table_name,
            Key={'time':{'N':str(then)},'hash':{'S':common.hash_key_val}},
            UpdateExpression="ADD post_ids :element",
            ExpressionAttributeValues={":element":{"SS":[post_id]}} # appends
        )



# fetch the batch of entries in the dynamodb table
# with timestamps covering the next n seconds
# returns a set of post_ids
def fetch_all():

    client = boto3.client('dynamodb')

    table_name = os.environ['post_history_table']

    response = client.scan(
        TableName=table_name,
        AttributesToGet=[
            'post_id'
        ],
        Select='SPECIFIC_ATTRIBUTES',
        ReturnConsumedCapacity='NONE',
        ConsistentRead=False
    )

    post_ids = [item['post_id']['S'] for item in response['Items']]

    while 'LastEvaluatedKey' in response:
    
        response = client.scan(
            TableName=table_name,
            AttributesToGet=[
                'post_id'
            ],
            Select='SPECIFIC_ATTRIBUTES',
            ReturnConsumedCapacity='NONE',
            ConsistentRead=False,
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        
        post_ids.extend([item['post_id']['S'] for item in response['Items']])

    

    return(post_ids)
    
if __name__ == '__main__':
    print('Triggered __main__')

    os.environ['post_history_table'] = 'paragraphiser-stack-postHistoryTable-132NV22648DXY'
    os.environ['schedule_table'] = 'paragraphiser-stack-scheduleTable-D4P9THUEJJBT'

    recheck_all()

    print('done')
