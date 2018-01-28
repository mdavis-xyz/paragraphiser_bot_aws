import boto3
from os import listdir
from os.path import isfile, join
import os
from tooling.colour import warn, error, emph, good
import pprint as pp


class CloudFormation(object):

    def __init__(self,project_name,cloudformation_dir,code_bucket):
        self.code_bucket = code_bucket
        self.cloudformation_dir = cloudformation_dir
        self.project_name = project_name

    def deploy(self):
        client = boto3.client('cloudformation')

        yamls = [f for f in listdir(self.cloudformation_dir)
                 if isfile(join(self.cloudformation_dir, f))]

        print('I found %d yaml files' % len(yamls))

        # TODO: multithread, or deal with dependencies between stacks
        for fname in yamls:
            self.deploy_one(fname)

        print(good('Finished deploying cloudformation stacks'))

    # fname is short name (excludes directory)
    def deploy_one(self,fname):
        assert(fname.endswith('.yaml'))
        fname_body = fname[0:len(fname)-len('.yaml')]
        stack_name = self.project_name + '-' + fname_body
        print('About to deploy file %s as stack %s' % (fname,stack_name))

        client = boto3.client('cloudformation')

        print('Checking template file %s' % fname)
        with open(join(self.cloudformation_dir,fname),"rb") as f:
            response = client.validate_template(
                TemplateBody=f.read().decode("utf-8")
            )

        print(good('Template %s is valid' % fname))

        params = [
            {
                'ParameterKey': 'botname',
                'ParameterValue': self.project_name
            },
            {
                'ParameterKey': 'codebucket',
                'ParameterValue': self.code_bucket
            }
        ]

        if stack_exists(stack_name):
            # update stack
            print('Stack %s already exists. Updating it' % stack_name)
            assert(False) # TODO
        else:
            print('Stack %s does not exist. Creating it' % stack_name)
            # create stack
            with open(join(self.cloudformation_dir,fname),"rb") as f:
                response = client.create_stack(
                    StackName=stack_name,
                    TemplateBody=f.read().decode("utf-8"),
                    Parameters=params,
                    Capabilities=['CAPABILITY_NAMED_IAM']
                )

            stack_id = response['StackId']

            waiter = client.get_waiter('stack_create_complete')
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={
                    'Delay': 10,
                    'MaxAttempts': 20
                }
            )

            response = client.describe_stacks(StackName=stack_name)
            assert(len(response['Stacks']) == 1)
            assert(response['Stacks'][0]['StackName'] == stack_name)

            status = response['Stacks'][0]['StackStatus']

            if status in ['CREATE_COMPLETE']:
                print(good('Stack %s sucessfully created' % stack_name))
            else:
                print(error('Failed to create stack %s'))
                print(warn('status %s' % status))
                print('Check cloudformation in the browser to see what went wrong')
                # TODO: add option to delete stack
                exit(1)


# returns true iff this stack exists
# this function handles pagination by boto
def stack_exists(stack_name):

    client = boto3.client('cloudformation')

    filt = [
        'CREATE_IN_PROGRESS',
        # 'CREATE_FAILED',
        'CREATE_COMPLETE',
        'ROLLBACK_IN_PROGRESS',
        'ROLLBACK_FAILED',
        'ROLLBACK_COMPLETE',
        'DELETE_IN_PROGRESS',
        'DELETE_FAILED',
        # 'DELETE_COMPLETE',
        'UPDATE_IN_PROGRESS',
        'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
        'UPDATE_COMPLETE',
        'UPDATE_ROLLBACK_IN_PROGRESS',
        'UPDATE_ROLLBACK_FAILED',
        'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS',
        'UPDATE_ROLLBACK_COMPLETE',
        'REVIEW_IN_PROGRESS',
    ]

    # get list of stacks to see if we need to create or update
    response = client.list_stacks(
        StackStatusFilter=filt
    )

    stack_names = [x['StackName'] for x in response['StackSummaries']]

    if stack_name in stack_names:
        return(True)

    while 'NextToken' in response:

        # get list of stacks to see if we need to create or update
        response = client.list_stacks(
            StackStatusFilter=filt,
            NextToken=response.NextToken
        )

        stack_names = [x['StackName'] for x in response['StackSummaries']]

        if stack_name in stack_names:
            return(True)

    return(False)
