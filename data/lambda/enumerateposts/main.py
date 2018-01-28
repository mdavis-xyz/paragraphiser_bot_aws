import json
import logging
logger = None # will be initialised in handler, then used as global var
import pprint as pp
import praw
import boto3

# secret stuff
# https://stackoverflow.com/questions/29372278/aws-lambda-how-to-store-secret-to-external-api#29600478

def read_single_cred_file(filename,encrypt):
    if encrypt:
        mode = 'rb'
    else:
        mode = 'r'

    with open('credentials/' + filename,mode) as f:
        data = f.read()
        if encrypt:
            data = decrypt(data)

    return(data)


def decrypt(ciphertext):
    client = boto3.client('kms')

    response = client.decrypt(
        CiphertextBlob=ciphertext,
    )

    decrypted = response['Plaintext'].decode()

    return(decrypted)


def init_praw():

    logger.info('reading in praw credentials from files')

    client_id = read_single_cred_file('client_id.txt',False)
    client_secret = read_single_cred_file('client_secret.dat',True)
    password = read_single_cred_file('password.dat',True)
    username = read_single_cred_file('username.txt',False)
    user_agent = read_single_cred_file('user_agent.txt',False)

    logger.info('finished reading in praw credentials from files')
    reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                password=password,
                user_agent=user_agent,
                username=username
             )
    logger.info('sucessfully initialised reddit instance')
    logger.info('about to try doing that incorrectly')
    reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                password=password,
                user_agent=user_agent,
                username=username + 'asd' # wrong
             )
    logger.info('ok, that didn\'t raise an exception')
    assert(False)

def execute(event,context):
    return("Not yet implemented")

def unit_test(event,context):
    global logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.info('Running unit tests')
    reddit = init_praw()
    print("Sucessfully created reddit instance")


def lambda_handler(event, context):
    global logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logger.info('event: ' + str(event))

    reddit = init_praw()

    if (event != None) and \
       ('Test Run' in event) and \
       (event['Test Run'] == True):
           ret_val = unit_test(event,context)
    else:
        ret_val = real(event,context)

    return(ret_val)
