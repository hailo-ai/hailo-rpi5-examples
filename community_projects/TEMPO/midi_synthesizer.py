from threading import Lock

import fluidsynth
import numpy as np
import struct


class MidiSynthesizer:
    def __init__(self, soundfont_path, sample_rate=44100):
        self.soundfont_path = soundfont_path
        self.sample_rate = sample_rate
        self.fl = fluidsynth.Synth(samplerate=float(sample_rate))
        self.sfid = self.fl.sfload(soundfont_path)
        self.devices = [[self.fl, self.sfid, False]]
        self.devices_lock = Lock()
        self.tempo = int((60 / 120) * 10 ** 6)  # default 120 bpm
        self.ticks_per_beat = 480
        self.curr_device = None

    def get_fluidsynth(self):
        with self.devices_lock:
            for device in self.devices:
                if not device[2]:
                    device[2] = True
                    return device
            fl = fluidsynth.Synth(samplerate=float(self.sample_rate))
            sfid = fl.sfload(self.soundfont_path)
            device = [fl, sfid, True]
            self.devices.append(device)
            return device

    def release_fluidsynth(self, device):
        device[0].system_reset()
        device[0].get_samples(self.sample_rate*5) # wait for silence
        device[2] = False

    def synthesis(self, midi_opus, is_first_batch, is_stream):
        event_list = []
        if is_first_batch:
            if self.curr_device:
                self.release_fluidsynth(self.curr_device)
            self.ticks_per_beat = midi_opus[0]
            midi_opus = midi_opus[1:]

            self.curr_device = self.get_fluidsynth()
            self.fl, self.sfid = self.curr_device[:-1]
            self.last_t = 0
            for c in range(16):
                self.fl.program_select(c, self.sfid, 128 if c == 9 else 0, 0)
        for track in midi_opus:
            abs_t = 0
            for event in track:
                abs_t += event[1]
                event_new = [*event]
                event_new[1] = abs_t
                event_list.append(event_new)
        event_list = sorted(event_list, key=lambda e: e[1])

        pcm = b""
        all_samples = np.empty((0, 2), dtype=np.int16)
        for event in event_list:
            name = event[0]
            sample_len = int(((event[1] / self.ticks_per_beat) * self.tempo / (10 ** 6)) * self.sample_rate)
            sample_len -= int(((self.last_t / self.ticks_per_beat) * self.tempo / (10 ** 6)) * self.sample_rate)
            self.last_t = event[1]
            if sample_len > 0:
                samples = self.fl.get_samples(sample_len).reshape(sample_len, 2)
                all_samples = np.concatenate([all_samples, samples])
                pcm += b''.join([struct.pack('<hh', sample[0], sample[1]) for sample in samples])
            if name == "set_tempo":
                self.tempo = event[2]
            elif name == "patch_change":
                c, p = event[2:4]
                self.fl.program_select(c, self.sfid, 128 if c == 9 else 0, p)
            elif name == "control_change":
                c, cc, v = event[2:5]
                self.fl.cc(c, cc, v)
            elif name == "note_on" and event[3] > 0:
                c, p, v = event[2:5]
                self.fl.noteon(c, p, v)
            elif name == "note_off" or (name == "note_on" and event[3] == 0):
                c, p = event[2:4]
                self.fl.noteoff(c, p)
        if is_stream:
            return pcm
        else:
            return all_samples

