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
        error_handler(logger,event)


def error_handler(logger,event):
    # TODO: check whether we've already sent a message
    if ('Records' in event) and (type(event) != type('')): # SNS with general alarm
        logger.info('invoked from SNS alarm')
        logger.info('%d alarms' % len(event))
        for rec in event['Records']:
            logger.info('record is:')
            logger.info(pp.pformat(event))
            msg_core = json.loads(rec['Sns']['Message'])['AlarmDescription']
            msg_full = 'A problem has occured with your %s reddit bot.\n\n%s' % (bot_name,msg_core)
            handle(logger,msg_full,msg_core)
    else: # direct invocation from try/except
        assert('error_type' in event)
        assert(event['error_type'] == 'direct invocation from traceback')
        logger.info('was directly invoked')
        msg_full = 'Lambda %s failed' % event['lambda_name']
        msg_full += '\n\nFull Traceback:\n\n%s' % event['traceback']
        handle(logger,msg_full,event['lambda_name'])

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

def handle(logger,msg_full,msg_hash):
    if not msg_already_sent(logger,msg_hash):
        bot_name = os.environ['bot_name']
        print('New message: %s' % msg_full)
        send_msg(logger,msg_full)
        save_to_table(logger,msg_hash)
    else:
        print('Error message: %s' % msg_full)
        print('We\'ve already sent a message about that lambda. Don\'t do anything')


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
    
def send_msg(logger,msg):

    bot_name = os.environ['bot_name']

    topic = os.environ['filtered_error_topic']

    client = boto3.client('sns')

    print('Sending SNS message to %s' % topic)

    response = client.publish(
        TopicArn=topic,
        Message=msg,
        Subject='Lambda failure for %s bot' % bot_name
    )
    
    print('sns message sent')



