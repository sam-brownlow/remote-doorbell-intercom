from abc import ABC, abstractmethod
import logging
from pathlib import Path
import os
import runpy
import sys
import warnings

import aubio
import sounddevice

from lib.utils import AssertContextFunc


class Stream(ABC):
  """
    An abstract class that streams blocks of audio data
  """
  
  def __init__(
    self,
    *,
    sample_rate=44100,
    block_size=1024,
    num_channels=1,
  ):
    self.sample_rate = sample_rate
    self.block_size = block_size
    self.num_channels = num_channels
    
    self._stream = None
    self._data = None
    self._num_blocks_read = 0

  def __enter__(self):
    self.open()
    return self

  def __exit__(self):
    self.close()

  @abstractmethod
  def _open(self):
    """
      Open the stream and assign it to self._stream
      :return: None
    """
    pass

  @abstractmethod
  def _close(self):
    """
      Close the stream and set self._stream to None
      :return: None
    """
    pass

  @abstractmethod
  def _read(self):
    """
      :return: the next block of block of audio data
    """
    pass

  @abstractmethod
  def _is_depleted(self):
    """
      :return: True if the stream has ended
               else return False
    """
    pass

  @property
  def stream(self):
    return self._stream

  @property
  def data(self):
    """
      :return: the last block of data returned from self.read()
    """
    return self._data

  @property
  def num_blocks_read(self):
    return self._num_blocks_read

  @property
  def num_seconds_read(self):
    raise Exception('need to calculate this from _num_blocks_read and the audio info')

  @property
  def is_depleted(self):
    return self._is_depleted()

  @AssertContextFunc(does_set=True, attribute='_stream')
  def open(self):
    self._open()

  @AssertContextFunc(sets_to_none=True, attribute='_stream')
  def close(self):
    self._close()
    self._data = None

  def iter_read(self):
    while True:
      if self.is_depleted():
        break
      yield self.read()
  
  def read(self):
    self._data = self._read()
    self._num_blocks_read += 1
    return self._data
  

class Microphone(Stream):
  """
    A live microphone stream
    
    todo: this class could be improved to handle input selection;
           it currently defaults to the system
  """
  
  def __init__(self, *args, dtype='float32', **kwargs):
    super().__init__(*args, **kwargs)
    self.dtype = dtype
  
  def _open(self):
    stream = sounddevice.InputStream(
      samplerate=self.sample_rate,
      blocksize=self.block_size,
      channels=self.num_channels,
      dtype=self.dtype,
    )
    stream.start()
    
    self._stream = stream
  
  def _close(self):
    if not self._stream.stopped:
      self._stream.stop()
    
    if not self._stream.closed:
      self._stream.close()
    
    self._stream = None
  
  def _read(self):
    return self._stream.read(self.block_size)
  
  def _is_depleted(self):
    return False


class File(Stream):
  """
    Audio streamed from a file
  """
  
  def __init__(self, *args, file_path, **kwargs):
    super().__init__(*args, **kwargs)
    self.file_path = file_path
    self._last_read_size = None
  
  def _open(self):
    self._stream = aubio.source(
      self.file_path,
      samplerate=self.sample_rate,
      hop_size=self.block_size,
      channels=self.num_channels,
    )
  
  def _close(self):
    self._stream.close()
    self._stream = None
  
  def _read(self):
    data, self._last_read_size = self._stream()
    return data

  def _is_depleted(self):
    return (
      self._last_read_size is not None
      and self._last_read_size < self.block_size
    )


class Pitch:
  def __init__(
    self,
    audio_stream,
    *,
    model='yin',
    tolerance=0.8,
    block_size_multiple=0.5,
  ):
    self.audio_stream = audio_stream
    self.model = model
    self.tolerance = tolerance
    self.block_size_multiple = block_size_multiple

    self._aubio_pitch = None
    self._cached_confidence = {}
  
  @AssertContextFunc(does_set=True, attribute='_aubio_pitch')
  def open(self):
    self._aubio_pitch = aubio.pitch(
      method=self.model,
      hop_size=int(self.audio_stream.block_size * self.block_size_multiple),
      buf_size=self.audio_stream.block_size,
      samplerate=self.audio_stream.sample_rate
    )
    self._aubio_pitch.set_tolerance(self.tolerance)
  
  def __enter__(self):
    self.open()
    return self
  
  @AssertContextFunc(sets_to_none=True, attribute='_aubio_pitch')
  def close(self):
    self._aubio_pitch = None
  
  def __exit__(self):
    self.close()
  
  def process_data(self):
    return self._aubio_pitch(self.audio_stream.data)
  
  def fetch_confidence(self):
    cached_confidence = self._cached_confidence.get(self.audio_stream.num_blocks_read)
    if cached_confidence is None:
      cached_confidence = self._aubio_pitch.get_confidence()
      self._cached_confidence = {
        self.audio_stream.num_blocks_read: cached_confidence
      }
    
    return cached_confidence


def _ensure_aubio_demos_in_path():
  aubio_demos_path = os.path.join(
    Path().absolute(),
    'submodules/aubio/python/demos'
  )
  
  if aubio_demos_path not in sys.path:
    assert os.path.isdir(aubio_demos_path), (
      "There is no directory at '{}'\n"
      'Be sure you ran `git submodule init && git submodule update`'
      ''.format(aubio_demos_path)
    )
  
    sys.path.append(aubio_demos_path)


def plot_audio_file_pitch_confidence(file_path, sample_rate):
  """
    Uses matplotlib, via aubio's `demo_pitch.py`,
    to plot an audio file's pitch confidence over time
  """
  
  argv_bak = sys.argv
  sys.argv = [
    argv_bak[0],
    file_path,
    sample_rate,
  ]

  try:
    exit_bak = sys.exit
    sys.exit = lambda *args, **kwargs: logging.debug('Intercepted sys.exit(*{}, **{})'.format(args, kwargs))
    
    try:
      with warnings.catch_warnings():
        _ensure_aubio_demos_in_path()
        warnings.filterwarnings('ignore', category=UserWarning)

        runpy.run_module(
          'demo_pitch',
          run_name='__main__',
          alter_sys=True,
        )
    finally:
      sys.exit = exit_bak
  finally:
    sys.argv = argv_bak
