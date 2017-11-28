from .lam import Lam
from .cloudformation import CloudFormation

class Project(object):
    # TODO: add boto credentials
    def __init__(self,project_name,region,lambda_dir,lib_dir,cloudformation_dir,data_dir,code_bucket):
        # self.lambda_dir = lambda_dir
        # self.lib_dir = lib_dir
        # self.cloudformation_dir = cloudformation_dir
        # self.code_bucket = code_bucket
        self.lam = Lam(region,lambda_dir,lib_dir,data_dir,code_bucket)
        self.cf = CloudFormation(project_name,cloudformation_dir,code_bucket)

    def the_lot(self,skip_zip, skip_build, skip_upload):
        self.lam.the_lot(skip_zip,skip_build, skip_upload)
        self.cf.deploy()
