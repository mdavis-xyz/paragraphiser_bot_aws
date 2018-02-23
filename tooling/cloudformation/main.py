import boto3
from os import listdir
from os.path import isfile, join
import os
from tooling.colour import warn, error, err,emph, good
import pprint as pp
import time
import traceback as tb


class CloudFormation(object):

    def __init__(self,project_name,cloudformation_dir,code_bucket,stage):
        self.code_bucket = code_bucket
        self.cloudformation_dir = cloudformation_dir
        self.project_name = project_name
        self.stage = stage

    # versions is a list of versions of s3 objects for lambdas
    # list of {'name':lambda_name,'S3Version':version}
    def deploy(self,lambda_versions):

        assert(not any([x['S3Version'] == None for x in lambda_versions]))
        self.lambda_versions = lambda_versions

        client = boto3.client('cloudformation')

        stack_name_short = 'stack'
        fname = os.path.join('data','cloudformation','%s.yaml' % stack_name_short)

        if not os.path.isfile(fname):
            print(error('Error: I expect a yaml template at %s' % fname))

        self.stack_name = self.project_name + '-' + stage
        print('About to deploy file %s as stack %s' % (fname,self.stack_name))

        client = boto3.client('cloudformation')

        print('Checking template file %s' % fname)
        with open(fname,"rb") as f:
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
            },
            {
                'ParameterKey': 'stage',
                'ParameterValue': self.stage
            }
        ]

        # versions of S3 zips
        version_params = [{'ParameterKey':'%sS3Version' % v['name'], \
                           'ParameterValue':v['S3Version'] \
                          } \
                          for v in self.lambda_versions]
        assert(not any([x['ParameterValue'] == None for x in version_params]))
        params.extend(version_params)
        if any([x['ParameterValue'] == None for x in params]):
            print(error('Error: some parameters are None'))
            pp.pprint([x['ParameterKey'] for x in params if x['ParameterValue'] == None])
            exit(1)

        if self.stack_exists(self.stack_name):
            # update stack
            print('Stack %s already exists. Updating it' % self.stack_name)

            change_set_name = 'update-%d' % int(time.time())
            with open(fname,"rb") as f:
                print('Creating change set for %s' % self.stack_name)
                response = client.create_change_set(
                    StackName=self.stack_name,
                    TemplateBody=f.read().decode("utf-8"),
                    Parameters=params,
                    Capabilities=['CAPABILITY_NAMED_IAM'],
                    ChangeSetName=change_set_name,
                    Description='Update of %s' % fname,
                    ChangeSetType='UPDATE'
                )

                try:
                    waiter = client.get_waiter('change_set_create_complete')
                    waiter.wait(
                        StackName=self.stack_name,
                        ChangeSetName=change_set_name,
                        WaiterConfig={
                            'Delay': 10,
                            'MaxAttempts': 100
                        }
                    )
                except Exception as e:
                    response = client.describe_change_set(
                        ChangeSetName=change_set_name,
                        StackName=self.stack_name
                    )
                    pp.pprint(response)
                    expected = 'The submitted information didn\'t contain changes.'
                    if (response['Status'] == 'FAILED') and (expected in response['StatusReason']):
                        print('No changes to make to stack %s' % self.stack_name)
                        response = client.delete_change_set(
                            ChangeSetName=change_set_name,
                            StackName=self.stack_name
                        )
                        return()
                    pp.pprint(e)
                    print(err('Could not create change set %s for stack %s' % (change_set_name,self.stack_name)))
                    raise(e)

                print(good('change set created sucessfully for %s' % self.stack_name))

                print('Applying change set to stack %s' % self.stack_name)
                response = client.execute_change_set(
                    ChangeSetName=change_set_name,
                    StackName=self.stack_name,
                )

                waiter = client.get_waiter('stack_update_complete')
                waiter.wait(
                    StackName=self.stack_name,
                    WaiterConfig={
                        'Delay': 10,
                        'MaxAttempts': 100
                    }
                )

                print(good('Stack %s updated sucessfully' % self.stack_name))


        else:
            print('Stack %s does not exist. Creating it' % self.stack_name)
            # create stack
            with open(fname,"rb") as f:
                response = client.create_stack(
                    StackName=self.stack_name,
                    TemplateBody=f.read().decode("utf-8"),
                    Parameters=params,
                    Capabilities=['CAPABILITY_NAMED_IAM']
                )

            stack_id = response['StackId']

            waiter = client.get_waiter('stack_create_complete')
            waiter.wait(
                StackName=self.stack_name,
                WaiterConfig={
                    'Delay': 10,
                    'MaxAttempts': 20
                }
            )

            response = client.describe_stacks(StackName=self.stack_name)
            assert(len(response['Stacks']) == 1)
            assert(response['Stacks'][0]['StackName'] == self.stack_name)

            status = response['Stacks'][0]['StackStatus']

            if status in ['CREATE_COMPLETE']:
                print(good('Stack %s sucessfully created' % self.stack_name))
            else:
                print(error('Failed to create stack %s'))
                print(warn('status %s' % status))
                print('Check cloudformation in the browser to see what went wrong')
                # TODO: add option to delete stack
                exit(1)


    # returns true iff this stack exists
    # this function handles pagination by boto
    def stack_exists(self,stack_name):

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

        self.stack_names = [x['StackName'] for x in response['StackSummaries']]

        if self.stack_name in self.stack_names:
            return(True)

        while 'NextToken' in response:

            # get list of stacks to see if we need to create or update
            response = client.list_stacks(
                StackStatusFilter=filt,
                NextToken=response.NextToken
            )

            self.stack_names = [x['StackName'] for x in response['StackSummaries']]

            if self.stack_name in self.stack_names:
                return(True)

        return(False)
