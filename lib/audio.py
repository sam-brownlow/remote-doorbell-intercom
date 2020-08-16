from abc import ABC, abstractmethod

import aubio
import sounddevice

from lib.utils import AssertContextFunc


class Stream(ABC):
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

  @property
  def stream(self):
    return self._stream

  @property
  def data(self):
    return self._data

  @property
  def num_blocks_read(self):
    return self._num_blocks_read

  @property
  def num_seconds_read(self):
    raise Exception('need to calculate this from _num_blocks_read and the audio info')
  
  @AssertContextFunc(does_set=True, attribute='_stream')
  def open(self):
    self._open()

  @abstractmethod
  def _open(self):
    # must assign self._stream
    pass

  def __enter__(self):
    self.open()
    return self

  @AssertContextFunc(sets_to_none=True, attribute='_stream')
  def close(self):
    self._close()
    self._data = None

  @abstractmethod
  def _close(self):
    # must set self._stream to None
    pass

  def __exit__(self):
    self.close()
  
  def iter_read(self):
    while True:
      if self.is_depleted():
        break
      yield self.read()
  
  def read(self):
    self._data = self._read()
    self._num_blocks_read += 1
    return self._data
  
  @abstractmethod
  def _read(self):
    pass

  @abstractmethod
  def _is_depleted(self):
    pass

  @property
  def is_depleted(self):
    return self._is_depleted()


class Microphone(Stream):
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
    
    try:
      stream.start()
    except Exception:
      stream.close()
      raise
    
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

