import pyttsx3

def play_sound(sentence):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[1].id)  # Change index to select different voices
    engine.setProperty('rate', 100)  # Speed of speech
    engine.setProperty('volume', 11)  # Volume from 0.0 to 1.0
    engine.say(sentence)
    engine.runAndWait()
    