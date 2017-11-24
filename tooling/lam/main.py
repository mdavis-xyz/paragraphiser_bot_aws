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

class Lam(object):

    def __init__(self,region, lambda_dir,lib_dir,data_dir,code_bucket):
        self.lambda_dir = lambda_dir
        self.lib_dir = lib_dir
        self.code_bucket = code_bucket
        self.data_dir = data_dir
        self.region = region

    def list_local_lambdas(self):
        subdirs = [f for f in listdir(self.lambda_dir) if isdir(join(self.lambda_dir, f))]
        return(subdirs)

    def the_lot(self,skip_zip, skip_build):
        lambdas = self.list_local_lambdas()

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

        steps = [
            {'step':'build',
             'function':self.build_one,
             'skip':skip_build},
            {'step':'zip',
             'function':self.zip_one,
             'skip':skip_zip},
            {'step':'upload',
             'function':self.upload_one,
             'skip':False}
        ]

        with Pool(3) as p:

            for step in steps:
                args = zip(
                        repeat(step['function']),
                        lambdas
                        )
                if step['skip']:
                    print(warn('Skipping %s of lambdas' % step['step']))
                else:
                    results = p.starmap(self.safe_fail, args)
                    results = [{'name':name,
                               'msg':result['msg'],
                               'Success':result['Success']}
                               for (name,result) in zip(lambdas,results)]

                    failed = [result for result in results if not result['Success']]
                    if len(failed) > 0:
                        print('\n' + '#'*20 + '\n')
                        print(failed[0]['msg'])
                        print('\n' + '#'*20 + '\n')
                        print(error('Unable to %s the following lambdas:' % step['step']))
                        print('   ' + '\n   '.join([x['name'] for x in failed]))
                        print('Output for %s of lambda %s shown above' % (step['step'],failed[0]['name']))
                        # pp.pprint(results)
                        exit(1)
                    else:
                        print(good('Successfully completed %s for all lambdas' % step['step']))


        print(good('Finished build, zip, test, upload'))

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

    def upload_one(self,name):
        zip_fname = os.path.join(self.lambda_dir,name,"lambda.zip")

        key = '%s-lambda.zip' % name

        client = boto3.client('s3')

        with open(zip_fname,"rb") as zip_f:
            response = client.put_object(
                ACL='bucket-owner-full-control',
                Body=zip_f.read(),
                Bucket=self.code_bucket,
                Key=key
            )

        ret = {'Success':True,'msg':'Uploaded sucessfully'}

        return(ret)
