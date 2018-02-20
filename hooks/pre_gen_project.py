import re

bot_name = "{{cookiecutter.bot_name}}"

MODULE_REGEX = r'^[a-zA-Z][-a-zA-Z0-9]+$'

if not re.match(MODULE_REGEX, bot_name):
    print('ERROR: %s is not a valid AWS resource prefix' % bot_name)
    print('Please choose a bot name which contains only letters, numbers, dashes and start with an alpha character')

    # exits with status 1 to indicate failure
    sys.exit(1)
