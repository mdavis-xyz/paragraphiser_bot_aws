import logging
import os
import pprint as pp
import boto3
import json

def unit_tests():
    print('No unit tests to run')

def lambda_handler(event,contex):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if ('unitTest' in event) and event['unitTest']:
        logger.info('Running unit tests')
        unit_tests()
        return()
    else:
        logger.info('Running main (non-test) handler')
        error_handler(logger,event)

# returns an int of the time the stack was last updated
def stack_timestamp():
    client = boto3.client('cloudformation')
    stack_name = os.environ['stack_name']
    response = client.describe_stacks(
        StackName=stack_name 
    )
    assert(len(response['Stacks']) == 1)
    stack_info = response['Stacks'][0]
    assert(stack_info['StackName'] == stack_name)
    stack_timestamp = stack_info['LastUpdatedTime'].timestamp()
    print('Stack %s was last updated at %d' % (stack_name,stack_timestamp))
    return(stack_timestamp)

def error_handler(logger,event):
    # TODO: check whether we've already sent a message
    bot_name = os.environ['bot_name']
    for rec in event['Records']:
        logger.info('record is:')
        logger.info(pp.pformat(event))
        msg_core = json.loads(rec['Sns']['Message'])['AlarmDescription']
        if not msg_already_sent(logger,msg_core):
            print('New message: %s' % msg_core)
            msg = 'A problem has occured with your %s reddit bot.\n\n%s' % (bot_name,msg_core)
            send_sms(logger,msg)
            save_to_table(logger,msg_core)
        else:
            print('Error message: %s' % msg_core)
            print('We\'ve already sent that message. Don\'t do anything')
        
def msg_already_sent(logger,msg):
    table_name = os.environ['error_table']
    timestamp = stack_timestamp()

    client = boto3.client('dynamodb')

    response = client.get_item(
        TableName=table_name,
        Key={
            'error': {
                'S': msg
            },
            'stackUpdateTime': {
                'N': str(timestamp) # boto requires str for ints
            }
        },
        ConsistentRead=False # if we send a message twice within milliseconds, the user won't be inconvenienced
    )

    exists = ('Item' in response)

    logger.info('Item exists? %s' % exists)

    return(exists)
    
def save_to_table(logger,msg):
    table_name = os.environ['error_table']
    timestamp = stack_timestamp()
    client = boto3.client('dynamodb')

    logger.info('saving error message to dynamo for time %d' % timestamp)

    response = client.put_item(
        TableName=table_name,
        Item={
            'error': {
                'S': msg
            },
            'stackUpdateTime': {
                'N': str(timestamp) # boto requires str for ints
            }
        },
    )

    logger.info('saved error message to dynamodb')
    
def send_sms(logger,msg):
    phone_number = os.environ['phone_number']

    client = boto3.client('sns')
   
    logger.info('About to send the following message to %s:\n%s' % (phone_number,msg))

    response = client.publish(
        PhoneNumber=phone_number, 
        Message=msg,
        MessageAttributes={
            'AWS.SNS.SMS.SenderID':{
                'DataType':'String',
                'StringValue':'MyRedditBot'
            }
        }
    )

    pp.pprint(response)
    print('SMS sent')
