import os
import sys
import argparse

sys.path.append(os.path.join(sys.path[0], '../'))
from instabot import Bot

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('-u', type=str, help="username")
parser.add_argument('-p', type=str, help="password")
parser.add_argument('-proxy', type=str, help="proxy")
args = parser.parse_args()

bot = Bot()
bot.login(username=args.u, password=args.p,
          proxy=args.proxy)

# Like all users that viewed your first story
# If the optional parameter is passed, only the first amount_of_users_to_like are taken
bot.like_self_story_viewers(amount_of_users_to_like=None)
