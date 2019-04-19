#!/bin/python3.6

import argparse
import pprint as pp
from tooling.project import Project
# from tooling import lam
from tooling.colour import warn, error, emph, good
import sys
import os



def arguments(argv):
    parser = argparse.ArgumentParser(description="Push updates to AWS Deployment")
    # subparsers = parser.add_subparsers(dest="operation")
    # dp_parser = subparsers.add_parser("deploy", help="Update deployment")
    parser.add_argument('-s', '--stage-name',
                           help="Name of the stage (e.g. prod, dev)",
                           type=str,
                           required=False,
                           default='prod'
                           )
    parser.add_argument('-b', '--skip-build',
                       help="Do not rebuild lambda environments",
                       action="store_true"
                       )

    parser.add_argument('-z', '--skip-zip',
                       help="Do not rezip lambdas",
                       action="store_true"
                       )


    parser.add_argument('-u', '--skip-zip-upload',
                       help="Do not upload lambda zips",
                       action="store_true"
                       )


    parser.add_argument('-t', '--skip-lambda-test',
                       help="Do not test lambdas",
                       action="store_true"
                       )

    args = parser.parse_args(argv[1:])
    return(args)

def main(argv):

    v = arguments(argv)

    if v.skip_zip_upload and not v.skip_build:
        print(error('Error: You\'ve asked me to skip the upload, but you still want me to rebuild the virtual environments?'))
        print(error('The new virtual environments would not be uploaded'))
        print(error('If skipping upload, you must also skip build'))
        exit(1)
    elif v.skip_zip_upload and not v.skip_zip:
        print(error('Error: You\'ve asked me to skip the upload, but you still want me to zip the local lambda files?'))
        print(error('The new zips would not be uploaded'))
        print(error('If skipping upload, you must also skip build'))
        exit(1)
    elif v.skip_zip and not v.skip_build:
        print(error('Error: You\'ve asked me to skip the zipping of lambdas, but you still want me rebuild the virtual environment?'))
        print(error('The zip will still contain the previous virtual environment'))
        print(error('If skipping zipping, you must also skip build'))
        exit(1)

    print(emph('deploying %s' % v.stage_name))

    root_dir = os.path.dirname(os.path.realpath(__file__))
    lambda_dir = os.path.join(root_dir,'data','lambda')
    lib_dir = os.path.join(root_dir,'data','lib')
    cloudformation_dir = os.path.join(root_dir,'data','cloudformation')
    data_dir = os.path.join(root_dir,'data')
    project_name = 'reddit-amp-bot'
    code_bucket = '%s-code' % project_name
    region = 'ap-southeast-2'

    prj = Project(project_name,region,lambda_dir,lib_dir,cloudformation_dir,data_dir,code_bucket,v.stage_name)
    prj.the_lot(v.skip_zip, v.skip_build, v.skip_zip_upload,v.skip_lambda_test)
    print(good('Done'))


if __name__ == "__main__":
    main(sys.argv)
