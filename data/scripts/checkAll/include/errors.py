# import praw
import os
import pprint as pp
import boto3
import traceback as tb
import json

def capture_err(func,event,context):
    try:
        func(event,context)
    except Exception as e:
        print('ERROR captured')
        traceback_str = tb.format_exc()
        payload = {
            'lambda_name': os.environ['AWS_LAMBDA_FUNCTION_NAME'],
            'traceback': traceback_str,
            'error_type': 'direct invocation from traceback'
        }
        handler_lambda_arn = os.environ['errorHandlerArn']
        print('Sending payload to error handler lambda:\n%s' % str(payload))
        client = boto3.client('lambda')
        response = client.invoke(
            FunctionName=handler_lambda_arn,
            InvocationType='Event',
            Payload=json.dumps(payload).encode(),
        )
        raise(e)
