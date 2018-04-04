import praw
import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
import json
import common
import re

def lambda_handler(event,context):
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        common.unit_tests()
        test_regex()
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

    if net_score < 0:
        print('Comment %s has negative reaction' % comment.id)
        send_alert(comment,net_score)

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

# takes in a praw comment object
# adds up downvotes and upvotes
# but also 'good bot' and 'bad bot' comments
# and provides a net score
def get_net_score(comment):
    net = net_comment_responses(comment) + comment.ups - comment.downs
    return(net)

# takes in a comment
# for each reply, check if it says 'good bot' or 'bad bot'
# sum all those up (good = 1, bad = -1, neither = 0)
def net_comment_responses(comment):
    # the praw library returns all replies (e.g. replies to replies)
    comment.refresh()
    forest = comment.replies
    #forest.refresh()
    replies = [r for r in forest if r.parent() == comment.id]

    net = sum([eval_reply(r.body) for r in replies])

    return(net)

# check if a comment says 'good bot' or 'bad bot'
# account for case sensitivity and stuff
def eval_reply(text):

    # not sure if regex can deal with multiline
    text = text.replace('\n',' ')

    contains_good = bool(re.compile('.*good\s+bot.*',re.IGNORECASE).match(text))
    contains_bad = bool(re.compile('.*bad\s+bot.*',re.IGNORECASE).match(text))

    if contains_good and contains_bad:
        return(0)
    elif contains_good:
        return(1)
    elif contains_bad:
        return(-1)
    else:
        return(0)

def test_regex():
    print('Testing regex stuff')
    inputs = [
        ('good bot',1),
        ('GoOd Bot!',1),
        ('good bot good bot!',1), # not 2
        ('GoOd  Bot!',1),
        ('This is a good bot',1),
        ('Bad bot!',-1),
        ('Good bot or bad bot? I don\'t know',0)
    ]

    for (text,expected) in inputs:
        print('Testing regex for: "%s"' % text) 
        ret = eval_reply(text)
        if ret != expected:
            print('Expected: %s' % expected)
            print('Got: %s' % ret)
            print('Input: %s' % text)
        assert(ret == expected)
        print('test passed for "%s"' % text)

# send an SNS message to the relevant topic
def send_alert(comment,net_score):
    comment_url = 'reddit.com' + comment.permalink
    bot_name = os.environ['bot_name']
    msg = 'Warning: Your %s bot posted comment %s which has been voted into negative territory.' % (bot_name,comment.id)
    msg += '\n\n' + comment_url

    topic = os.environ['filtered_error_topic']

    client = boto3.client('sns')

    print('Sending SNS message to %s' % topic)

    response = client.publish(
        TopicArn=topic,
        Message=msg,
        Subject='Comment by %s bot voted negative' % bot_name
    )
    
    print('sns message sent')
