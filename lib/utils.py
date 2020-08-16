import functools
import json
import logging
import os
import sys
import time


sys_excepthook_bak = sys.excepthook
def configure_logging(*, level):
  assert sys.excepthook == sys_excepthook_bak, (
    "Logging has already been configured"
  )
  
  logging.Formatter.converter = time.gmtime
  logging.basicConfig(
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S-00:00',  # '-00:00' implied by `logging.Formatter.converter = time.gmtime`
    level=level
  )

  def sys_excepthook(*args, **kwargs):
    # https://stackoverflow.com/a/6234491
    logging.exception('UNHANDLED EXCEPTION')
    return sys_excepthook_bak(*args, **kwargs)
  
  sys.excepthook = sys_excepthook


def load_conf_to_env_vars(*, json_path):
  """
    Maps the key:values found in `json_path` to environment variables
    
    :param json_path: the path to the json file
    :return: None
  """
  
  with open(json_path, 'r') as json_file:
    conf = json.load(json_file)
  
  d = {}
  for k, v in conf.items():
    assert isinstance(v, str), (
      "Expected value to be a string, but found type of '{}' for key of '{}' in file at '{}'"
      ''.format(
        type(v),
        k,
        json_path,
      )
    )
    
    if k in os.environ:
      assert os.environ[k] == v, (
        "There is already an environment variable named '{}', with a different value "
        "than the value for key of '{}' in file at '{}'"
        ''.format(
          k,
          k,
          json_path,
        )
      )
    else:
      d[k] = v
  
  os.environ.update(**d)


class AssertContextFunc(object):
  """
    A decorator that ensures that a class's context method correctly
      handles the before-and-after values of `attribute`, depending
      on if the method...
        (1) `does_set` the `attribute`
        or
        (2) `sets_to_none` the `attribute`
    
    Usage example:
    
      class This:
        def __init__(self):
          self._that = None
        
        @AssertContextFunc(does_set=True, attribute='_that')
        def open(self):
          self._that = 123
          
        @AssertContextFunc(sets_to_none=True, attribute='_that')
        def close(self):
          self._that = None
  """
  
  def __init__(self, *, attribute, does_set=None, sets_to_none=None):
    assert (does_set is None) != (sets_to_none is None), (
      "must specify exactly 1 non-None, boolean value for kwarg 'does_set' or 'sets_to_none'"
    )
    
    self._attribute = attribute
    self._does_set = does_set is not None
  
  def __call__(self, caching_func):
    @functools.wraps(caching_func)
    def decorated(self_of_caching_func, *args, **kwargs):
      attr_val_is_none = getattr(self_of_caching_func, self._attribute) is None
      assert attr_val_is_none == self._does_set, (
        "self.{} is *{}* priorly defined for *{}* via method '{}' in {}"
        ''.format(
          self._attribute,
          'already' if self._does_set else 'not',
          'setting' if self._does_set else 'setting to None',
          caching_func.__name__,
          self_of_caching_func,
        )
      )
      
      caching_func(self_of_caching_func, *args, **kwargs)
      
      attr_val_is_not_none = getattr(self_of_caching_func, self._attribute) is not None
      assert attr_val_is_not_none == self._does_set, (
        "self.{} is *{}* subsequently defined from *{}* via method '{}' in {}"
        ''.format(
          self._attribute,
          'not' if self._does_set else 'still',
          'setting' if self._does_set else 'setting to None',
          caching_func.__name__,
          self_of_caching_func,
        )
      )
    
    return decorated
