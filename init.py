import boto3
from tooling.colour import warn, error, emph, good
import json
import getpass
import pprint as pp

def alias_name(project_name):
    return('alias/%s_praw' % project_name)

# data = {
#   'client_id':x,
#   'client_secret':x,
#   'password':x,
#   'username':x,
#   'user_agent':x
# }
def upload_praw_creds(project_name,data):
    init_key(project_name)

def read_and_encrypt_creds(project_name):
    # we only need to encrypt the password
    # but if we're going to be passing around all this data,
    # we may as well just include the plaintext username and stuff

    print('I\'m about to ask you for all the credentials for this reddit bot')
    print('Go to the reddit api site to get these')
    client_id=input('Please enter the client ID:\n')
    client_secret=getpass.getpass('Please enter the client Secret:\n')
    password=getpass.getpass('Please enter the user password:\n')
    password2=getpass.getpass('Please reenter the user password:\n')
    if password != password2:
        print('That 2nd password didn\'t match the first')
        print('Error: exiting')
        exit(1)
    username=input('Please enter the user name:\n')
    user_agent=input('Please enter the user agent:\n')
    print('Thanks')

    data = [
        {
            'filename':'client_id.txt',
            'content':client_id,
            'encrypt':False,
        },
        {
            'filename':'client_secret.dat', # binary
            'content':client_secret,
            'encrypt':True,
        },
        {
            'filename':'password.dat', # binary
            'content':password,
            'encrypt':True,
        },
        {
            'filename':'username.txt',
            'content':username,
            'encrypt':False,
        },
        {
            'filename':'user_agent.txt',
            'content':user_agent,
            'encrypt':False,
        }
    ]

    # write this stuff to file
    print('Writing that to file')
    for x in data:
        fname = 'data/credentials/' + x['filename']
        if x['encrypt']:
            mode = 'wb'
        else:
            mode = 'w'
        with open(fname,mode) as f:
            if x['encrypt']:
                data_to_write = encrypt(x['content'],project_name)
            else:
                data_to_write = x['content']
            f.write(data_to_write)

        # check it wrote properly
        if x['encrypt']:
            mode = 'rb'
        else:
            mode = 'r'
        with open(fname,mode) as f:
            written_data = f.read()
            if x['encrypt']:
                written_data = decrypt(written_data,project_name)

            assert(written_data == x['content'])
    print('Wrote that stuff to file')

# I'm not sure whether this is sent plaintext over the internet
# to AWS servers, then encrypted.
# It might be. But since this is only a reddit bot, I CBF using
# double keys
# plaintext is a string
def encrypt(plaintext,project_name):
    client = boto3.client('kms')
    response = client.encrypt(
        KeyId=alias_name(project_name),
        Plaintext=str.encode(plaintext),
    )

    ciphertext = response['CiphertextBlob']

    return(ciphertext)

def decrypt(ciphertext,project_name):
    client = boto3.client('kms')

    response = client.decrypt(
        CiphertextBlob=ciphertext,
    )

    decrypted = response['Plaintext'].decode()

    return(decrypted)


def test_encrypt_decrypt(project_name):
    test_payload = '123$%^'
    print('original: %s' % test_payload)
    client = boto3.client('kms')
    response = client.encrypt(
        KeyId=alias_name(project_name),
        Plaintext=str.encode(test_payload),
    )

    ciphertext = response['CiphertextBlob']
    print('ciphertext: %s' % ciphertext)

    response = client.decrypt(
        CiphertextBlob=ciphertext,
    )

    decrypted = response['Plaintext'].decode()
    print('decrypted: %s' % decrypted)

    assert(test_payload == decrypted)

def init_key(project_name):
    print('creating key')
    client = boto3.client('kms')

    response = client.create_key(
        Description='Key for encrypting the reddit credentials for %s' % project_name,
        KeyUsage='ENCRYPT_DECRYPT',
        Origin='AWS_KMS',
        Tags=[
            {
                'TagKey': 'project',
                'TagValue': project_name
            },
        ]
    )

    assert(response['KeyMetadata']['KeyState']=='Enabled')

    keyId = response['KeyMetadata']['KeyId']


    response = client.create_alias(
        AliasName=alias_name(project_name),
        TargetKeyId=keyId
    )

    print(good('finished creating key under alias %s' % alias_name(project_name)))

# init_key('paragraphiser')
print('Starting __main__')
read_and_encrypt_creds('paragraphiser')
print('FInished __main__')
# test_encrypt_decrypt('paragraphiser')
