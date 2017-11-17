#!/bin/python3.6

import argparse
import pprint as pp
from tooling import lam
from tooling.colour import warn, error, emph, good
import sys
import os

this_dir = os.path.dirname(os.path.realpath(__file__))
lambda_dir = os.path.join(this_dir,'lambda')
lib_dir = os.path.join(this_dir,'lib')

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
    lam.build_and_zip(lambda_dir, lib_dir, v.skip_zip, v.skip_build)
    print(good('Done'))


if __name__ == "__main__":
    main(sys.argv)
