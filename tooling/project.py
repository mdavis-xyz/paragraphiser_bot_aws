from .lam import Lam

class Project(object):
    def __init__(self,lambda_dir,lib_dir,cloudformation_dir,data_dir,code_bucket):
        # self.lambda_dir = lambda_dir
        # self.lib_dir = lib_dir
        # self.cloudformation_dir = cloudformation_dir
        # self.code_bucket = code_bucket
        self.lam = Lam(lambda_dir,lib_dir,data_dir,code_bucket)
