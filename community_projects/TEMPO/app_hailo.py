import argparse
import glob
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Union, Optional

import gradio as gr
import numpy as np
import requests
import struct
import tqdm

import MIDI
from midi_model import MIDIModel
from midi_synthesizer import MidiSynthesizer
from midi_tokenizer import MIDITokenizerV1, MIDITokenizerV2

MAX_SEED = np.iinfo(np.int32).max


def generate(prompt=None, batch_size=1, max_len=512, temp=1.0, top_p=0.98, top_k=20,
             disable_patch_change=False, disable_control_change=False, disable_channels=None, generator=None):
    for next_token_seq in model.generate(
        prompt=prompt,
        batch_size=batch_size,
        max_len=max_len,
        temp=temp,
        top_p=top_p,
        top_k=top_k,
        disable_patch_change=disable_patch_change,
        disable_control_change=disable_control_change,
        disable_channels=disable_channels,
        generator=generator
    ):
        yield next_token_seq


def create_msg(name, data):
    return {"name": name, "data": data}


def send_msgs(msgs):
    return json.dumps(msgs)


def run(tab, mid_seq, continuation_state, continuation_select, instruments, drum_kit, bpm, time_sig, key_sig, mid,
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

    init_msgs = [create_msg("progress", [0, gen_events])]
    if not (tab == 2 and continuation_select == 0):
        for i in range(OUTPUT_BATCH_SIZE):
            events = [tokenizer.tokens2event(tokens) for tokens in mid_seq[i]]
            init_msgs += [create_msg("visualizer_clear", [i, tokenizer.version]),
                          create_msg("visualizer_append", [i, events])]
    yield mid_seq, continuation_state, seed, send_msgs(init_msgs)
    midi_generator = model.generate(mid, batch_size=OUTPUT_BATCH_SIZE, max_len=max_len, temp=temp,
                                    top_p=top_p, top_k=top_k, disable_patch_change=disable_patch_change,
                                    disable_control_change=not allow_cc, disable_channels=disable_channels,
                                    generator=generator)
    events = [list() for i in range(OUTPUT_BATCH_SIZE)]
    t = time.time()
    for i, token_seqs in enumerate(midi_generator):
        token_seqs = token_seqs.tolist()
        for j in range(OUTPUT_BATCH_SIZE):
            token_seq = token_seqs[j]
            mid_seq[j].append(token_seq)
            events[j].append(tokenizer.tokens2event(token_seq))
        if time.time() - t > 0.2:
            msgs = [create_msg("progress", [i + 1, gen_events])]
            for j in range(OUTPUT_BATCH_SIZE):
                msgs += [create_msg("visualizer_append", [j, events[j]])]
                events[j] = list()
            yield mid_seq, continuation_state, seed, send_msgs(msgs)
            t = time.time()
    yield mid_seq, continuation_state, seed, send_msgs([])


def finish_run(mid_seq):
    if mid_seq is None:
        outputs = [None] * OUTPUT_BATCH_SIZE
        return *outputs, []
    outputs = []
    end_msgs = [create_msg("progress", [0, 0])]
    if not os.path.exists("outputs"):
        os.mkdir("outputs")
    for i in range(OUTPUT_BATCH_SIZE):
        events = [tokenizer.tokens2event(tokens) for tokens in mid_seq[i]]
        mid = tokenizer.detokenize(mid_seq[i])
        with open(f"outputs/output{i + 1}.mid", 'wb') as f:
            f.write(MIDI.score2midi(mid))
        outputs.append(f"outputs/output{i + 1}.mid")
        end_msgs += [create_msg("visualizer_clear", [i, tokenizer.version]),
                     create_msg("visualizer_append", [i, events]),
                     create_msg("visualizer_end", i)]
    return *outputs, send_msgs(end_msgs)


def synthesis_task(mid, is_first_batch):
    return synthesizer.synthesis(MIDI.score2opus(mid), is_first_batch, is_stream=False)


def render_audio(mid_seq, should_render_audio):
    if (not should_render_audio) or mid_seq is None:
        outputs = [None] * OUTPUT_BATCH_SIZE
        return tuple(outputs)
    outputs = []
    if not os.path.exists("outputs"):
        os.mkdir("outputs")
    audio_futures = []
    for i in range(OUTPUT_BATCH_SIZE):
        mid = tokenizer.detokenize(mid_seq[i])
        audio_future = thread_pool.submit(synthesis_task, mid, is_first_batch=True)
        audio_futures.append(audio_future)
    for future in audio_futures:
        outputs.append((44100, future.result()))
    if OUTPUT_BATCH_SIZE == 1:
        return outputs[0]
    return tuple(outputs)


def undo_continuation(mid_seq, continuation_state):
    if mid_seq is None or len(continuation_state) < 2:
        return mid_seq, continuation_state, send_msgs([])
    if isinstance(continuation_state[-1], list):
        mid_seq = continuation_state[-1]
    else:
        mid_seq = [ms[:continuation_state[-1]] for ms in mid_seq]
    continuation_state = continuation_state[:-1]
    end_msgs = [create_msg("progress", [0, 0])]
    for i in range(OUTPUT_BATCH_SIZE):
        events = [tokenizer.tokens2event(tokens) for tokens in mid_seq[i]]
        end_msgs += [create_msg("visualizer_clear", [i, tokenizer.version]),
                     create_msg("visualizer_append", [i, events]),
                     create_msg("visualizer_end", i)]
    return mid_seq, continuation_state, send_msgs(end_msgs)


def load_model():
    global model, tokenizer
    model_path_dir = "TEMPO_FILES"
    if not os.path.exists(model_path_dir):
        return "Model not found. Make sure to run ./download_files.sh first."
    try:
        base_emb = os.path.join(model_path_dir, "model_base_embed_tokens.npy")
        token_emb = os.path.join(model_path_dir, "model_token_embed_tokens.npy")
        model_token = os.path.join(model_path_dir, "model_token.hef")
        model_base = os.path.join(model_path_dir, "model_base.hef")
        model = MIDIModel(model_base, model_token, base_emb, token_emb)
        tokenizer = model.tokenizer
    except Exception as e:
        print(f"Failed to load model")
        return e
    return "success"


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


def load_javascript(dir="javascript"):
    scripts_list = glob.glob(f"{dir}/*.js")
    javascript = ""
    for path in scripts_list:
        with open(path, "r", encoding="utf8") as jsfile:
            js_content = jsfile.read()
            js_content = js_content.replace("const MIDI_OUTPUT_BATCH_SIZE=4;",
                                            f"const MIDI_OUTPUT_BATCH_SIZE={OUTPUT_BATCH_SIZE};")
            javascript += f"\n<!-- {path} --><script>{js_content}</script>"
    template_response_ori = gr.routes.templates.TemplateResponse

    def template_response(*args, **kwargs):
        res = template_response_ori(*args, **kwargs)
        res.body = res.body.replace(
            b'</head>', f'{javascript}</head>'.encode("utf8"))
        res.init_headers()
        return res

    gr.routes.templates.TemplateResponse = template_response


number2drum_kits = {-1: "None", 0: "Standard", 8: "Room", 16: "Power", 24: "Electric", 25: "TR-808", 32: "Jazz",
                    40: "Blush", 48: "Orchestra"}
patch2number = {v: k for k, v in MIDI.Number2patch.items()}
drum_kits2number = {v: k for k, v in number2drum_kits.items()}
key_signatures = ['C♭', 'A♭m', 'G♭', 'E♭m', 'D♭', 'B♭m', 'A♭', 'Fm', 'E♭', 'Cm', 'B♭', 'Gm', 'F', 'Dm',
                  'C', 'Am', 'G', 'Em', 'D', 'Bm', 'A', 'F♯m', 'E', 'C♯m', 'B', 'G♯m', 'F♯', 'D♯m', 'C♯', 'A♯m']

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860, help="gradio server port")
    parser.add_argument("--batch", type=int, default=4, help="batch size")
    parser.add_argument("--share", action="store_true", default=False, help="share gradio")
    opt = parser.parse_args()
    OUTPUT_BATCH_SIZE = opt.batch
    download_if_not_exit("https://huggingface.co/skytnt/midi-model/resolve/main/soundfont.sf2", "soundfont.sf2")
    synthesizer = MidiSynthesizer("soundfont.sf2")
    thread_pool = ThreadPoolExecutor(max_workers=OUTPUT_BATCH_SIZE)
    tokenizer: Union[MIDITokenizerV1, MIDITokenizerV2, None] = None
    model: Optional[MIDIModel] = None

    load_javascript()
    app = gr.Blocks()
    with app:
        js_msg_history_state = gr.State(value=[])
        js_msg = gr.Textbox(elem_id="msg_receiver", visible=False)
        js_msg.change(None, [js_msg], [], js="""
                (msg_json) =>{
                    let msgs = JSON.parse(msg_json);
                    executeCallbacks(msgReceiveCallbacks, msgs);
                    return [];
                }
                """)
        with gr.Accordion(label="Model option", open=True):
            load_model_btn = gr.Button("Load Model")
            model_msg = gr.Textbox()
            load_model_btn.click(
                load_model, [], model_msg
            )
        tab_select = gr.State(value=0)
        with gr.Tabs():
            with gr.TabItem("custom prompt") as tab1:
                input_instruments = gr.Dropdown(label="🪗instruments (auto if empty)", choices=list(patch2number.keys()),
                                                multiselect=True, max_choices=15, type="value")
                input_drum_kit = gr.Dropdown(label="🥁drum kit", choices=list(drum_kits2number.keys()), type="value",
                                             value="None")
                input_bpm = gr.Slider(label="BPM (beats per minute, auto if 0)", minimum=0, maximum=255,
                                      step=1,
                                      value=0)
                input_time_sig = gr.Radio(label="time signature (only for tv2 models)",
                                          value="auto",
                                          choices=["auto", "4/4", "2/4", "3/4", "6/4", "7/4",
                                                   "2/2", "3/2", "4/2", "3/8", "5/8", "6/8", "7/8", "9/8", "12/8"]
                                          )
                input_key_sig = gr.Radio(label="key signature (only for tv2 models)",
                                         value="auto",
                                         choices=["auto"] + key_signatures,
                                         type="index"
                                         )
                example1 = gr.Examples([
                    [[], "None"],
                    [["Acoustic Grand"], "None"],
                    [['Acoustic Grand', 'SynthStrings 2', 'SynthStrings 1', 'Pizzicato Strings',
                      'Pad 2 (warm)', 'Tremolo Strings', 'String Ensemble 1'], "Orchestra"],
                    [['Trumpet', 'Oboe', 'Trombone', 'String Ensemble 1', 'Clarinet',
                      'French Horn', 'Pad 4 (choir)', 'Bassoon', 'Flute'], "None"],
                    [['Flute', 'French Horn', 'Clarinet', 'String Ensemble 2', 'English Horn', 'Bassoon',
                      'Oboe', 'Pizzicato Strings'], "Orchestra"],
                    [['Electric Piano 2', 'Lead 5 (charang)', 'Electric Bass(pick)', 'Lead 2 (sawtooth)',
                      'Pad 1 (new age)', 'Orchestra Hit', 'Cello', 'Electric Guitar(clean)'], "Standard"],
                    [["Electric Guitar(clean)", "Electric Guitar(muted)", "Overdriven Guitar", "Distortion Guitar",
                      "Electric Bass(finger)"], "Standard"]
                ], [input_instruments, input_drum_kit])
            with gr.TabItem("midi prompt") as tab2:
                input_midi = gr.File(label="input midi", file_types=[".midi", ".mid"], type="binary")
                input_midi_events = gr.Slider(label="use first n midi events as prompt", minimum=1, maximum=512,
                                              step=1,
                                              value=128)
                input_reduce_cc_st = gr.Checkbox(label="reduce control_change and set_tempo events", value=True)
                input_remap_track_channel = gr.Checkbox(
                    label="remap tracks and channels so each track has only one channel and in order", value=True)
                input_add_default_instr = gr.Checkbox(
                    label="add a default instrument to channels that don't have an instrument", value=True)
                input_remove_empty_channels = gr.Checkbox(label="remove channels without notes", value=False)
            with gr.TabItem("last output prompt") as tab3:
                gr.Markdown("Continue generating on the last output.")
                input_continuation_select = gr.Radio(label="select output to continue generating", value="all",
                                               choices=["all"] + [f"output{i + 1}" for i in range(OUTPUT_BATCH_SIZE)],
                                               type="index"
                                               )
                undo_btn = gr.Button("undo the last continuation")

        tab1.select(lambda: 0, None, tab_select, queue=False)
        tab2.select(lambda: 1, None, tab_select, queue=False)
        tab3.select(lambda: 2, None, tab_select, queue=False)
        input_seed = gr.Slider(label="seed", minimum=0, maximum=2 ** 31 - 1,
                               step=1, value=0)
        input_seed_rand = gr.Checkbox(label="random seed", value=True)
        input_gen_events = gr.Slider(label="generate max n midi events", minimum=1, maximum=4096,
                                     step=1, value=512)
        with gr.Accordion("options", open=False):
            input_temp = gr.Slider(label="temperature", minimum=0.1, maximum=1.2, step=0.01, value=1)
            input_top_p = gr.Slider(label="top p", minimum=0.1, maximum=1, step=0.01, value=0.94)
            input_top_k = gr.Slider(label="top k", minimum=1, maximum=128, step=1, value=20)
            input_allow_cc = gr.Checkbox(label="allow midi cc event", value=True)
            input_render_audio = gr.Checkbox(label="render audio after generation", value=True)
            example3 = gr.Examples([[1, 0.94, 128], [1, 0.98, 20], [1, 0.98, 12]],
                                   [input_temp, input_top_p, input_top_k])
        run_btn = gr.Button("generate", variant="primary")
        stop_btn = gr.Button("stop and output")
        output_midi_seq = gr.State()
        output_continuation_state = gr.State([0])
        midi_outputs = []
        audio_outputs = []
        with gr.Tabs(elem_id="output_tabs"):
            for i in range(OUTPUT_BATCH_SIZE):
                with gr.TabItem(f"output {i + 1}") as tab1:
                    output_midi_visualizer = gr.HTML(elem_id=f"midi_visualizer_container_{i}")
                    output_audio = gr.Audio(label="output audio", format="mp3", elem_id=f"midi_audio_{i}")
                    output_midi = gr.File(label="output midi", file_types=[".mid"])
                    midi_outputs.append(output_midi)
                    audio_outputs.append(output_audio)
        run_event = run_btn.click(run, [tab_select, output_midi_seq, output_continuation_state,
                                        input_continuation_select, input_instruments, input_drum_kit, input_bpm,
                                        input_time_sig, input_key_sig, input_midi, input_midi_events,
                                        input_reduce_cc_st, input_remap_track_channel,
                                        input_add_default_instr, input_remove_empty_channels,
                                        input_seed, input_seed_rand, input_gen_events, input_temp, input_top_p,
                                        input_top_k, input_allow_cc],
                                  [output_midi_seq, output_continuation_state, input_seed, js_msg],
                                  concurrency_limit=10, queue=True)
        finish_run_event = run_event.then(fn=finish_run,
                                          inputs=[output_midi_seq],
                                          outputs=midi_outputs + [js_msg],
                                          queue=False)
        finish_run_event.then(fn=render_audio,
                              inputs=[output_midi_seq, input_render_audio],
                              outputs=audio_outputs,
                              queue=False)
        stop_btn.click(None, [], [], cancels=run_event, queue=False)
        undo_btn.click(undo_continuation, [output_midi_seq, output_continuation_state],
                       [output_midi_seq, output_continuation_state, js_msg], queue=False)
    # load_javascript not work on ssr mode
    app.launch(server_port=opt.port, inbrowser=False, share=opt.share, ssr_mode=False)
    thread_pool.shutdown()
