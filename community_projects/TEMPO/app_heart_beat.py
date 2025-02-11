import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import bpm_measurement

import numpy as np
import requests
import tqdm

import MIDI
from midi_model import MIDIModel
from midi_synthesizer import MidiSynthesizer
from sound_stream import generate_wav, play_wav

MAX_SEED = np.iinfo(np.int32).max
OUTPUT_BATCH_SIZE = 1

number2drum_kits = {-1: "None", 0: "Standard", 8: "Room", 16: "Power", 24: "Electric", 25: "TR-808", 32: "Jazz",
                    40: "Blush", 48: "Orchestra"}
patch2number = {v: k for k, v in MIDI.Number2patch.items()}
drum_kits2number = {v: k for k, v in number2drum_kits.items()}
key_signatures = ['C♭', 'A♭m', 'G♭', 'E♭m', 'D♭', 'B♭m', 'A♭', 'Fm', 'E♭', 'Cm', 'B♭', 'Gm', 'F', 'Dm',
                  'C', 'Am', 'G', 'Em', 'D', 'Bm', 'A', 'F♯m', 'E', 'C♯m', 'B', 'G♯m', 'F♯', 'D♯m', 'C♯', 'A♯m']


def run(model, tokenizer, tab, mid_seq, continuation_state, continuation_select, instruments, drum_kit, bpm, time_sig, key_sig, mid,
        midi_events,  reduce_cc_st, remap_track_channel, add_default_instr, remove_empty_channels, seed, seed_rand,
        gen_events, temp, top_p, top_k, allow_cc):
    bpm = int(bpm)
    if time_sig == "auto":
        time_sig = None
        time_sig_nn = 4
        time_sig_dd = 2
    else:
        time_sig_nn, time_sig_dd = time_sig.split('/')
        time_sig_nn = int(time_sig_nn)
        time_sig_dd = {2: 1, 4: 2, 8: 3}[int(time_sig_dd)]
    if key_sig == 0:
        key_sig = None
        key_sig_sf = 0
        key_sig_mi = 0
    else:
        key_sig = (key_sig - 1)
        key_sig_sf = key_sig // 2 - 7
        key_sig_mi = key_sig % 2
    gen_events = int(gen_events)
    max_len = gen_events
    if seed_rand:
        seed = np.random.randint(0, MAX_SEED)
    generator = np.random.default_rng(seed)
    disable_patch_change = False
    disable_channels = None
    if tab == 0:
        i = 0
        mid = [[tokenizer.bos_id] + [tokenizer.pad_id] * (tokenizer.max_token_seq - 1)]
        if tokenizer.version == "v2":
            if time_sig is not None:
                mid.append(tokenizer.event2tokens(["time_signature", 0, 0, 0, time_sig_nn - 1, time_sig_dd - 1]))
            if key_sig is not None:
                mid.append(tokenizer.event2tokens(["key_signature", 0, 0, 0, key_sig_sf + 7, key_sig_mi]))
        if bpm != 0:
            mid.append(tokenizer.event2tokens(["set_tempo", 0, 0, 0, bpm]))
        patches = {}
        if instruments is None:
            instruments = []
        for instr in instruments:
            patches[i] = patch2number[instr]
            i = (i + 1) if i != 8 else 10
        if drum_kit != "None":
            patches[9] = drum_kits2number[drum_kit]
        for i, (c, p) in enumerate(patches.items()):
            mid.append(tokenizer.event2tokens(["patch_change", 0, 0, i + 1, c, p]))
        mid = np.asarray([mid] * OUTPUT_BATCH_SIZE, dtype=np.int64)
        mid_seq = mid.tolist()
        if len(instruments) > 0:
            disable_patch_change = True
            disable_channels = [i for i in range(16) if i not in patches]
    elif tab == 1 and mid is not None:
        eps = 4 if reduce_cc_st else 0
        mid = tokenizer.tokenize(MIDI.midi2score(mid), cc_eps=eps, tempo_eps=eps,
                                 remap_track_channel=remap_track_channel,
                                 add_default_instr=add_default_instr,
                                 remove_empty_channels=remove_empty_channels)
        mid = mid[:int(midi_events)]
        mid = np.asarray([mid] * OUTPUT_BATCH_SIZE, dtype=np.int64)
        mid_seq = mid.tolist()
    elif tab == 2 and mid_seq is not None:
        mid = np.asarray(mid_seq, dtype=np.int64)
        if continuation_select > 0:
            continuation_state.append(mid_seq)
            mid = np.repeat(mid[continuation_select - 1:continuation_select], repeats=OUTPUT_BATCH_SIZE, axis=0)
            mid_seq = mid.tolist()
        else:
            continuation_state.append(mid.shape[1])
    else:
        continuation_state = [0]
        mid = [[tokenizer.bos_id] + [tokenizer.pad_id] * (tokenizer.max_token_seq - 1)]
        mid = np.asarray([mid] * OUTPUT_BATCH_SIZE, dtype=np.int64)
        mid_seq = mid.tolist()

    if mid is not None:
        max_len += mid.shape[1]

    midi_generator = model.generate(mid, batch_size=OUTPUT_BATCH_SIZE, max_len=max_len, temp=temp,
                                    top_p=top_p, top_k=top_k, disable_patch_change=disable_patch_change,
                                    disable_control_change=not allow_cc, disable_channels=disable_channels,
                                    generator=generator)
    for i, token_seqs in enumerate(midi_generator):
        token_seqs = token_seqs.tolist()
        for j in range(OUTPUT_BATCH_SIZE):
            token_seq = token_seqs[j]
            mid_seq[j].append(token_seq)
    return mid_seq, continuation_state, seed


def finish_run(mid_seq, tokenizer):
    if mid_seq is None:
        outputs = [None] * OUTPUT_BATCH_SIZE
        return outputs
    outputs = []
    if not os.path.exists("outputs"):
        os.mkdir("outputs")
    for i in range(OUTPUT_BATCH_SIZE):
        mid = tokenizer.detokenize(mid_seq[i])
        with open(f"outputs/output{i + 1}.mid", 'wb') as f:
            f.write(MIDI.score2midi(mid))
        outputs.append(f"outputs/output{i + 1}.mid")
    return outputs


def synthesis_task(mid, synthesizer, is_first_batch):
    return synthesizer.synthesis(MIDI.score2opus(mid), is_first_batch, is_stream=True)


def render_audio(mid_seq, should_render_audio, tokenizer, thread_pool, synthesizer):
    if (not should_render_audio) or mid_seq is None:
        outputs = [None] * OUTPUT_BATCH_SIZE
        return tuple(outputs)
    outputs = []
    if not os.path.exists("outputs"):
        os.mkdir("outputs")
    audio_futures = []
    for i in range(OUTPUT_BATCH_SIZE):
        mid = tokenizer.detokenize(mid_seq[i])
        audio_future = thread_pool.submit(synthesis_task, mid, synthesizer, is_first_batch=True)
        audio_futures.append(audio_future)
    for future in audio_futures:
        outputs.append(future.result())
    if OUTPUT_BATCH_SIZE == 1:
        return outputs[0]
    return tuple(outputs)


def load_model():
    model_path_dir = "TEMPO_FILES"
    if not os.path.exists(model_path_dir):
        print("Model not found. Make sure to run ./download_files.sh first.")
        raise FileNotFoundError("Model not found")
    try:
        base_emb = os.path.join(model_path_dir, "model_base_embed_tokens.npy")
        token_emb = os.path.join(model_path_dir, "model_token_embed_tokens.npy")
        model_token = os.path.join(model_path_dir, "model_token.hef")
        model_base = os.path.join(model_path_dir, "model_base.hef")
        model = MIDIModel(model_base, model_token, base_emb, token_emb)
        tokenizer = model.tokenizer
    except Exception as e:
        print(f"Failed to load model")
        raise e
    return model, tokenizer


def download(url, output_file):
    print(f"Downloading {output_file} from {url}")
    response = requests.get(url, stream=True)
    file_size = int(response.headers.get("Content-Length", 0))
    with tqdm.tqdm(total=file_size, unit="B", unit_scale=True, unit_divisor=1024,
                   desc=f"Downloading {output_file}") as pbar:
        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))


def download_if_not_exit(url, output_file):
    if os.path.exists(output_file):
        return
    try:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        download(url, output_file)
    except Exception as e:
        print(f"Failed to download {output_file} from {url}")
        raise e


def get_instruments(bpm):
    if bpm <= 80:
        return ['Flute', 'French Horn', 'Clarinet', 'String Ensemble 2', 'English Horn', 'Bassoon', 'Oboe', 'Pizzicato Strings'], "Orchestra"
    elif bpm <= 100:
        return ['Acoustic Grand', 'SynthStrings 2', 'SynthStrings 1', 'Pizzicato Strings', 'Pad 2 (warm)', 'Tremolo Strings', 'String Ensemble 1'], "Orchestra"
    elif bpm <= 120:
        return ["Electric Guitar(clean)", "Electric Guitar(muted)", "Overdriven Guitar", "Distortion Guitar", "Electric Bass(finger)"], "Standard"
    return ['Electric Piano 2', 'Lead 5 (charang)', 'Electric Bass(pick)', 'Lead 2 (sawtooth)', 'Pad 1 (new age)', 'Orchestra Hit', 'Cello', 'Electric Guitar(clean)'], "Standard"


def main():
    download_if_not_exit("https://huggingface.co/skytnt/midi-model/resolve/main/soundfont.sf2", "soundfont.sf2")
    synthesizer = MidiSynthesizer("soundfont.sf2")
    thread_pool = ThreadPoolExecutor(max_workers=OUTPUT_BATCH_SIZE)
    model, tokenizer = load_model()
    
    continuation_state = [0]
    tab = 0
    
    while True:
        bpm = bpm_measurement.get_bpm()
        instruments, drum_set = get_instruments(bpm)
        output_midi_seq, continuation_state, input_seed = run(model, tokenizer, tab, None, continuation_state, 0, instruments, drum_set, bpm, "auto", 0, None, None,  None, None, None, None, None, True, 128, 1.0, 0.94, 20, True)
        midi_outputs = finish_run(output_midi_seq, tokenizer)
        audio_outputs = render_audio(output_midi_seq, True, tokenizer, thread_pool, synthesizer)
        tab = 0
        path = generate_wav(audio_outputs)
        play_wav(path)


if __name__ == '__main__':
    main()