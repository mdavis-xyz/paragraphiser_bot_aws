import praw
import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
import json
import common

SEC_PER_MIN = 60
MIN_PER_H = 60
SEC_PER_H = SEC_PER_MIN * MIN_PER_H
H_PER_DAY = 24
MIN_PER_DAY = H_PER_DAY * MIN_PER_H
SEC_PER_DAY = H_PER_DAY * SEC_PER_H


# Apparently you can't have a dynamo table with just a
# sort key. So I'll add a hash key, which will only have
# one value of 0
hash_key_val = 'data' 


def lambda_handler(event,contex):
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        common.unit_tests()
        look_for_new(dry_run=True)
    else:
        print('Running main (non-test) handler')
        return(look_for_new())

def look_for_new(dry_run=False):
    print('Looking for new posts')

    reddit = praw.Reddit('bot1')
    subreddits = ['bottest']

    for sub_name in subreddits:
        print('subreddit: ' + sub_name)
        check_subreddit(sub_name,dry_run=dry_run)

def check_subreddit(sub_name,dry_run=False):

    skipped_posts = 0
    limit = int(os.getenv('num_to_scan',50))

    reddit = praw.Reddit('bot1')
    subreddit = reddit.subreddit(sub_name)
    submissions = subreddit.hot(limit=limit)

    print('Looking at the hottest %d posts' % limit)

    submissions = [s for s in submissions if s.is_self]
    print('Only %d of the hottest are self posts' % len(submissions))

    # eligible bodies
    submissions = [s for s in submissions if common.eligible_body(s.selftext)]
    print('Only %d of the hottest self posts have an eligible body' % len(submissions))

    if len(submissions) > 0:


        post_ids = [s.id for s in submissions]

        posts_replied_to = keys_exist(post_ids)

        # only keep the expressions we haven't seen before
        submissions = [s for s in submissions if s.id not in posts_replied_to]

        print('Only %d of the hottest self posts have an eligible body and I haven\'t replied to them yet' % len(submissions))

        if len(submissions) > 0:

            replies = [common.generate_reply(s) for s in submissions]


            if dry_run:
                print('I would reply to the following posts:')
            else:
                print('About to reply to the following posts:')
            print('\n   '+ '\n   '.join([s.id for s in submissions]))

            if not dry_run:
                for (msg,s) in zip(replies,submissions):
                    try:
                        print('Replying to post %s' % s.id)
                        s.reply(msg)
                    except praw.exceptions.APIException as e:
                        if 'ratelimit' in e.message.lower():
                            print('Hmm, I\'m being rate limited. Waiting 60 seconds')
                            time.sleep(60)
                            print('Waking up, trying again')
                            s.reply(msg)
                    time.sleep(10) # praw isn't handling throttling as well as it should

                save_initial(replies,submissions)
                schedule_checks([s.id for s in submissions])

    if dry_run:
        print('Would have replied to %d posts, skipped %d posts' % (len(submissions),limit-len(submissions)))
    else:
        print('Replied to %d posts, skipped %d posts' % (len(submissions),limit-len(submissions)))

def save_initial(replies,submissions):
    table_name = os.environ['post_history_table']
    client = boto3.client('dynamodb')

    now = int(time.time())

    for (r,s) in zip(replies,submissions):
        item = {
            'post_id':{'S':s.id},
            'inital_reply':{'S':r},
            'initial_post_body':{'S':s.selftext},
            'initial_reply_time':{'N':str(now)} # boto requires numbers as strings
        }

        print('Saving initial post for %s' % s.id)

        response = client.put_item(
            TableName=table_name,
            Item=item,
        )

        print('Saved initial post for %s' % s.id)


# takes in a list of post ids
# returns a list which is a subset of that list
# containing the post ids which appear as a primary key
# in the table_name dynamodb table
#
# this function handles pagination
def keys_exist(ids):
        table_name = os.environ['post_history_table']
        client = boto3.client('dynamodb')
        keys = [{'post_id': {'S': id}} for id in ids]
        try:
            response = client.batch_get_item(
                RequestItems={
                    table_name: {
                        'Keys': keys,
                        'AttributesToGet': [
                            'post_id'
                        ],
                        'ConsistentRead': False,
                    }
                },
                ReturnConsumedCapacity='NONE'
            )
        except client.exceptions.ResourceNotFoundException:
            print('Table %s doesn\'t exist yet' % table_name)
            return([])


        items = response['Responses'][table_name]

        pp.pprint(items)

        if ('UnprocessedKeys' in response) and (response['UnprocessedKeys'] != {}):
            print('Here was the response:')
            pp.pprint(response)
            print('TODO: implement pagination')
            raise(NotImplementedError)

        items = [x['post_id']['S'] for x in items]
        return(items)

def schedule_checks(post_ids):


    # minutes
    delays = [
       1, # 1 minute
       2,
       4,
       7,
       10,
       20,
       30,
       45,
       1*MIN_PER_H, # 1 hour
       1.5*MIN_PER_H,   
       2*MIN_PER_H,
       3*MIN_PER_H,
       4*MIN_PER_H,
       5*MIN_PER_H,
       7*MIN_PER_H,
       10*MIN_PER_H,
       14*MIN_PER_H,
       18*MIN_PER_H,
       1*MIN_PER_DAY, # 1 day
       1.5*MIN_PER_DAY,
       2*MIN_PER_DAY,
       3*MIN_PER_DAY,
       5*MIN_PER_DAY,
       8*MIN_PER_DAY,  
       10*MIN_PER_DAY,
       20*MIN_PER_DAY,
       30*MIN_PER_DAY, # 1 month
       50*MIN_PER_DAY,
       100*MIN_PER_DAY,
       365*MIN_PER_DAY # 1 year
    ]


    delays = [int(x) for x in delays] # rounding

    print('Scheduling checks')
    save_to_dynamo(delays,post_ids)
    print('Finished scheduling messages for later')

# delays is a list of times from now
# measured in minutes
# post_ids is an iterable of post ids
# (any duplicates will be combined)
def save_to_dynamo(delays,post_ids):
    client = boto3.client('dynamodb')

    table_name = os.environ['delay_table']

    for delay in delays:
        now = int(time.time())

        then = now + delay*SEC_PER_MIN

        print('Saving for time %d' % then)

        client.update_item(
            TableName=table_name,
            Key={'time':{'N':str(then)},'hash':hash_key_val},
            UpdateExpression="ADD post_ids :element",
            ExpressionAttributeValues={":element":{"SS":post_ids}}
        )

        # dynamo limit is 5 per second for this table
        # Halving that frequency, just to be sure
        time.sleep(2/5) # python 3 does this as a float

