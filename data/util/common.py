# import praw
import os
import pprint as pp
import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
from mako.template import Template
import string
import re
import certifi
import urllib3
from bs4 import BeautifulSoup as bs
import praw


otherAMPBot = 'AntiGoogleAmpBot'

# Apparently you can't have a dynamo table with just a
# sort key. So I'll add an arbitrary hash key to the delay table, which will only have
# one value
hash_key_val = 'data'


# to be called by checkForNew
def unit_tests():
    testAll()
    testGetReplyDict()
    testSelfPost()
    return()


# for posts we have not seen before if you want to ignore this post, return None
# if you want to comment on this post, return
# {'original_reply':msg}, where msg is a markdown formatted
# comment which will be used to generate a reply
# this return dict may other data (1 level deep though)
# and it will be returned in update_reply when we come back to
# check how your comment is doing
def generate_reply(submission,debug=False):
    print('generate_reply called on post %s' % submission.id)


    if submission.is_self:
        newURL = convertURL(submission.selftext)
        if not newURL:
            print("Submission %s did not contain any AMP links" % submission.id)
            return(None)
        elif newURL in submission.selftext:
            print("submission %s includes the canonical link too")
            return(None)
        else:
            print("Submission %s selftext contains URL, new one is: %s" % (submission.id,newURL))
            reply = getReplyDict(newURL) 
            if otherAMPBot(submission): 
                print("Other AMP bot has already replied to %s, returning None" % submission.id)
                return(None)
            return(reply)

    else: # link post
        newURL = convertURL(submission.url)
        if newURL:
            print("Submission %s links to AMP link %s which corresponds to: %s" % (submission.id,submission.url,newURL))
            reply = getReplyDict(newURL)
            if otherAMPBot(submission):
                print("Other AMP bot has already replied to %s, returning None" % submission.id)
                return(None)
            return(reply)
        else:
            print("Submission %s did not link to an AMP link, url was %s" % (submission.id,submission.url))
            return(None)

def testSelfPost():
    postId = 'bf826q' #https://www.reddit.com/r/bottest/comments/bf826q/test/
    print("Running unit tests for post %s" % postId)
    expected = 'https://uk.reuters.com/article/uk-britain-russia-idUKKBN1GH2V6'
    reddit = praw.Reddit('bot1')

    submission = reddit.submission(id=postId)

    actual = convertURL(submission.selftext)

    assert(actual == expected)

    reply = generate_reply(submission)
    assert(reply == getReplyDict(expected))

# returns true if that other AMP bot has replied
def otherAMPBot(submission):
    submission.comments.replace_more(limit=None)
    for comment in submission.comments:
        if comment.author.id == otherAMPBot:
            return(True)
    return(False)


def testOtherAMPBot():
    reddit = praw.Reddit('bot1')

    # I don't have any positive tests
    # since I don't think that bot actually replies to posts, only to comments
    tests = [
       (False,"https://www.reddit.com/r/worldnews/comments/besihy/mueller_identified_dozens_of_us_rallies_organized/")
    ]
    for (expected,postURL) in tests:
        submission = reddit.submission(url=postURL)
        assert(expected == otherAMPBot(submission))


# outside function, to cache between lambda invocations
with open('template.md','r') as f:
    template = Template(f.read())

# takes in a canonical URL,
# returns a dict with {'original_reply':text}
def getReplyDict(url):
    text = template.render(url=url)
    return({'original_reply':text})

def testGetReplyDict():
    url = "https://www.example.com/test"

    with open('templateTest.md','r') as f:
        text = f.read()

    expected = {'original_reply':text}

    actual = getReplyDict(url)

    assert(expected == actual)

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
    return(None) # never update a comment


# initialise outside a function, to cache between lambda invocations
http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',ca_certs=certifi.where())
def downloadWebPage(url):
    r = http.request('GET',url)
    if r.status == 200:
        print("Hit: " + url)
        html = r.data.decode('utf-8')
        #soup = bs(html, 'html.parser')
        return({'html':html,'status':r.status})
    else:
        print("Error %d fetching page %s" % (r.status, url))
        return({'status':r.status})


def testRegex():
    pattern = r"(\d+)\s\d+"
    replace = r"!\1"
    original = "test123 456 test"
    expected = "test!123 test"
    regex = re.compile(pattern, re.IGNORECASE)

    actual = regex.sub(replace,original)

    if expected != actual:
       print("expected: %s" % expected)
       print("actual: %s" % actual)
    assert(expected == actual)

    pattern = r"http(s?):\/\/[^\)\s]+"
    text = "[link](https://something.com/blah)"
    expected = "https://something.com/blah"
    regex = re.compile(pattern,re.IGNORECASE)
    match = regex.search(text)
    assert(match)
    assert(match.group(0) == expected)

# returns a new url if the original is AMP
# otherwise return None
# do this outside the function, to cache it between lambda invocations
patterns = [
        r"http(s?):\/\/www\.google\.com\/amp\/s\/[^\s\)]+",
        r"http(s?):\/\/[^\/]+.ampproject.org/v/s\/[^\s\)]+",
        r"http(s?):\/\/amp\.[^\s\)]+",
        r"http(s?):\/\/\S+\/amp\/[^\s\)]+"

]
regexs = [re.compile(pattern,re.IGNORECASE) for pattern in patterns]
# returns the url extracted from text, if there is an AMP url in the text
# otherwise return None
def getAMP(text):
    for regex in regexs:
        match = regex.search(text)
        if match:
            return(match.group(0))
    return(None)



# text is a string which may contain a URL
# if the argument contains an AMP link, this function returns the canonical link
# otherwise, returns None
def convertURL(text):
    url = getAMP(text)
    if not url:    
        print("No AMP link")
        return(None)

    print("Contains AMP link: %s" % url)
    download = downloadWebPage(url)
    if download['status'] != 200:
        print("Not sure how to convert URL")
        return(None)

    soup = bs(download['html'], 'html.parser')    

    choices = []
    # inside <head></head> grab meta tags
    #   <meta property="og:url" content="https://www.mdavis.xyz/" />
    #   <link href="https://www.9news.com.au/2019/02/15/21/17/perth-news-vegan-farmer-fight" rel="canonical">
    metaTags = soup.find_all('meta',attrs={'property':'og:url'})
    choices += [tag.get('content') for tag in metaTags]

    linkTags = soup.find_all('link',attrs={'rel':'canonical'})
    choices += [tag.get('href') for tag in linkTags]
   
    pp.pprint({'original':url,'possibilities':choices})
    if any([getAMP(u) for u in choices]):
       print("some canonical links are still AMP: ")
       print('\n'.join([u for u in choices if getAMP(u)]))
    choices = set([c for c in choices if not getAMP(c)])

    if any(c.startswith('https://') for c in choices):
       choices = set([c for c in choices if not c.startswith('http://')])
    assert(len(choices) > 0)

    if len(choices) > 1:
       print("Multiple options for %s:" % url)
       print("\n   ".join(choices))

    choice = list(choices)[0]

    print("FROM %s" % url)
    print("TO   %s" % choice)

    assert(not getAMP(choice))

    return(choice)


def testAll(): 
    testRegex()
    # check simple domain changes 
    data = [
       {"before": "https://www.google.com/amp/s/amp.theguardian.com/lifeandstyle/2019/feb/23/truth-world-built-for-men-car-crashes",
        "after": "https://www.theguardian.com/lifeandstyle/2019/feb/23/truth-world-built-for-men-car-crashes"
        },
       {"before": "https://www-rawstory-com.cdn.ampproject.org/v/s/www.rawstory.com/2019/02/fox-friends-host-says-hasnt-washed-hands-10-years-germs-not-real-thing-cant-see/amp/?amp_js_v=a2&amp_gsa=1#referrer=https%3A%2F%2Fwww.google.com&amp_tf=From%20%251%24s&ampshare=https%3A%2F%2Fwww.rawstory.com%2F2019%2F02%2Ffox-friends-host-says-hasnt-washed-hands-10-years-germs-not-real-thing-cant-see%2F",
        "after": "https://www.rawstory.com/2019/02/fox-friends-host-says-hasnt-washed-hands-10-years-germs-not-real-thing-cant-see/"
        },
        {"before": "https://www-telegraph-co-uk.cdn.ampproject.org/v/s/www.telegraph.co.uk/news/2018/12/15/iranian-asylum-seeker-raped-17-year-old-spared-deportation-due/amp/?amp_js_v=a2&amp_gsa=1#referrer=https%3A%2F%2Fwww.google.com&amp_tf=From%20%251%24s&ampshare=https%3A%2F%2Fwww.telegraph.co.uk%2Fnews%2F2018%2F12%2F15%2Firanian-asylum-seeker-raped-17-year-old-spared-deportation-due%2F",
         "after": "https://www.telegraph.co.uk/news/2018/12/15/iranian-asylum-seeker-raped-17-year-old-spared-deportation-due/"
         },
        {"before": "https://www.google.com/amp/s/www.seattletimes.com/seattle-news/data/kids-making-a-comeback-more-than-100000-under-18-in-seattle-for-the-first-time-in-50-years/%3Famp%3D1",
         "after": "https://www.seattletimes.com/seattle-news/data/kids-making-a-comeback-more-than-100000-under-18-in-seattle-for-the-first-time-in-50-years/"
         },
        {"before": "https://www.google.com/amp/s/anps.org/2018/05/30/know-your-natives-death-camas/amp/",
         "after": "https://anps.org/2018/05/30/know-your-natives-death-camas/"
         },
        {"before": "https://www.google.com/amp/s/www.christianpost.com/amp/dr-phil-exposes-cult-that-some-say-is-masking-itself-as-christian-church-in-wells-texas.html",
         "after": "https://www.christianpost.com/news/dr-phil-exposes-cult-that-some-say-is-masking-itself-as-christian-church-in-wells-texas.html"
         },
        {"before": "https://www.google.com/amp/s/www.fatherly.com/news/masturbation-robot-sperm-collector-chinese/amp/",
         "after": "https://www.fatherly.com/news/masturbation-robot-sperm-collector-chinese/"
         },
        {"before": "https://www.google.com/amp/s/us.blastingnews.com/showbiz-tv/2018/09/got-leak-claims-tyrion-will-be-found-guilty-of-treason-in-the-dragonpit-trial-002710077.amp.html",
         "after": "https://us.blastingnews.com/showbiz-tv/2018/09/got-leak-claims-tyrion-will-be-found-guilty-of-treason-in-the-dragonpit-trial-002710077.html"
         },
        {"before": "https://amp.smh.com.au/federal-election-2019/morrison-caught-lying-bowen-demands-answers-from-treasury-over-387-billion-tax-costing-20190412-p51dl7.html?__twitter_impression=true",
         "after": "https://www.smh.com.au/federal-election-2019/morrison-caught-lying-bowen-demands-answers-from-treasury-over-387-billion-tax-costing-20190412-p51dl7.html"
         },
        {"before": "https://amp.9news.com.au/article/f4dbc610-b8f8-4fe6-9226-f3029b002d98",
         "after": "https://www.9news.com.au/2019/02/15/21/17/perth-news-vegan-farmer-fight"
         },
        {"before": "https://uk.mobile.reuters.com/article/amp/idUKKBN1GH2V6",
         "after": "https://uk.reuters.com/article/uk-britain-russia-idUKKBN1GH2V6"
         }
        ]


    for urls in data:
        try:
            assert(getAMP(urls['before']) == urls['before'])
        except AssertionError as e:
            print("\n\nbefore: %s" % urls['before'])
            print("after: %s" % getAMP(urls['before']))
            raise(e)
        assert(not getAMP(urls['after']))
        actual = convertURL(urls['before'])
        if not actual:
            print("\n\nAMP link not detected as AMP link: %s" % urls['before'])
        assert(actual)
        assert(convertURL(urls['after']) == None)
        actual = convertURL(urls['before'])
        if actual != urls['after']:
            print("\n"*5)
            print("\nbefore: %s" % urls['before'])
            print("\nexpected: %s" % urls['after'])
            print("\nactual: %s" % actual)
        assert(actual == urls['after'])
        selftext = 'Here is [a link](%s)' % urls['before']
        if not getAMP(selftext):
            print("selftext:\n%s" % selftext)
        try:
            assert(getAMP(selftext) == urls['before'])
        except AssertionError as e:
            print("selftext: %s" % selftext)
            print("AMP url with getAMP(): %s" % getAMP(selftext))
            raise(e)
        actual = convertURL(selftext)
        if actual != urls['after']:
            print("\n"*5)
            print("\nbefore: %s" % selftext)
            print("\nexpected: %s" % urls['after'])
            print("\nactual: %s" % actual)
        assert(actual == urls['after'])

if __name__ == '__main__':
    print('common.py invoked standalone, running unit tests')
    unit_tests()
    print('all unit tests passed')
