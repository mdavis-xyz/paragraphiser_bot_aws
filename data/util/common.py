# import praw
import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
from mako.template import Template
import string
import re

# Apparently you can't have a dynamo table with just a
# sort key. So I'll add an arbitrary hash key to the delay table, which will only have
# one value
hash_key_val = 'data'

# bot replies for posts with at least this many characters without a new line
size_limit = 2300

def unit_tests():
    test_count_words()
    test_split()
    return()

# only run from a lambda which has replyTemplateNew.mako
def mako_test():
    # using mako library to pass data into the template
    print('Checking that mako works')
    reply_template_fname = './replyTemplateNew.mako'
    with open(reply_template_fname,'r') as f:
        reply_msg = Template(f.read()).render(num_potatos=1)

def test_split():
    print('testing paragraph splitter')
    input = 'first\n \nsecond para\n\n\nthird para\nstill third'
    expected = ['first','second para','third para\nstill third']
    actual = split_by_paragraph(input)
    if expected != actual:
        print('Error: test failed')
        print('input: %s' % input)
        print('expected: %s' % expected)
        print('actual: %s' % actual)
    assert(expected == actual)
    print('paragraph splitter passed')

# takes in a string
# returns an array of strings
# In markdown, a single new line character does not create a new paragraph
def split_by_paragraph(text):
    # regex because some people write '\n \n' when making a new paragraph
    # or maybe that's dynamodb playing tricks on me
    paragraphs = re.split('\n\s+\n',text)

    ## in case there are triple \n
    paragraphs = [p.strip('\n') for p in paragraphs]

    ## remove any 'paragraphs' which are empty or only whitespace
    all_white = lambda s: all([c in string.whitespace for c in s]) # True if empty
    paragraphs = [p for p in paragraphs if (not all_white(p)) or (p == '')]

    return(paragraphs)
    
def debug_lengths(text):
    paragraphs = split_by_paragraph(text)

    data = [{'start':p[0:10],'length':len(p)} for p in paragraphs]

    return(data)

def max_paragraph_size(text):
    paragraphs = split_by_paragraph(text)

    largest_para = max([len(p) for p in paragraphs])
    return(largest_para)

# for posts we have not seen before if you want to ignore this post, return None
# if you want to comment on this post, return
# {'original_reply':msg}, where msg is a markdown formatted
# comment which will be used to generate a reply
# this return dict may other data (1 level deep though)
# and it will be returned in update_reply when we come back to
# check how your comment is doing
def generate_reply(submission):
    print('generate_reply called on post %s' % submission.id)
    if (not submission.is_self):
        #print('Submission %s is not eligible for reply because it is not a self post' % submission.id)
        return(None)
    else:
        max_size = max_paragraph_size(submission.selftext)
        if max_size < size_limit:
            #print('Submission %s is not eligible for reply because it is too short' % submission.id)
            return(None)
        print('Max size in post %s: %d chars, size_limit %d' % (submission.id,max_size,size_limit))

        # using mako library to pass data into the template
        reply_template_fname = './replyTemplateNew.mako'
        with open(reply_template_fname,'r') as f:
            reply_msg = Template(f.read()).render()

        ret = {
            'original_reply':reply_msg,
            'original_post':submission.selftext
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

    # praw is wierd at times
    x = submission.selftext
    y = submission.selftext
    z = submission.selftext
    assert(x == y == z)
    assert(type(x) == type(''))

    max_size = max_paragraph_size(submission.selftext)

    if max_size >= size_limit:
        print('largest paragraph is %d characters' % max_size)
        print('Debug lengths:')
        pp.pprint(debug_lengths(submission.selftext))
        print('Post %s is still eligible for comment, no change' % submission.id)
        return(None)
    else:
        prev_words = count_words_max(data['original_post'])
        cur_words = count_words_max(submission.selftext)

        reply_template_fname = './replyTemplateUpdate.mako'

        with open(reply_template_fname,'r') as f:
            reply_msg = Template(f.read()).render(
                cur_max=cur_words,
                prev_max=prev_words
            )

        data['updated_reply'] = reply_msg
        data['curr_words'] = cur_words

        return(data)

# returns the number of words in the longest paragraph
def count_words_max(text):
    paragraphs = text.split('\n\n') # one \n renders as the same paragraph in markdown

    # in case there's 3 new line characters, remove 1 on the ends
    paragraphs = [p.strip('\n') for p in paragraphs]

    # if there's a single new line character, replace it with a normal space, because it's a word break
    paragraphs = [p.replace('\n',' ') for p in paragraphs]
    
    lengths = [count_words(p) for p in paragraphs]
    return(max(lengths))

# returns the number of words, assuming this is one paragraph
def count_words(text):

    # replace all white space with single space characters
    for c in string.whitespace:
        text = text.replace(c,' ')

    # remove punctuation
    for c in string.punctuation:
        text = text.replace(c,'')

    # split by white space
    words = text.split(' ')

    # get rid of empty words (e.g. was punctuation, or multiple consecutive white space
    words = [w for w in words if w != '']

    count = len(words)

    return(count)

def test_count_words():
    print('Testing count_words_max()')
    example = 'I\'ve got to get out of, here now!\n\nNo use stayin\'\nyeah you heard me, that is what I said'
    expected = 12
    actual = count_words_max(example)
    assert(expected == actual)
    print('count_words() test passed')
