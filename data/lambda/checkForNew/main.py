import praw
import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
import json
import common
import scheduling

def lambda_handler(event,contex):
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        return(common.unit_tests())
    else:
        print('Running main (non-test) handler')
        return(look_for_new())

def look_for_new():
    print('Looking for new posts')

    reddit = praw.Reddit('bot1')
    subreddits = ['bottest']

    for sub_name in subreddits:
        print('subreddit: ' + sub_name)
        check_subreddit(sub_name)

def check_subreddit(sub_name):

    dry_run = os.getenv('dry_run',"False")
    dry_run = dry_run in [True,"True","TRUE",'true']

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
                scheduling.new_posts([s.id for s in submissions])

    if dry_run:
        print('Would have replied to %d posts, skipped %d posts' % (len(submissions),limit-len(submissions)))
    else:
        print('Replied to %d posts, skipped %d posts' % (len(submissions),limit-len(submissions)))

def save_initial(replies,submissions):
    table_name = os.environ['post_history_table']
    client = boto3.client('dynamodb')

    now = int(time.time())
    items = []


    for (r,s) in zip(replies,submissions):
        item = {
            'PutRequest':{
                'Item':{
                    'post_id':{'S':s.id},
                    'inital_reply':{'S':r},
                    'initial_post_body':{'S':s.selftext},
                    'initial_reply_time':{'N':str(now)} # boto requires numbers as strings
                }
            }
        }
        items.append(item)

    # print('Here is what I will write to dynamodb')
    # pp.pprint(items)
    print('Writing what I\'ve done to dynamodb')
    try:
        response = client.batch_write_item(
            RequestItems={
                table_name: items
            },
            ReturnConsumedCapacity='TOTAL',
        )
    except client.exceptions.ResourceNotFoundException:
        print('Table %s does not exist, creating it now' % table_name)
        response = client.create_table(
            AttributeDefinitions=[
                {
                    'AttributeName': 'post_id',
                    'AttributeType': 'S'
                },
            ],
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'post_id',
                    'KeyType': 'HASH'
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 5
            }
        )
        waiter = client.get_waiter('table_exists')
        waiter.wait(
            TableName=table_name,
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 20
            }
        )
        print('Now trying again to write to table %s' % table_name)
        response = client.batch_write_item(
            RequestItems={
                table_name: items
            },
            ReturnConsumedCapacity='TOTAL'
        )

    print('Consumed capacity:')
    pp.pprint(response['ConsumedCapacity'])

    if ('UnprocessedItems' in response) and (response['UnprocessedItems'] != {}):
        print('Response to batch_write:')
        pp.pprint(response)
        raise(NotImplementedError)


# takes in a list of post ids
# returns a list which is a subset of that list
# containing the post ids which appear as a primary key
# in the table_name dynamodb table
#
# this function handles pagination
def keys_exist(ids):
        table_name = os.environ['postHistoryTable']
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
