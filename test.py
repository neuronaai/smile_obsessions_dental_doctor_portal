import pyttsx3

engine = pyttsx3.init()


voices = engine.getProperty('voices')
for v in voices:
    print(v.id)
engine.setProperty('voice', voices[1].id)

engine.say("Testing, 1 2 3. Hello from pyttsx3!")
engine.runAndWait()