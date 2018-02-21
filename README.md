# Matt's Reddit Bot Template

This is a template for making reddit bots in python, and deploying them to AWS Lambda.

## Why Use This Template

TODO: write this (I'll get around to this in a week)

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

TODO: explain flags to speed up deployment

Submit a post in r/bottest and wait for the bot to respond. It's currently polling for new posts every 10 minutes.
If you don't want to wait for 10 minutes:

* log into the AWS console in a browser
* go to Lambda
* search for `checkForNew`
* Select the corresponding lambda
* trigger it (you'll have to set up a 'test' configuration. This is fairly straightforward. Just use the default payload, or an empty payload.)
* If you see red in the console, read the error message there, then redeploy. For more advanced debugging methods, read 'Debugging and logs'

**After** thorough testing, the subreddit the bot browses in can be changed by going into `data/cloudformation/stack.yaml`. Search for `subreddits`. 
Replace `"bottest"` with your new subreddit name(s).
If you want the bot to be active in multiple subreddits, seperate them with a comma. Leave off the "r/"

## Debugging and Logs

## How it works

TODO: write this (I'll get around to it within a fortnight)

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

That's it! My tooling keeps everything together.

