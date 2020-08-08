from utils import configure_logging
configure_logging()

from utils import load_conf_to_env_vars
load_conf_to_env_vars()


if __name__ == '__main__':
  """
    This will eventually...
    
    1) detect when the door bell is buzzing
    2) initiate a phone call via twilio
    3) allow the user to answer the bell, over the phone, and communicate with the intercom's audio
    4) allow the user to then unlock the door if they choose to
  """