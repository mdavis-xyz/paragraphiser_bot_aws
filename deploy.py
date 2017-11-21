#!/bin/python3.6

import argparse
import pprint as pp
from tooling.project import Project
# from tooling import lam
from tooling.colour import warn, error, emph, good
import sys
import os

root_dir = os.path.dirname(os.path.realpath(__file__))
lambda_dir = os.path.join(root_dir,'data','lambda')
lib_dir = os.path.join(root_dir,'data','lib')
cloudformation_dir = os.path.join(root_dir,'data','cloudformation')
data_dir = os.path.join(root_dir,'data')
code_bucket = 'paragraphiser_code'


def arguments(argv):
    parser = argparse.ArgumentParser(description="Push updates to AWS Deployment")
    # subparsers = parser.add_subparsers(dest="operation")
    # dp_parser = subparsers.add_parser("deploy", help="Update deployment")
    parser.add_argument('-d', '--deployment-name',
                           help="Name of the deployment (prod/dev)",
                           type=str,
                           required=True
                           )
    parser.add_argument('-r', '--skip-build',
                       help="Do not rebuild lambda environments",
                       action="store_true"
                       )

    parser.add_argument('-z', '--skip-zip',
                       help="Do not rezip lambdas",
                       action="store_true"
                       )

    args = parser.parse_args(argv[1:])
    return(args)

def main(argv):

    v = arguments(argv)

    print(emph('deploying %s' % v.deployment_name))
    prj = Project(lambda_dir,lib_dir,cloudformation_dir,data_dir,code_bucket)
    prj.lam.the_lot(v.skip_zip, v.skip_build)
    print(good('Done'))


if __name__ == "__main__":
    main(sys.argv)
