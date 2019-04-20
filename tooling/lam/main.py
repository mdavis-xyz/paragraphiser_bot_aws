import boto3
from os import listdir
from os.path import isdir, join
import os
from multiprocessing import Pool
from itertools import repeat
from tooling.colour import warn, error, emph, good
import subprocess
import traceback
import pprint as pp
import zipfile
import json
import base64
import sys

class Lam(object):

    def __init__(self,project_name,region, lambda_dir,lib_dir,data_dir,code_bucket,stage):
        self.project_name = project_name
        self.lambda_dir = lambda_dir
        self.lib_dir = lib_dir
        self.code_bucket = code_bucket
        self.data_dir = data_dir
        self.region = region
        self.stage = stage

    def list_local_lambdas(self):
        subdirs = [f for f in listdir(self.lambda_dir) if isdir(join(self.lambda_dir, f))]
        return(subdirs)

    # build, zip, upload
    def the_lot(self,skip_zip, skip_build, skip_upload):


        if skip_build:
            print(warn('Skipping building of lambdas'))
        else:
            self.do_work('build',self.build_one)

        if skip_zip:
            print(warn('Skipping zipping of lambdas'))
        else:
            self.do_work('zip',self.zip_one)


        if skip_upload:
            print(warn('Skipping uploading of lambdas'))
            print('using latest versions of zips currently in S3')
            lambdas = self.list_local_lambdas()
            with Pool(3) as p:
                versions_raw = p.map(self.latest_version,lambdas)
            versions = [{'name':lam,'S3Version':v} for (lam,v) in zip(lambdas,versions_raw)]
        else:

            # check code bucket exists

            client = boto3.client('s3')
            response = client.list_buckets()
            buckets = [b['Name'] for b in response['Buckets']]
            if self.code_bucket not in buckets:
                print('Bucket %s does not exist, creating it now' % self.code_bucket)
                response = client.create_bucket(
                ACL='private',
                Bucket=self.code_bucket,
                CreateBucketConfiguration={
                'LocationConstraint': self.region
                }
                )

                # enable versioning
                response = client.put_bucket_versioning(
		    Bucket=self.code_bucket,
		    VersioningConfiguration={
			'MFADelete': 'Disabled',
			'Status': 'Enabled'
		    }

		) 

            # list of {'name':x,'return_val':s3version}
            results = self.do_work('upload',self.upload_one)
            versions = [{'name':x['name'],'S3Version':x['return_val']} for x in results]

        assert(not any([x['S3Version'] == None for x in versions]))
        self.versions = versions

    def test_lambdas(self,skip_test,stack_name):
        if skip_test:
            print(warn('Skipping testing of lambdas'))
        else:
            self.stack_name = stack_name
            self.do_work('test',self.test_one)


    # step is a string
    # function is a function to which we call
    def do_work(self,step,function):
        lambdas = self.list_local_lambdas()

        with Pool(3) as p:

            args = zip(
                    repeat(function),
                    lambdas
                    )

            print('About to %s lambdas' % step)
            results = p.starmap(self.safe_fail, args)
            results = [{'name':name,
                       'msg':result['msg'],
                       'Success':result['Success'],
                       'return_val':None if ('return_val' not in result) else result['return_val']
                       }
                       for (name,result) in zip(lambdas,results)]



            failed = [result for result in results if not result['Success']]
            if len(failed) > 0:
                print('\n' + '#'*20 + '\n')
                print(failed[0]['msg'])
                print('\n' + '#'*20 + '\n')
                print(error('Unable to %s the following lambdas:' % step))
                print('   ' + '\n   '.join([x['name'] for x in failed]))
                print('Output for %s of lambda %s shown above' % (step,failed[0]['name']))
                # pp.pprint(results)
                exit(1)
            else:
                print(good('Successfully completed %s for all lambdas' % step))
                return(results)

    def safe_fail(self,func,name):
        try:
            ret = func(name)
        except Exception:
            msg = traceback.format_exc()
            ret = {'Success':False,'msg':msg}

        return(ret)

    # return value:
    # {'Success':True|False,
    #  'msg':str}
    # msg won't be there if it was a success
    def build_one(self,name):
        this_lambda_dir = os.path.join(self.lambda_dir,name)
        print('   Building env for lambda %s' % name)

        makefile_short = 'makeScript.sh'

        makefile_long = os.path.join(this_lambda_dir,makefile_short)

        if not os.path.isfile(makefile_long):
            msg = 'Error: makescript for lambda %s does not exist at %s' % (name,makefile_long)
            success = False
        else:
            # https://stackoverflow.com/a/4760517
            result = subprocess.run([makefile_long, self.data_dir],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    cwd=this_lambda_dir,
                                    encoding='utf-8',
                                    bufsize=1)
            success = (result.returncode == 0)
            msg = result.stdout #.decode('utf-8')
            msg += result.stderr
            msg += '\n\nmake script returned %s' % str(result.returncode)

        ret = {
            'Success':success,
            'msg':msg
        }

        print('   Finished building %s' % name)

        return(ret) # success

    def zip_one(self,name):
        # https://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html
        this_lambda_dir = os.path.join(self.lambda_dir,name)
        zip_fname = os.path.join(this_lambda_dir,"lambda.zip") # TODO: put artefacts somewhere else
        print('   Zipping env for lambda %s' % name)
        with zipfile.ZipFile(zip_fname, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(os.path.join(this_lambda_dir,"main.py"), "main.py")
            # TODO: deal with multiple files in root directory
            incl_dir = os.path.join(this_lambda_dir,"include")
            for dirname, subdirs, files in os.walk(incl_dir):
                # print('There are %d files in include folder' % len(files))
                for filename in files:
                    absname = os.path.abspath(os.path.join(dirname, filename))
                    path_in_zip = filename
                    # print('Adding file %s to zip %s' % (absname,path_in_zip))
                    zf.write(absname, path_in_zip)
            for lib in ['lib','lib64']:
                # TODO: don't hard code 3.6
                for package_dir_name in ['site-packages', 'dist-packages']:
                    package_dir = os.path.join(this_lambda_dir,'env',lib,'python3.6',package_dir_name)
                    for dirname, subdirs, files in os.walk(package_dir):
                        for filename in files:
                            absname = os.path.abspath(os.path.join(dirname, filename))
                            arcname = absname[len(package_dir) + 1:]
                            zf.write(absname, arcname)

        # # TODO: finish writing limit check
        # print('\n'.join(dir(zipfile.ZipInfo(zip_fname))))
        # zip_size = zipfile.ZipInfo(zip_fname).compress_size
        #
        # size_limit_compressed =  52428800 # 50MB, must be less than, not equal
        # size_limit_uncompressed = 262144000 # 250MB must be less than, not equal
        #
        # # assert(False)
        #
        # print('   zipped lambda %s to size %d' % (name,zip_size))
        #
        # if zip_size >= lambda_size_limit:
        #     ret = {'Success':False,'msg':'Zip too large. Is %d bytes, should be < %d' % (zip_size,lambda_size_limit)}
        # else:
        #     ret = {'Success':True,'msg':'Zipped successfully'}

        ret = {'Success':True,'msg':'Zipped successfully'}

        # TODO: add flush and stuff
        # TODO: delete __init__.py if not needed

        return(ret)

    def latest_version(self,lambda_name):
        key = self.s3_key(lambda_name)

        # s3 = boto3.resource('s3')
        # object_summary = s3.ObjectSummary(self.code_bucket,key)
        # version = object_summary.Version()

        client = boto3.client('s3')

        print('Getting version info for zip %s from S3' % lambda_name)
        response = client.list_object_versions(
            Bucket=self.code_bucket,
            Prefix=key,
            # KeyMarker=key, # won't work if we just list versions for one key
            MaxKeys=1 # deleted keys show up for some reason
        )

        if 'Versions' not in response:
            pp.pprint(response)

        versions = response['Versions']

        i = 0

        while(response['IsTruncated']):
            # pp.pprint(response)
            i = i + 1
            if (i % 5) == 0:
                sys.stdout.write('.') # print('.') but without a newline
                sys.stdout.flush()
            # print('Getting next page of version info for zip %s from S3' % lambda_name)
            assert('NextVersionIdMarker' in response)
            response = client.list_object_versions(
                Bucket=self.code_bucket,
                KeyMarker=response['NextKeyMarker'],
                MaxKeys=1, # deleted keys show up for some reason
                VersionIdMarker=response['NextVersionIdMarker'],
                Prefix=key
            )
            versions.extend(response['Versions'])

        print('Got all versions, now finding the most recent for %s' % key)
        version_ids = [v['VersionId'] for v in versions if (v['IsLatest'] and (v['Key'] == key))]
        if len(version_ids) == 0:
            print(error('Couldn\'t find zip %s in S3 bucket %s. Try again without -u' % (key,self.code_bucket)))
            exit(1)
        elif len(version_ids) != 1:
            print('Versions:')
            pp.pprint(versions)
            print('Key: %s' % key)
            print('version_ids:')
            pp.pprint(version_ids)

        assert(len(version_ids) == 1)

        version = version_ids[0]
        print('Latest version of zip for %s is %s' % (lambda_name,version))

        assert(version != None)

        return(version)

    def s3_key(self,lambda_name):
        return('%s/%s.zip' % (self.stage,lambda_name))

    def upload_one(self,name):
        zip_fname = os.path.join(self.lambda_dir,name,"lambda.zip")

        key = self.s3_key(name)

        s3 = boto3.resource('s3')
        obj = s3.Object(self.code_bucket,key)

        with open(zip_fname,"rb") as zip_f:
            print('   about to upload zip of %s to S3' % name)
            response = obj.put(
                ACL='bucket-owner-full-control',
                Body=zip_f.read()
            )
            print('   uploaded zip of %s to S3' % name)
            obj.reload()

            if 'VersionId' in response:
                version = response['VersionId']
            elif obj.version_id:
                version = obj.version_id
            else:
                print(warn("Failed to get version id of %s zip S3 obj" % name))
                etag = response['ETag']

                obj = s3.Object(self.code_bucket, key)
                obj.load()
                assert(obj.e_tag == etag)
                assert(obj.version_id)
                version = obj.version_id

            assert(version)
            assert(type(version) == type(''))

        ret = {'Success':True,'msg':'Uploaded sucessfully','return_val':version}

        return(ret)


    # takes in a short lambda name
    # returns the long name of the deployed lambda
    # which includes stack name and a random string
    def local_name_to_remote(self,short):
        client = boto3.client('cloudformation')
        response = client.describe_stack_resource(
            StackName=self.stack_name,
            LogicalResourceId=short
        )

        long_name = response['StackResourceDetail']['PhysicalResourceId']

        #print('   Long name for lambda %s is %s' % (short,long_name))
        return(long_name)

    def test_one(self,name):
        print('   invoking test lambda for %s' % name)
        client = boto3.client('lambda')
        remote_name = self.local_name_to_remote(name)
        # https://boto3.readthedocs.io/en/docs/reference/services/lambda.html#Lambda.Client.invoke
        response = client.invoke(
            FunctionName=remote_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({'unitTest':True}).encode(),
            LogType='Tail'
        )

        #pp.pprint(response)

        if (response['StatusCode'] == 200):

            return_val = json.load(response['Payload'])

            if not ((return_val != None) and \
                    ('errorMessage' in return_val)):
                ret = {'Success':True,'msg':'Tested %s sucessfully' % name}
                return(ret)

        logs = base64.b64decode(response['LogResult']).decode('utf-8')
        msg = logs
        msg += '\nStatus Code:%d'  % (response['StatusCode'])
        if 'PayLoad' in response:
            return_val = json.load(response['Payload'])
            msg += '\nReturned Value:\n%s' % return_val
        if 'FunctionError' in response:
            msg += '\nFunction Error:%s'  % (response['FunctionError'])

        msg += '\nTest failed'
        ret = {'Success':False,'msg':msg}

        return(ret)

    # short name is just the name of the lambda itself
    def lambda_name(self,short_name):
        lambda_name = '%s-%s' % (self.project_name,short_name)
        return(lambda_name)

    # check whether a lambda function exists under a particular name
    def lambda_exists(self,name):
        client = boto3.client('lambda')
        response = client.list_functions()
        while 'NextMarker' in response:
            functions = [x['FunctionName'] for x in response['Functions']]
            # pagination
            if name in functions:
                return(True)
            response = client.list_functions(marker=response['NextMarker'])

        functions = [x['FunctionName'] for x in response['Functions']]
        return(name in functions)

    # delete old versions of the zips in S3
    def cleanup(self):
        print('Deleting old versions of zips from S3')
        prefix=self.stage + '/'
        objs = self.list_all_zips(prefix)

        print('There are %d zips in S3 %s/%s/' % (len(objs),self.code_bucket,self.stage))

        lambdas = self.list_local_lambdas()
        keys_to_keep = ['%s/%s.zip' % (self.stage,lam) for lam in lambdas]

        dont_del = lambda item: item['IsLatest'] and item['Key'] in keys_to_keep

        objs = [obj for obj in objs if not dont_del(obj)]

        print('About to delete %d zips' % len(objs))

        #self.delete_versions(objs)
        for obj in objs:
            self.delete_version(obj)

    # takes in a list of {'Key':fullkey,'VersionId':s3version,'IsLatest':bool}
    # deletes it
    def delete_version(self,obj):
        client = boto3.client('s3')

        print('Deleting key %s version %s from S3 bucket %s' % (obj['Key'],obj['VersionId'],self.code_bucket))

        response = client.delete_object(
            Bucket=self.code_bucket,
            Key=obj['Key'],
            VersionId=obj['VersionId']
        )

    # takes in a list of {'Key':fullkey,'VersionId':s3version,'IsLatest':bool}
    # deletes those objects from S3 in batch
    def delete_versions(self,objs):
        client = boto3.client('s3')

        # batch delete works on up to 1000 items
        MAX_ITEMS=1000 

        to_delete = [{'Key':x['Key'],'VersionId':x['VersionId']} for x in objs[::MAX_ITEMS]]

        print('About to delete the following from S3')
        pp.pprint(objs[::MAX_ITEMS])
        response = client.delete_objects(
            Bucket=self.code_bucket,
            Delete={
                'Objects': to_delete,
                'Quiet': False
            },
            MFA='string',
            RequestPayer='requester'
        )

        # delete the remainder if there were too many
        self.delete_versions(objs[MAX_ITEMS::])


    # returns a list of {'Key':fullkey,'VersionId':s3version,'IsLatest':bool}
    # for objects in the s3 directory for this stage
    # handles pagination
    # includes every version of each file
    # with the latest version of the zips still used excluded
    def list_all_zips(self,prefix):
        client = boto3.client('s3')
        response = client.list_object_versions(
            Bucket=self.code_bucket,
            MaxKeys=100,
            Prefix=prefix
        )

        items = response['Versions']

        while response['IsTruncated']:
            response = client.list_object_versions(
                Bucket=self.code_bucket,
                MaxKeys=100,
                Prefix=prefix,
                KeyMarker=response['NextKeyMarker'],
                VersionIdMarket=response['NextVersionIdMarker']
            )
            items.extend(response['Versions'])

        return(items)
