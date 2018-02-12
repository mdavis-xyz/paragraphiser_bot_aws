# import praw
import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time

def unit_tests():
    pass

def max_paragraph_size(text):
    paragraphs = text.split('\n')
    largest_para = max([len(p) for p in paragraphs])
    return(largest_para)



def generate_reply(submission):
    reply_template_fname = './data/reply_template.md'
    with open(reply_template_fname,'r') as f:
        reply_msg = f.read()
    return(reply_msg)



# returns True if the text body is eligible for a reply
def eligible_body(text):
    # ret = max_paragraph_size(text) > 3000
    ret = 'potato' in text.lower()
    return(ret)
