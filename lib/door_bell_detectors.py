from abc import ABC, abstractmethod
from collections import deque
import time

from lib.audio import Pitch


class DoorbellDetector(ABC):
  """
    An abstract class that takes an audio stream as input
      and detects when your doorbell is ringing
  """
  
  def __init__(self, *, audio_stream):
    self.audio_stream = audio_stream
  
  @abstractmethod
  def is_ringing(self):
    """
      Iterate over the audio stream until ringing is detected
    
      :return: True when the ringing is detected
               or False if the stream ends before a ring is detected
    """
    pass


class AiPhoneGT1A(DoorbellDetector):
  """
    Detect the ring from an Aiphone GT-1A intercom
    
    https://www.aiphone.com/home/products/gt-1a
  """
  
  def __init__(
    self,
    *args,
    min_ringing_confidence=0.45,
    max_ringing_confidence=0.75,
    pitch_confidences_per_second=86,
    ringing_seconds=1.8,
    gap_seconds=1.8,
    max_wait_gap_multiple=2,
    max_wait_subsequent_ring_multiple=2,
    **kwargs
  ):
    """
      :param args:   The args   to pass to DoorbellDetector()
      :param kwargs: The kwargs to pass to DoorbellDetector()
      
      :param min_ringing_confidence: the minimum end of the range
         of confidence values that is considered as ringing

      :param max_ringing_confidence: the maximum end of the range
         of confidence values that is considered as ringing

      :param pitch_confidences_per_second: the number of
         `pitch_confidences` that cover 1 second of audio

      :param ringing_seconds: the number of seconds that the audio
         must have an average pitch confidence within the min<->max
         range for the ringing to be triggered as having been fully
         detected

      :param gap_seconds: the number of seconds that the audio
         must have an average pitch confidence *not* within the min<->max
         range for the ringing to be triggered as having been fully
         detected

      :param max_wait_gap_multiple:
          allow `gap_seconds * max_wait_gap_multiple` seconds
          for a gap to be detected after a single ring is detected
      
      :param max_wait_subsequent_ring_multiple:
          allow `gap_seconds * max_wait_gap_multiple` seconds
          for a ring to be detected subsequent to the detection of a
          single ring followed by a single gap
    """
    
    super().__init__(*args, **kwargs)
    
    self.min_ringing_confidence = min_ringing_confidence
    self.max_ringing_confidence = max_ringing_confidence
    self.pitch_confidences_per_second = pitch_confidences_per_second
    self.ringing_seconds = ringing_seconds
    self.gap_seconds = gap_seconds
    self.max_wait_gap_multiple = max_wait_gap_multiple
    self.max_wait_subsequent_ring_multiple = max_wait_subsequent_ring_multiple
    
    self.audio_pitch = Pitch(
      audio_stream=self.audio_stream,
    )
  
  def is_ringing(self):
    with self.audio_stream:
      with self.audio_pitch:
        while not self.audio_stream.is_depleted:
          if self._is_ringing():
            return True
          
    return False
  
  def _is_ringing(self):
    """
      This is the high level algorithm:
        Iterate over pitch confidences and detect a full "ring cycle"
      A "ring cycle" is <ringing> <pause> <ringing>
    """
  
    return (
      self._detect_single_ring()
      and self._detect_single_gap(max_wait_seconds_multiple=self.max_wait_gap_multiple)
      and self._detect_single_ring(max_wait_seconds_multiple=self.max_wait_subsequent_ring_multiple)
    )
  
  def _iter_confidences(self):
    for _ in self.audio_stream.read_iter():
      self.audio_pitch.process_data()
      yield self.audio_pitch.fetch_confidence()
  
  def _detect_single_ring(self, max_wait_seconds_multiple=None):
    """
      Iterate pitch confidences and detect when ringing is heard

      A ring being detected means that the audio, at some point,
         has an average pitch confidence within the min<->max
         confidence range, over a period of `ringing_seconds`

      :param max_wait_seconds_multiple: optional param that, if set, will
        cause the detection to abort if we reach:
          start_time + ringing_seconds * max_wait_seconds_multiple

      :return: True if a ring is detected else False
    """

    if max_wait_seconds_multiple is None:
      max_wait_time = None
    else:
      max_wait_time = time.time() + self.ringing_seconds * max_wait_seconds_multiple
  
    num_confidences_to_average = int(self.pitch_confidences_per_second * self.ringing_seconds)
    dq = deque(
      (0 for _ in range(num_confidences_to_average)),
      maxlen=num_confidences_to_average
    )
  
    for pitch_confidence in self._iter_confidences():
      dq.append(pitch_confidence)
      avg_confidence = sum(dq) / num_confidences_to_average
      if self.min_ringing_confidence <= avg_confidence <= self.max_ringing_confidence:
        return True
      if max_wait_time and (time.time() >= max_wait_time):
        return False
  
    return False
  
  def _detect_single_gap(self, max_wait_seconds_multiple=None):
    """
      Iterate pitch confidences and detect when ringing is *not* heard

      A gap being detected means that the audio, at some point,
         has an average pitch confidence outside the min<->max
         confidence range, over a period of `gap_seconds`

      :param max_wait_seconds_multiple: optional param that, if set, will
        cause the detection to abort if we reach:
          start_time + gap_seconds * max_wait_seconds_multiple

      :return: True if a gap is detected else False
    """
  
    if max_wait_seconds_multiple is None:
      max_wait_time = None
    else:
      max_wait_time = time.time() + self.gap_seconds * max_wait_seconds_multiple
  
    average_ring_confidence = (self.min_ringing_confidence + self.max_ringing_confidence) / 2
  
    num_confidences_to_average = int(self.pitch_confidences_per_second * self.gap_seconds)
    dq = deque(
      (average_ring_confidence for _ in range(num_confidences_to_average)),
      maxlen=num_confidences_to_average
    )
  
    for pitch_confidence in self._iter_confidences():
      dq.append(pitch_confidence)
      avg_confidence = sum(dq) / num_confidences_to_average
      if not (self.min_ringing_confidence <= avg_confidence <= self.max_ringing_confidence):
        return True
      if max_wait_time and (time.time() >= max_wait_time):
        return False
  
    return False
