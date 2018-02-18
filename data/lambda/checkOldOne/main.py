import praw
import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
import json
import common

def lambda_handler(event,contex):
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        return(common.unit_tests())
    else:
        print('Running main (non-test) handler')
        return(check_old(event))

def check_old(event):
    try:
        post_id = event['post_id']
    except Exception as e:
        print('event is type %s' % type(event))
        print('event:')
        pp.pprint(event)
        raise(e)

    print('Getting data from dynamodb')
    (data,post_id,comment_id) = load_post_info(post_id)

    print('Initialising praw')
    reddit = praw.Reddit('bot1')

    print('Getting submission %s' % post_id)
    submission = reddit.submission(id=post_id)

    print('Getting comment %s' % comment_id)
    comment = reddit.comment(id=comment_id)

    ret = common.update_reply(submission,comment,data)

    if ret != None:
        print('Updating comment %s for post %s' % (comment_id,post_id))
        print('New comment:')
        print(ret['updated_reply'])
        comment.edit(ret['updated_reply'])

    # now check votes
    print('Checking score')
    net_score = get_net_score(comment)
    raise(NotImplementedError)

# takes in a praw comment object
# adds up downvotes and upvotes
# but also 'good bot' and 'bad bot' comments
# and provides a net score
def get_net_score(comment):
    raise(NotImplementedError)

# takes in id of a post
# returns (data,post_id,comment_id)
# where data is a dict of what common.generate_reply returned for that post
def load_post_info(post_id):
    table_name = os.environ['post_history_table']
    client = boto3.client('dynamodb')

    print('Fetching dynamodb data for post %s' % post_id)

    response = client.get_item(
        TableName=table_name,
        Key={
            'post_id': {
                'S': post_id
            }
        },
        ConsistentRead=False, # cheaper
    )
    
    assert(post_id == response['Item']['post_id']['S'])
    comment_id = response['Item']['comment_id']['S']
    data_raw = response['Item']['data']['S']
    data = json.loads(data_raw)

    print('Dynamodb data for post %s: comment %s, data:' % (post_id,comment_id))
    pp.pprint(data)

    return (data,post_id,comment_id)
