# import praw
import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
from mako.template import Template
import string

# Apparently you can't have a dynamo table with just a
# sort key. So I'll add an arbitrary hash key to the delay table, which will only have
# one value
hash_key_val = 'data'

def unit_tests():
    return()

# only run from a lambda which has replyTemplateNew.mako
def mako_test():
    # using mako library to pass data into the template
    print('Checking that mako works')
    reply_template_fname = './replyTemplateNew.mako'
    with open(reply_template_fname,'r') as f:
        reply_msg = Template(f.read()).render(num_potatos=1)


def max_paragraph_size(text):
    paragraphs = text.split('\n')
    largest_para = max([len(p) for p in paragraphs])
    return(largest_para)

# count the number of times word appears in text
# case insensitive
def count_word_occurance(word,text):
    # replace all white space with single space characters
    for c in string.whitespace:
        text = text.replace(c,' ')
    assert(all([c not in word for c in string.whitespace]))

    # split by white space
    words = text.split(' ')

    # and remove punctuation
    words = [w.strip(string.punctuation) for w in words]

    # case insensitive count
    count = len([w for w in words if word.lower() in w.lower()])

    return(count)

# for posts we have not seen before
# if you want to ignore this post, return None
# if you want to comment on this post, return
# {'original_reply':msg}, where msg is a markdown formatted
# comment which will be used to generate a reply
# this return dict may other data (1 level deep though)
# and it will be returned in update_reply when we come back to
# check how your comment is doing
def generate_reply(submission):
    print('generate_reply called on post %s' % submission.id)
    if (not submission.is_self):
        print('Submission %s is not eligible for reply because it is not a self post' % submission.id)
        return(None)
    else:
        num_potatos = count_word_occurance('potato',submission.selftext)
        if num_potatos == 0:
            print('Submission %s is not eligible for reply because it doesn\'t mention the word potato' % submission.id)
            return(None)

        # using mako library to pass data into the template
        reply_template_fname = './replyTemplateNew.mako'
        with open(reply_template_fname,'r') as f:
            reply_msg = Template(f.read()).render(num_potatos=num_potatos)

        ret = {
            'original_reply':reply_msg,
            'original_post':submission.selftext,
            'original_num_potatos':num_potatos
        }

        return(ret)

# for posts we've seen and commented on before
# submission is the current state of the post
# data is what you returned from generate_reply when we first saw the post
# This will only be called on posts we've commented on
# return None to do nothing (leave comment as is)
# or return a dict with {'updated_reply':msg}, then the comment will
# be updated to equal msg
# that return dict can contain other entries, which will be saved and returned next time we check
# if it contains keys returned before, this latest version's values will be updated
def update_reply(submission,comment,data):
    assert(submission.is_self)
    if 'potato' in submission.selftext:
        print('Post %s is still eligible for comment' % submission.id)
        return(None)
    else:
        reply_template_fname = './replyTemplateUpdate.mako'
        cur_num_potatos = count_word_occurance('potato',submission.selftext)
        if cur_num_potatos == data['current_num_potatos']:
            print('No change to post %s since last check' % submission.id)
            return(None)
        prev_num_potatos = data['original_num_potatos']

        with open(reply_template_fname,'r') as f:
            reply_msg = Template(f.read()).render(
                cur_num_potatos=cur_num_potatos,
                prev_num_potatos=prev_num_potatos
            )

        data['current_num_potatos'] = cur_num_potatos
        data['updated_reply'] = reply_msg

        return(data)
