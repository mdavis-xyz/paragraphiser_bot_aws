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

def list_local_lambdas(dir):
    subdirs = [f for f in listdir(dir) if isdir(join(dir, f))]
    return(subdirs)

def build_and_zip(lambda_dir, root_dir, skip_zip, skip_build):
    lambdas = list_local_lambdas(lambda_dir)

    steps = [
        {'step':'build',
         'function':build_one,
         'skip':skip_build},
        {'step':'zip',
         'function':zip_one,
         'skip':skip_zip}
    ]

    with Pool(3) as p:

        for step in steps:
            args = zip(
                    repeat(step['function']),
                    lambdas,
                    repeat(lambda_dir),
                    repeat(root_dir)
                    )
            if step['skip']:
                print(warn('Skipping %s of lambdas' % step['step']))
            else:
                results = p.starmap(safe_fail, args)
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

def safe_fail(func,name,lambda_dir,root_dir):
    try:
        ret = func(name,lambda_dir,root_dir)
    except Exception:
        msg = traceback.format_exc()
        ret = {'Success':False,'msg':msg}

    return(ret)

# lambda_dir is the root dir of all lambdas
# return value:
# {'Success':True|False,
#  'msg':str}
# msg won't be there if it was a success
def build_one(name,lambda_dir,root_dir):
    print('   Building env for lambda %s' % name)

    makefile_short = 'makeScript.sh'

    makefile_long = os.path.join(lambda_dir,name,makefile_short)

    if not os.path.isfile(makefile_long):
        msg = 'Error: makescript for lambda %s does not exist at %s' % (name,makefile_long)
        success = False
    else:
        # https://stackoverflow.com/a/4760517
        result = subprocess.run([makefile_long, root_dir],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=os.path.join(lambda_dir,name),
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

# lambda_dir is the root dir of all lambdas
def zip_one(name,lambda_dir,root_dir):
    print('   Zipping env for lambda %s' % name)
    ret = {'Success':False,'msg':'Not actually zipping'}
    assert(False)
    return(ret)
