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


def lambda_handler(event,contex):
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        common.unit_tests()
        common.mako_test()
        look_for_new(dry_run=True)
    else:
        print('Running main (non-test) handler')
        return(look_for_new())

def look_for_new(dry_run=False):
    print('Looking for new posts')

    reddit = praw.Reddit('bot1')
    subreddits = os.environ['subreddits'].split(',')

    for sub_name in subreddits:
        print('subreddit: ' + sub_name)
        check_subreddit(sub_name,dry_run=dry_run)

def check_subreddit(sub_name,dry_run=False):

    skipped_posts = 0
    limit = int(os.getenv('num_to_scan',50))

    reddit = praw.Reddit('bot1')
    subreddit = reddit.subreddit(sub_name)
    submissions = [s for s in subreddit.hot(limit=limit)]

    print('Looking at the hottest %d posts' % limit)

    post_ids = [s.id for s in submissions]

    print('Hottest %d post ids: %s' % (limit,', '.join(post_ids)))
    posts_replied_to = keys_exist(post_ids)

    if len(posts_replied_to) > 0:
        print('I have replied to some of these posts already: \n%s' % ', '.join(posts_replied_to))
    else:
        print('I have not replied to any of these posts before')

    # only keep the submissions we haven't seen before
    submissions = [s for s in submissions if (s.id not in posts_replied_to)]

    print('%d of the hottest self posts not been replied to yet' % len(submissions))
    print(', '.join([s.id for s in submissions]))

    if len(submissions) != 0:

        replies = [common.generate_reply(s) for s in submissions]

        # drop submissions where generate_reply returned None
        submissions = [s for (s,r) in zip(submissions,replies) if r != None]
        replies = [r for r in replies if r != None]

        if len(replies) == 0:
            print('None of the new posts are eligible for reply')
        else:
            if dry_run:
                print('I would reply to the following posts:')
            else:
                print('About to reply to the following posts:')
            print('\n   '+ '\n   '.join([s.id for s in submissions]))

            comment_ids = []

            for (r,s) in zip(replies,submissions):
                reply_and_save(r,s,dry_run)
                time.sleep(10) # praw isn't handling throttling as well as it should

    if dry_run:
        print('Would have replied to %d posts, skipped %d posts' % (len(submissions),limit-len(submissions)))
    else:
        print('Replied to %d posts, skipped %d posts' % (len(submissions),limit-len(submissions)))

def reply_and_save(reply,submission,dry_run):

        assert(type(reply) == type({}))
        assert('original_reply' in reply)

        if dry_run:
            print('Would reply to post %s' % submission.id)
            print('With comment:\n%s' % reply['original_reply'])
        try:
            print('Replying to post %s' % submission.id)
            comment = submission.reply(reply['original_reply'])
        except praw.exceptions.APIException as e:
            if 'ratelimit' in e.message.lower():
                print('Hmm, I\'m being rate limited. Waiting 60 seconds')
                time.sleep(60)
                print('Waking up, trying again')
                submission.reply(reply['original_reply'])
        comment_id = comment.id

        save_initial(reply,submission.id,comment_id,dry_run)
        schedule_checks(submission.id,dry_run)

# reply is the data payload returned by common.generate_reply
def save_initial(data,submission_id,comment_id,dry_run):
    table_name = os.environ['post_history_table']
    client = boto3.client('dynamodb')

    now = int(time.time())

    item = {
        'post_id':{'S':submission_id},
        'comment_id':{'S':comment_id},
        'data':{'S':json.dumps(data)},
        'initial_reply_time':{'N':str(now)} # boto requires numbers as strings
    }

    if dry_run:
        print('Would save initial post data for %s' % submission_id)
    else:
        print('Saving initial post for %s' % submission_id)

        response = client.put_item(
            TableName=table_name,
            Item=item,
        )

        print('Saved initial post for %s' % submission_id)


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


        items = response['Responses'][table_name]

        pp.pprint(items)

        if ('UnprocessedKeys' in response) and (response['UnprocessedKeys'] != {}):
            print('Here was the response:')
            pp.pprint(response)
            print('TODO: implement pagination')
            raise(NotImplementedError)

        items = [x['post_id']['S'] for x in items]
        return(items)

def schedule_checks(post_id,dry_run):

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

    client = boto3.client('dynamodb')

    table_name = os.environ['schedule_table']

    for delay in delays:
        now = int(time.time())

        then = now + delay*SEC_PER_MIN

        assert(type(post_id) == type(''))

        if dry_run:
            print('Would save for time %d' % then)
        else:
            print('Saving for time %d' % then)

            client.update_item(
                TableName=table_name,
                Key={'time':{'N':str(then)},'hash':{'S':common.hash_key_val}},
                UpdateExpression="ADD post_ids :element",
                ExpressionAttributeValues={":element":{"SS":[post_id]}} # appends
            )

            # dynamo limit is 5 per second for this table
            # Halving that frequency, just to be sure
            time.sleep(2/5) # python 3 does this as a float

    print('Finished scheduling messages for later for post %s' % post_id)
