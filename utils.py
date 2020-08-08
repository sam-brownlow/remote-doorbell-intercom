import json
import logging
import os
import sys


sys_excepthook_bak = sys.excepthook
def configure_logging(*, level):
  logging.Formatter.converter = time.gmtime
  logging.basicConfig(
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S-00:00', # '-00:00' implied by `logging.Formatter.converter = time.gmtime`
    level=level
  )

  # log any unhandled exceptions
  def sys_excepthook(*args, **kwargs):
    # https://stackoverflow.com/a/6234491
    logging.exception('UNHANDLED EXCEPTION')
    return sys_excepthook_bak(*args, **kwargs)
  sys.excepthook = sys_excepthook


def load_conf_to_env_vars(json_path=None):
  if json_path is None:
    json_path = os.path.join(
      os.path.dirname(os.path.abspath(__file__)),
      'conf.json'
    )
  
  with open(json_path, 'r') as json_file:
    secrets = json.load(json_file)
  
  for k, v in secrets.items():
    assert k not in os.environ, (
      "There is already an environment variable defined for key of '{}'".format(k)
    )

    os.environ[k] = v
