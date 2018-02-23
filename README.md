# Matt's Reddit Bot Template

This is a template for making reddit bots in python, and deploying them to AWS Lambda.

## Why Use This Template

### Bot Logic

This bot template has some nice features:

* Everything is already set up ready to go. You just:
  1. run the cookiecutter template (explained below)
  1. set up Amazon cloud credentials on your computer
  1. run the deployment script
 Bam! Now you have a working reddit bot. This particular reddit bot looks at `r/bottest` and responds to any self post that mentions the word potato. Now you can just go look at that specific potato logic, see how it works, and change it into what you want your bot to do. That's easier than writing everything yourself.

This bot also checks up on comments after it makes them.
If your bot's comment gets downvoted to negative infinity, you'd want to know.
This system sends you an email when your comment gets downvoted to negative.

This bot also checks on the post you commented on, after you comment.
Perhaps the submitter read your comment and changed their post.
You may want to update your comment to avoid looking silly.

It checks up on comments very frequently for new comments, and less frequently for old comments.
This is to provide the perfect compromise between low latency updates, and not using the reddit API too much. (You'll get throttled if you try to check up on all your bot's posts, every minute)


### Tooling and Infrastructure

Running your own server can be a lot of hassle, and results in downtime, and hardware costs.
I initially ran my bot on a beaglebone server, but a lightening strike in my street broke the server.
For most bots, you can run using serverless Lambda functions in Amazon's cloud, and you won't have to pay. (They have a free usage tier)

If you don't know what Amazon's "Lambda functions" are: You give them code, and they run it. You don't need to worry about an operating system (`sudo apt-get install blah`). You don't need to worry about scaling. If your reddit bot wants to comment on a thousand posts per second today, and nothing tomorrow, Amazon will happily handle that. (Reddit will definitely throttle that, but my point is that you don't need to worry about scaling, and you only pay for the seconds of computation that you use.)

You can try to run a simple script as a cron job on a simple server.
As mentioned earlier, there are downsides to a physical server, and a virtual machine is more expensive than lambda functions.

This tooling is very customisable, and can be extended to use any AWS resource.
You want to send an SMS whenever your bot spots a certain type of post?
That's easy, just modify the cloudformation template.
You want to use an image recognition API? Same again, it's far easier than with other tools.

## How To Use It

1. This repo is a [cookiecutter](https://cookiecutter.readthedocs.io/en/latest/index.html) template. Install the `cookiecutter` library.
(Typically with `pip install cookiecutter` or `pip install cookiecutter --user`)
1. Create a new reddit account to run your bot as. (It's neater than using your own)
1. Log in to reddit in your browser with this account. Click 'preferences', then select 'apps'
1. Fill out the information. Once you have 'created' the app, take note of the information you see. You'll need it for the next step.
1. In a terminal on a Linux computer, run: `cookiecutter https://github.com/mlda065/paragraphiser_bot_aws.git`. (I haven't tested this on a windows computer. It might work, I dunno. Windows is pretty useless) You'll be asked to fill out some information:
   * `bot_name`: The name of your bot. It must contain only letters, numbers, dashes and start with a letter
   * `aws_region`: Amazon's cloud has many regions. The cheapest is generally `us-east-1`. [Here is the full list of possibilities](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#concepts-available-regions)
   * `directory_name`: The name of the folder you want to download the template into. The folder should not yet exist
   * `email_for_alerts`: When there's an error with your bot, or a comment by your bot is downvoted into negative territory, an email will be sent here.
   * `reddit_client_id`: Get this from the previous step
   * `reddit_client_secret`: Get this from the previous step
   * `reddit_password`: the password for your bot's reddit account (which you just created). This will be saved in plain text, so make sure you don't the same password for anything else
   * `reddit_username`: the username of the reddit account you just created
   * `user_agent`: An arbitrary string used to identify your bot, and which version. e.g. "My Potatobot v0.1"

The template bot scans self posts in r/bottest, and comments on that post if it contains the word 'potato'. If that post is later edited, it updates the comment.

To change what the criteria is, go into `data/util/common.py`.
 * `generate_reply` takes in a [praw submission](https://praw.readthedocs.io/en/latest/code_overview/reddit_instance.html?highlight=submission#praw.Reddit.submission) object. ([praw](https://praw.readthedocs.io/en/latest/index.html) is the library used to talk to the reddit API).
   * `submission.id` is the unique identifier of each post. This is a short string which appears in the url in your browser when you look at the post.
   * `submission.is_self` is `True` or `False` depending on whether the post is a self post (text) or non-self post (link)
   * `submission.selftext` only exists for self posts. This is the body of the post.
   * read the comments at the top of this function, and look at the code that's there to understand it.
   * Apply your bot logic here. If you want your bot to ignore this submission, return None. If you want your bot to comment on this post, return a dictionary like `{'original_reply':msg}`. `msg` is the markdown formatted comment your bot will make. (You don't need to make it reply. The function calling `generate_reply` will do that). You may include other key/value pairs within this dict. That exact dict will be passed later to `update_reply` as the `data` argument
 * After commenting on a post, the bot comes back to see how it's gone.
   * The checks are frequent for recent comments, and infrequent for old comments. To see the specific times that the bot goes and checks on it's past comments, look in function `schedule_checks` in `data/lambda/checkForNew/main.py`
   * It looks at the score of the comment. This is upvotes - downvotes, plus comment replies. If someone replies to your bot's comment with 'good bot' or 'bad bot', that counts as an up/down vote. If the post is voted into negative score, you'll get an email to alert you.
   * It looks at the submission again. Perhaps the OP modified their post after reading your bot's comment. If so, maybe your bot's comment is no longer applicable. If you want to update your comment, return a dictionary which includes `{'updated_reply':msg}` (among other keys). Your comment will be updated to say the contents of `msg`. This dict will be returned the next time `update_reply` is called.
 * Add any tests you want to do to validate your code into the `unit_tests` function in `data/util/common.py`
 * The example uses a [mako](http://www.makotemplates.org/) template to put data into the reply. Look at the code for `update_reply` to see how this works. The files of the templates are `data/util/replyTemplateNew.mako` and `replyTemplateUpdate.mako`

Let's install the python packages we need for the tooling.
* Run `./makeForDeploy.sh` in a terminal
* This will create a virtual environment in `./env`
* Activate this virtual environment with `. ./env/bin/activate`
* Set up your local machine with the credentials of your aws account if you haven't already, using `aws configure`


## Deployment

This template comes with a fully fledged AWS deployment tooling. It's more general than just reddit bots or just lambda functions. Read 'How it works' to understand the detail'.

You can deploy to different stages (e.g. `dev` vs `prod`).

To deploy the bot:

* activate the virtual environment mentioned before (alternatively you could just install the `boto` python package onto your system)
* from the directory with `deploy.py`, run `python deploy.py -s dev`
   * `-s dev` tells the system to deploy to the dev stage. You can replace `dev` with `prod` or any other string.
   * This could take 5 minutes if it's your first run

You should see all green when the command finishes.

Submit a post in r/bottest and wait for the bot to respond. It's currently polling for new posts every 10 minutes.
If you don't want to wait for 10 minutes:

* log into the AWS console in a browser
* go to Lambda
* search for `checkForNew`
* Select the corresponding lambda
* trigger it (you'll have to set up a 'test' configuration. This is fairly straightforward. Just use the default payload, or an empty payload.)
* If you see red in the console, read the error message there, then redeploy. For more advanced debugging methods, read 'Debugging and logs'

## Development

The full deployment can take about 5 minutes, which is a frustratingly long deployment cycle. You can skip steps. There are 4 steps:

1. The virtual environment of each lambda function is built by executing the `makescript.sh` file within each lambda function's folder in `data/lambda/`. You only need to run this if you have modified the `makescript.sh` file (to add new python libraries), or modified anything in `data/util` or `data/credentials` (which gets copied in to the `data/lambda/x/include` folders). If you have not done either of those things since your last deployment, use the `-b` flag. e.g. `python deploy.sh -s prod -b`
1. Each lambda gets zipped up into a `.zip` file. If you have modified the python code in any `data/lambda/x/main.py` file, then you need to do this step. If you needed to do the previous step, then you need to do this step. Otherwise you can skip this step with the `-z` flag. e.g. `python deploy.py -s prod -bz`.
1. The zip of each lambda gets uploaded to S3. If you needed to do either of the previous steps, you need to do this step. If you only changed the cloudformation template (`data/cloudformation/stack.yaml`), then you can skip this step with the `-u` flag. e.g. `python deploy.py -s prod -bzu`
1. The cloudformation script is applied to the stack. The deployment script pushes whatever is the latest version of each zip from S3. (This is something normal cloudformation does not do. A benefit of using this tooling.) This step can't be skipped, it is compulsory. Unfortunately this step is very super quick.

If you're finding that the upload step is taking too long, consider doing your development on an EC2 virtual machine.
Uploads to S3 are faster that way.

**After** thorough testing, the subreddit the bot browses in can be changed by going into `data/cloudformation/stack.yaml`. Search for `subreddits`.
Replace `"bottest"` with your new subreddit name(s).
If you want the bot to be active in multiple subreddits, seperate them with a comma. Leave off the "r/"

## Debugging and Logs

There are unit tests which are conducted whenever a lambda is deployed. If the tests fail, you will be told, and will see the output of one of the tests.
In the `main.py` file for each lambda (`data/lambda/x/main.py`) there is a function called `lambda_handler()`. The general format is:

```
def lambda_handler(event,contex):
    if ('unitTest' in event) and event['unitTest']:
        print('Running unit tests')
        # add your unit tests here
    else:
        print('Running main (non-test) handler')
        main() # this handles the actual workload
```

The deployment tooling invokes the lambda function in the lambda environment,
with all the same permissions as normal.

When the tests fail, you will see the output of one of the failed tests printed by the deployment tooling.
If you want to see more detailed logs of the tests, or of the production invocations,
open up AWS in your browser, and go to Cloudwatch. Select *Logs*, then filter by
`/aws/lambda/<botname>-stack-`.

## How it works

### Bot

There are 5 lambda functions.

* checkForNew
   * This polls reddit every 10 minutes for new posts. This frequency is set in `data/cloudformation/stack.yaml`
   * Each new post is passed to `util/common.py` `generate_reply()` to determine whether the bot should reply to it or not. If so:
      * the bot replies
      * data about the post and the reply is saved in the `botname-stack-postHistory` `dynamodb` table
      * many entries are saved in the `botname-stack-schedule` table. One for each time that the bot should come back and check the comment and the post. One feature of this system is that these checks are very frequent for new comments, and less frequent for old comments. The large integer in the index of this table is a unix timestamp.
* poll
   * every 60 seconds this function looks at what's in `botname-stack-schedule`. If there are any timestamps in the past or within the next 60 seconds, this bot checks the posts corresponding to those timestamps. (Duplicates merged) It doesn't check it directly. For each post, `poll` invokes `checkOldOne` with a payload that contains one post id.
* checkOldOne
   * This is invoked by `poll`. Or can be manually invoked with a payload of `{"post_id":"xxxxxxx"}` if you want to check on a particular post. (Where `xxxxxxx` is the post id in the url of that submission)
   * This checks whether your bot's comment on that post was downvoted below 0. If so you get sent an email.
   * This also checks whether the original post has been changed.
* errorHandler
   * This monitors whether any other functions fail (i.e. raise a python exception). If they do, you get sent an email. But if they fail again, you won't get sent a second email. This is deliberate, because you don't want to get an email every minute if `poll` keeps encountering the same error. Once you deploy, the emails will start again.
* failer
   * This lambda is not normally invoked. If you go into the console and invoke it manually, it will fail. This is so that you can test that the errorHandler is working.

### Tooling

As mentioned earlier, the deployment tooling is a fully customisable, generalisable AWS deployment kit.
I've looked into alternatives (e.g. Zappa, serverless.com) and I couldn't find anything that did quite what I want.

Here's how it works:

* The data for each lambda function is saved in a folder in `data/lambda`
   * `data/lambda/$LAMBDA/makescript.sh` is a bash script to create a virtual environment. This is useful if you want to create a different virtual environment for each lambda in your project. (e.g. if Lambda A requires large library X, and Lambda B requires large library Y, and X+Y is too large for lambda). This is invoked by the deployment tooling if you don't use the `-b` flag. The makescripts are also how files from `data/util` or `data/credentials` get copied into each lambda. Those folders are for any code which is used by multiple lambdas. The deployment tooling executes the makescripts for all lambdas in parallel.
   * `data/lambda/$LAMBDA/main.py` has the main logic, and any unit tests.
* Each lambda gets zipped up into a `lambda.zip` file. This is the virtual environment (created by the `makescript.sh`), `main.py` and anything in `data/lambda/$LAMBDA/include`. The deployment tooling zips all lambdas in parallel.
* The zip of each lambda gets uploaded to S3, all in parallel. The bucket should be set to have versioning turned on.
* The cloudformation template (`data/cloudformation.stack.yaml`) is applied. (Either stack creation or change set). Normally if you upload a new version of the lambda zip to S3 and apply a cloudformation template, it will not update the lambda to use what's in S3. This tooling keeps track of the version of lambda you just uploaded, and passes that as a parameter to the cloudformation yaml template. Everything for each project is kept contained within one cloudformation template. (except the S3 bucket)
* After the latest zip is pushed into lambda, all previous versions of that lambda are deleted. This is important because otherwise you'd build up many GB of version history in S3, which would cost you money. (If you delete a file in S3, previous versions are still there, but the browser interface makes you think they're gone)

## Security

I tried to handle the secrets for reddit properly. I really did. But it's bloody hard to pass secrets into Amazon's lambda function with enterprise-grade security. Amazon's key handler is really confusing to use.
So the credentials for reddit are saved in `credentials/praw.ini`, which is copied into `data/lambda/checkForOne/include/praw.ini` and `data/lambda/checkOldOne/include/praw.ini` by the deployment tooling. Then it's added to the zip file for the lambda function.
This is kind of bad practice, but hey, this is just a reddit bot. That's why you should make a new reddit user just for the bot, and not use the same password anywhere else.

The AWS IAM permissions of the resources are very loose. I was too lazy to tighten them. (If you feel up for it, go change `ExecutionRole` in `data/cloudformation/stack.yaml`).
But why bother? If you have nothing in this AWS account except for your reddit bot, what's the worst case scenario? Someone takes control of your reddit bot.
If that happens, log in to reddit and change your bot's password. Tada!

If you *do* have other stuff in the same AWS account, well ... don't! It's good practice to have a seperate AWS account for each project.
It provides excellent security through iron-clad partitioning.
It also means that if you hit a limit in one project (e.g. max writes to dynamodb), your other projects won't come grinding to a halt.

## Deleting the bot

1. Log into AWS in a browser.
1. Go to "Cloudformation"
1. Delete the stack with the relevant name
1. Go delete the S3 bucket with the code

That's it! My tooling keeps everything together.

# Help

If my documentation isn't clear enough, or you have a particular request, just create an 'issue' in this repository.

# TODO

* add S3 bucket name to cookiecutter
* deployment tool should check S3 bucket does versioning
* cloudformation should roll back if the unit tests fail (note: this requires keeping old versions of each zip)
