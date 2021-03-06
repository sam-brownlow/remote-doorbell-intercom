from argparse import ArgumentParser
import logging
import os
from pathlib import Path
from lib.utils import configure_logging, load_conf_to_env_vars
from lib import audio, door_bell_detectors


def main_kwargs():
  arg_parser = ArgumentParser()
  
  arg_parser.add_argument('-door_bell_detector', '--door_bell_detector', type=str, default='AiPhoneGT1A')
  arg_parser.add_argument('-conf_path', '--conf_path', type=str, default=os.path.join(Path().absolute(), 'conf.json'))
  arg_parser.add_argument('-log_level', '--log_level', type=str, default='INFO')
  arg_parser.add_argument('-audio_file_path', '--audio_file_path', type=str)
  
  kwargs = vars(arg_parser.parse_args())
  kwargs['log_level'] = logging._checkLevel(kwargs['log_level'].upper())
  
  return kwargs


def main(*, conf_path, log_level, door_bell_detector, audio_file_path=None):
  load_conf_to_env_vars(json_path=conf_path)
  configure_logging(level=log_level)
  
  audio_stream = (
    audio.Microphone()
    if audio_file_path is None
    else audio.File(file_path=audio_file_path)
  )
  
  doorbell_detector_class = getattr(door_bell_detectors, door_bell_detector)
  doorbell_detector_instance = doorbell_detector_class(audio_stream=audio_stream)
  logging.info('Listening via doorbell detector of {}'.format(doorbell_detector_instance))
  
  if doorbell_detector_instance.is_ringing():
    print('the doorbell is ringing')


if __name__ == '__main__':
  """
    This will eventually...
    
    [done] 1) detect when the door bell is buzzing
    [todo] 2) initiate a phone call via twilio
    [todo] 3) allow the user to answer the bell, over the phone, and communicate with the intercom's audio
    [todo] 4) allow the user to then unlock the door if they choose to
  """

  main(**main_kwargs())
