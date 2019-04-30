import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
import json
import common
import errors
import praw
import prawcore

SEC_PER_MIN = 60
MIN_PER_H = 60
SEC_PER_H = SEC_PER_MIN * MIN_PER_H
H_PER_DAY = 24
MIN_PER_DAY = H_PER_DAY * MIN_PER_H
SEC_PER_DAY = H_PER_DAY * SEC_PER_H
DAYS_PER_YEAR = 365
MIN_PER_YEAR = MIN_PER_DAY * DAYS_PER_YEAR
H_PER_YEAR = H_PER_DAY * DAYS_PER_YEAR
SEC_PER_YEAR = SEC_PER_DAY * DAYS_PER_YEAR



def lambda_handler(event,context):
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        common.unit_tests()
        look_for_new({'post_id':'bg2c86'},context,dry_run=True)
        subreddits = [r.strip() for r in os.environ['subreddits'].split(',') if r.strip() != '']
        look_for_new(event,context,dry_run=True,subreddits=subreddits[0:2]) # keep it quick, because http invocation times out
    elif os.environ['enable'] not in [True,'true','True','TRUE',1]:
        print('Function disabled')
    else:
        print('Running main (non-test) handler')
        return(errors.capture_err(look_for_new,event,context))


def look_for_new(event,context,dry_run=False,subreddits=None):

    reddit = praw.Reddit('bot1')

    if 'post_id' in event:
        post_id = event['post_id']
        print("Checking just post %s" % post_id)
        if post_id in keys_exist([post_id]):
            print("Post %s has already been replied to, doing nothing" % post_id)
        else:
            submission = reddit.submission(id=post_id)
            reply = common.generate_reply(submission)
            if reply:
                if submission.id in common.otherBotRecent(reddit):
                    print("Not replying to %s because other bot already has" % submission.id)
                else:
                    print("Other bot has not replied to %s" % submission.id)
                    reply_and_save(reply,submission,dry_run)
            else:
                print("Not replying to submission %s" % post_id)
    else:
        print('Looking for new posts')
        print("First getting posts by other bot")
        start = time.time()
        other_bot_recent = common.otherBotRecent(reddit)
        end = time.time()
        print("Got posts by other bot (took %.1f seconds)" % (end - start))

        if not subreddits:
            subreddits = [r.strip() for r in os.environ['subreddits'].split(',') if r.strip() != '']
        else:
            assert(type(subreddits) == type(['']))
        start = time.time()
        for sub_name in subreddits:
            now = time.time()
            if dry_run and ((now - start) > 30): # when invoked over http, timeout is short
                print("Breaking out of for loop for test")
                break
            assert(sub_name.strip() != '')
            assert(not any([c in sub_name for c in ',;/']))
            print('subreddit: ' + sub_name)
            start = time.time()
            check_subreddit(sub_name,other_bot_recent,dry_run=dry_run)
            end = time.time()
            print("Took %.1f seconds to check subreddit %s" % (end-start,sub_name))
    print("look_for_new returning")

def check_subreddit(sub_name,other_bot_recent=[],dry_run=False):

    start = time.time()

    skipped_posts = 0
    limit = int(os.getenv('num_to_scan',20))

    reddit = praw.Reddit('bot1')
    subreddit = reddit.subreddit(sub_name)
    try:
        submissions = [s for s in subreddit.new(limit=limit)]
    except prawcore.exceptions.ResponseException:
        print('Error: something went wrong, sleeping for 10 seconds then trying again, slower')
        time.sleep(10)
        subreddit = reddit.subreddit(sub_name)
        submissions = []
        for s in subreddit.hot(limit=limit):
            submissions.append(s)
            time.sleep(1)


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

        end = time.time()
        print("Everything for sub %s prior to for loop took %.1f seconds" % (sub_name,end - start))

        print("Iterating through remaining submissions:")
        num_replied = 0
        start_loop = time.time()
        for submission in submissions:
            start_subm = time.time()
            reply = common.generate_reply(submission)
            if reply != None:
                if submission.id in other_bot_recent:
                    print("Would comment on %s, but the other bot did already" % submission.id)
                else:
                    num_replied += 1
                    reply_and_save(reply,submission,dry_run)
                    end_subm = time.time()
                    print("Checking and replying to post %s took %.1f seconds" % (submission.id,end_subm-start_subm))
                    #if not dry_run:
                    #    print("Sleeping for a bit")
                    #    time.sleep(10) # praw isn't handling throttling as well as it should
        end_loop = time.time()
        print("Loop for sub %s took %.1f seconds" % (sub_name,end_loop-start_loop))

    if dry_run:
        print('Would have replied to %d posts, skipped %d posts' % (num_replied,limit-num_replied))
    else:
        print('Replied to %d posts, skipped %d posts' % (num_replied,limit-num_replied))

def reply_and_save(reply,submission,dry_run):

        assert(type(reply) == type({}))
        assert('original_reply' in reply)

        if dry_run:
            print('Would reply to post %s' % submission.id)
            print('With comment:\n%s' % reply['original_reply'])
            comment_id = 'fake comment id for testing'
        else:
            try:
                print('Replying to post %s' % submission.id)
                comment = submission.reply(reply['original_reply'])
            except praw.exceptions.APIException as e:
                if 'ratelimit' in e.message.lower():
                    print('Hmm, I\'m being rate limited. Waiting 60 seconds')
                    time.sleep(80)
                    
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
            MIN_PER_H,
            MIN_PER_DAY,
            7*MIN_PER_DAY,
            30*MIN_PER_DAY,
            MIN_PER_YEAR
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

if __name__ == '__main__':
    post_id = 'bg2c86'
    event = {'post_id':post_id}
    context = None
    print("Calling look_for_new from __main__")
    look_for_new(event,context,dry_run=True)
    print("Done")
