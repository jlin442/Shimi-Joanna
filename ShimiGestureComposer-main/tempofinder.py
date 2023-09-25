def tempo(audio):
    from librosa import beat, onset, load
    import numpy as np

    [x,fs] = load(audio, mono=True)
    x = x/np.abs(x.max())
    onsetenv = onset.onset_strength(y=x, sr=fs)
    bpm, beats = beat.beat_track(y=x, sr=fs, onset_envelope=onsetenv)
    bpm = int(bpm)
    return bpm