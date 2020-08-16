import os
from switchbotpy import Bot

SWITCHBOT_MAC_ANSWER_BELL = os.environ['SWITCHBOT_MAC_ANSWER_BELL']
SWITCHBOT_MAC_UNLOCK_DOOR = os.environ['SWITCHBOT_MAC_UNLOCK_DOOR']


def answer_doorbell():
  bot = Bot(
    bot_id=0,
    mac=SWITCHBOT_MAC_ANSWER_BELL,
    name='answer_doorbell'
  )
  bot.press()


def unlock_door():
  bot = Bot(
    bot_id=1,
    mac=SWITCHBOT_MAC_UNLOCK_DOOR,
    name='unlock_door'
  )
  bot.press()
