
import simpleaudio as sa
wave_object = sa.WaveObject.from_wave_file('db/icq-message.wav')

# import pickle 
import pickle 

# define an object to control the play
# play_object = wave_object.play()
# play_object.wait_done()


# save the wave object to a pickle file
with open('db/icq.pkl', 'wb') as f:
    pickle.dump(wave_object, f)

