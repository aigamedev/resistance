import threading
import subprocess

import speech_recognition as speech


class SpeechMixin(object):
    """Support for voice interactions as both input with speech-to-text and output with
    text-to-speech.  Derive your Bot from this mixin class to expose this functionality
    to all your AI functions.
    """

    def __init__(self, voice='Zarvox', audio_threshold=1000):
        # Use a robotic voice by default to output the message.  Pick your bot's name
        # carefully as not all names (or voice names) are recognized by the speech API.
        self.voice = voice

        # The threshold of the recognizer is very important for the speech library
        # to be able to segment audio into utterances.  If it's a loud room you may
        # have to bump it up to 4000, otherwise 1000 seems reasonable if you speak
        # clearly into the microphone.
        self.recognizer = speech.Recognizer()
        self.recognizer.energy_threshold = audio_threshold
        self._stop = False

        self.thread = threading.Thread(target=self.listen)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self._stop = True
        self.thread.join()

    def speak(self, message):
        subprocess.call(['/usr/bin/say', '-v', self.voice, message])

    def listen(self):
        for st in self.sentences():
            self.onMessage(source=None, message=st)

    def sentences():
        while not self._stop:
            with speech.Microphone() as source:
                audio = self.recognizer.listen(source)
                self.log.debug("Received %i bytes of audio data." % len(audio.data))

            try:
                sentence = self.recognizer.recognize(audio)
                self.log.debug("Understood: %s" % sentence)
                yield sentence

            except LookupError:
                self.log.debug("Could not understand.")
