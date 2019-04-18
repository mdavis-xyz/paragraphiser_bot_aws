import certifi
import urllib3
from bs4 import BeautifulSoup as bs
import pprint as pp
import re

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

# returns a new url if the original is AMP
# otherwise return None
patterns = [
        r"http(s?):\/\/www\.google\.com\/amp\/s\/(\S+)",
        r"http(s?):\/\/[^\/]+.ampproject.org/v/s\/(\S+)",
        r"http(s?):\/\/amp\.(\S+)"
]
regexs = [re.compile(pattern,re.IGNORECASE) for pattern in patterns]
def isAMP(url):
    return(any([regex.match(url) for regex in regexs]))

def convertURL(url):
    if not isAMP(url):    
        print("Not AMP link: %s" % url)
        return(None)

    print("Is AMP link: %s" % url)
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
    if any([isAMP(u) for u in choices]):
       print("some canonical links are still AMP: ")
       print('\n'.join([u for u in choices if isAMP(u)]))
    choices = set([c for c in choices if not isAMP(c)])

    if any(c.startswith('https://') for c in choices):
       choices = set([c for c in choices if not c.startswith('http://')])
    assert(len(choices) > 0)

    if len(choices) > 1:
       print("Multiple options for %s:" % url)
       print("\n   ".join(choices))

    choice = list(choices)[0]

    print("FROM %s" % url)
    print("TO   %s" % choice)

    return(choice)


def testAll(): 
    testRegex()
    # check simple domain changes 
    data = [
       {"before": "https://www.google.com/amp/s/amp.theguardian.com/lifeandstyle/2019/feb/23/truth-world-built-for-men-car-crashes",
        "after": "https://www.theguardian.com/lifeandstyle/2019/feb/23/truth-world-built-for-men-car-crashes"
        },
       {"before": "https://www-rawstory-com.cdn.ampproject.org/v/s/www.rawstory.com/2019/02/fox-friends-host-says-hasnt-washed-hands-10-years-germs-not-real-thing-cant-see/amp/?amp_js_v=a2&amp_gsa=1#referrer=https%3A%2F%2Fwww.google.com&amp_tf=From%20%251%24s&ampshare=https%3A%2F%2Fwww.rawstory.com%2F2019%2F02%2Ffox-friends-host-says-hasnt-washed-hands-10-years-germs-not-real-thing-cant-see%2F",
        "after": "https://www.rawstory.com/2019/02/fox-friends-host-says-hasnt-washed-hands-10-years-germs-not-real-thing-cant-see/amp/?amp_js_v=a2&amp_gsa=1#referrer=https%3A%2F%2Fwww.google.com&amp_tf=From%20%251%24s&ampshare=https%3A%2F%2Fwww.rawstory.com%2F2019%2F02%2Ffox-friends-host-says-hasnt-washed-hands-10-years-germs-not-real-thing-cant-see%2F"
        },
        {"before": "https://www-telegraph-co-uk.cdn.ampproject.org/v/s/www.telegraph.co.uk/news/2018/12/15/iranian-asylum-seeker-raped-17-year-old-spared-deportation-due/amp/?amp_js_v=a2&amp_gsa=1#referrer=https%3A%2F%2Fwww.google.com&amp_tf=From%20%251%24s&ampshare=https%3A%2F%2Fwww.telegraph.co.uk%2Fnews%2F2018%2F12%2F15%2Firanian-asylum-seeker-raped-17-year-old-spared-deportation-due%2F",
         "after": "https://www.telegraph.co.uk/news/2018/12/15/iranian-asylum-seeker-raped-17-year-old-spared-deportation-due/amp/?amp_js_v=a2&amp_gsa=1#referrer=https%3A%2F%2Fwww.google.com&amp_tf=From%20%251%24s&ampshare=https%3A%2F%2Fwww.telegraph.co.uk%2Fnews%2F2018%2F12%2F15%2Firanian-asylum-seeker-raped-17-year-old-spared-deportation-due%2F"
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
         }
    ]

    for urls in data:
        actual = convertURL(urls['before'])
        if actual == None:
            print("url not detected as AMP link: " + urls['before'])
        assert(actual)
        assert(convertURL(urls['after']) == None)
        if actual != urls['after']:
            print("\n"*5)
            print("\nbefore:   %s" % urls['before'])
            print("\nexpected: %s" % urls['after'])
            print("\nactual:   %s" % actual)
        assert(actual == urls['after'])

    # check full lookup
    data = [
        {"before": "https://amp.smh.com.au/federal-election-2019/morrison-caught-lying-bowen-demands-answers-from-treasury-over-387-billion-tax-costing-20190412-p51dl7.html?__twitter_impression=true",
         "after": "https://www.smh.com.au/federal-election-2019/morrison-caught-lying-bowen-demands-answers-from-treasury-over-387-billion-tax-costing-20190412-p51dl7.html"
         },
        {"before": "https://amp.9news.com.au/article/f4dbc610-b8f8-4fe6-9226-f3029b002d98",
         "after": "https://www.theregister.co.uk/2017/05/19/open_source_insider_google_amp_bad_bad_bad"
         }
        ]


    for urls in data:
        actual = convertURL(urls['before'])
        assert(actual)
        assert(convertURL(urls['after']) == None)
        actual = convertURL(urls['before'])
        if actual != urls['after']:
            print("before: %s" % urls['before'])
            print("expected: %s" % urls['after'])
            print("actual: %s" % actual)
        assert(actual == urls['after'])

testAll()
print("Done")
