# https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account#verify-your-personal-phone-number
# https://www.twilio.com/blog/design-phone-survey-system-python-google-sheets-twilio

import base64
import os

from flask import Flask, Response, url_for
from flask_socketio import emit, SocketIO
from pyngrok import ngrok
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, Start, VoiceResponse


"""  NOTES
  gather example

    response = VoiceResponse()

    with response.gather(
      num_digits=1,
      action=url_for_domain(
        domain=NGROK_HTTP_DOMAIN,
        endpoint='/doorbell/answered'
      ),
      method='POST'
    ) as g:
      g.say(
        message=(
          'Ring ring... someone is at the front door. '
          'If you are expecting a visitor '
          'then enter any number to unlock the door to the building. '
          'Otherwise, hang up to keep the door locked.'
        ),
        loop=2,
        voice=TWILIO_VOICE
      )

      return twiml(response)


  websocket events

    receivable_events = (
      'connected',
      'start',
      'media',
      'stop',
      'mark',
    )

    sendable_events = (
      'media',
      'mark',
      'clear',
    )

"""


TWILIO_VOICE = 'alice'
TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
TWILIO_FROM_NUMBER = os.environ['TWILIO_FROM_NUMBER']

FLASK_SECRET_KEY = os.environ['FLASK_SECRET_KEY']
FLASK_PORT = 5000

NGROK_HTTP_DOMAIN = ngrok.connect(
  port=FLASK_PORT
)
NGROK_WSS_DOMAIN = ngrok.connect(
  port=FLASK_PORT,
  proto='wss',
)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config.update({
 'PREFERRED_URL_SCHEME': 'https',
})
socketio = SocketIO(app)


def twiml(twilio_response):
  # take a `twilio_response` value, e.g. `VoiceResponse`,
  # and give the flask route return value
  flask_response = Response(str(twilio_response))
  flask_response.headers['Content-Type'] = 'text/xml'
  return flask_response


def url_for_domain(*, domain, endpoint):
  # return a join of the `domain` and `endpoint`
  flask_path = url_for(endpoint)

  return '/'.join((
    domain.strip('/'),
    flask_path.strip('/')
  ))


def doorbell_ring(to_phone):
  # ring the `to_phone` number to initiate doorbell communication
  # response handled by `doorbell_answered`
  client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
  return client.calls.create(
    to=to_phone,
    from_=TWILIO_FROM_NUMBER,
    status_callback=url_for_domain(
      domain=NGROK_HTTP_DOMAIN,
      endpoint='/doorbell/answered'
    ),
    status_callback_event='answered',
    status_callback_method='POST'
  )

@app.route('/doorbell/answered', methods=['POST'])
def doorbell_answered():
  # the `doorbell_ring` has been answered by the `to_phone`
  # initiate a bi-directional stream to be communicated over websocket

  response = VoiceResponse()

  start = Start()
  start.stream(
    url=url_for_domain(
      domain=NGROK_WSS_DOMAIN,
      endpoint='/doorbell/stream'
    ),
    track='both_tracks'
  )
  response.append(start)
  return twiml(response)

_cache = {
  'stream_sid': None,
}
@socketio.on('start', namespace='/doorbell/stream')
def doorbell_audio_track_started(data):
  assert _cache['stream_sid'] is None, "_cache['stream_sid'] == '{}'".format(_cache['stream_sid'])

  _cache['stream_sid'] = data['start']['streamSid']

@socketio.on('media', namespace='/doorbell/stream')
def doorbell_audio_track_media(_data):
  assert _cache['stream_sid'] is not None, "_cache['stream_sid'] is None for data of {}".format(_data)

  emit(
    'media',
    {
      'streamSid': 'xxxxxxx',
      'media': {
        'payload': base64.b64encode(
          # raw mulaw/8000
        )
      }

    }
  )

@app.route('/doorbell/response', methods=['POST'])
def doorbell_response():
  response = VoiceResponse()
  with response.gather(
    num_digits=1,
    action=url_for('question_two'),
    method="POST"
  ) as g:
    g.say(
      'Question one. Do you own or rent a house? Please press 1 if you own a house or 2 if you rent a house',
      loop=2,
      voice=TWILIO_VOICE
    )

    return twiml(response)

