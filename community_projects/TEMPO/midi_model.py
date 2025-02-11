from midi_tokenizer import MIDITokenizer

import numpy as np
import tqdm

from hailo_platform import (
    ConfigureParams,
    FormatType,
    HailoSchedulingAlgorithm,
    HailoStreamInterface,
    HEF,
    InferVStreams,
    InputVStreamParams,
    OutputVStreamParams,
    VDevice, 
)

timeout_ms = 1000


class MIDIModel:
    MAX_MIDI_SEQUENCE_LENGTH = 512


    def __init__(self, model_base, model_token, model_base_emb, model_token_emb):
        # Currently only support tv2o-medium model.
        self.tokenizer = MIDITokenizer()
        self.tokenizer.set_optimise_midi()

        self.net_emb = np.load(model_base_emb)
        self.net_token_emb = np.load(model_token_emb)
        
        self._init_hefs(model_base, model_token)

    def _init_hefs(self, model_base, model_token):
        params = VDevice.create_params()
        params.scheduling_algorithm = HailoSchedulingAlgorithm.ROUND_ROBIN
        params.multi_process_service=False
        self.vdevice = VDevice(params)

        model_base = HEF(model_base)
        model_token = HEF(model_token)

        configure_params = ConfigureParams.create_from_hef(model_base, interface=HailoStreamInterface.PCIe)
        configure_token_params = ConfigureParams.create_from_hef(model_token, interface=HailoStreamInterface.PCIe)

        self.net = self.vdevice.configure(model_base, configure_params)[0]
        self.net_token = self.vdevice.configure(model_token, configure_token_params)[0]

        self.input_vstreams_params = InputVStreamParams.make(self.net, format_type=FormatType.FLOAT32)
        self.input_vstreams_params["model_base/input_layer1"].user_buffer_format.type = FormatType.FLOAT32
        self.output_vstreams_params = OutputVStreamParams.make(self.net, format_type=FormatType.FLOAT32)

        self.input_vstreams_token_params = InputVStreamParams.make(self.net_token, format_type=FormatType.FLOAT32)
        self.input_vstreams_token_params["model_token/input_layer1"].user_buffer_format.type = FormatType.FLOAT32
        self.output_vstreams_token_params = OutputVStreamParams.make(self.net_token, format_type=FormatType.FLOAT32)

    def forward_token(self, infer_pipeline_token, hidden_state, x=None):
        """
        :param hidden_state: (batch_size, n_embd)
        :param x: (batch_size, token_sequence_length)
        :return: (batch_size, 1 + token_sequence_length, vocab_size)
        """
        # concat hidden state with token sequence
        hidden_state = np.expand_dims(hidden_state, (1, 2))  # (batch_size, 1, 1, n_embd)
        if x is None:
            x = np.empty((hidden_state.shape[0], 0), dtype=np.int64)
        x = x[..., :self.tokenizer.max_token_seq - 1]
        return_indexs = x.shape[-1] + 1
        if x.shape[-1] < self.tokenizer.max_token_seq:
            x = np.pad(x, ((0, 0), (0, self.tokenizer.max_token_seq - 1 - x.shape[-1])),
                       mode="constant", constant_values=self.tokenizer.pad_id)
        x = np.expand_dims(self.net_token_emb[x], 1)
        hidden_state = np.concatenate([hidden_state, x], axis=2)

        logits = infer_pipeline_token.infer(hidden_state)
        logits = list(logits.values())[0]
        return logits[:, 0, :return_indexs]

    def forward(self, infer_pipeline, x):
        """
        :param x: (batch_size, midi_sequence_length, token_sequence_length)
        :return: hidden (batch_size, midi_sequence_length, n_embd)
        """
        x = x[:, -self.MAX_MIDI_SEQUENCE_LENGTH:]
        return_indexs = x.shape[1]
        if x.shape[1] < self.MAX_MIDI_SEQUENCE_LENGTH:
            x = np.pad(x, ((0, 0), (0, self.MAX_MIDI_SEQUENCE_LENGTH - x.shape[1]), (0, 0)),
                       mode="constant", constant_values=self.tokenizer.pad_id)
        # merge token sequence
        x = self.net_emb[x]
        x = np.expand_dims(np.sum(x, axis=-2), 1)

        x = x.reshape(-1, x.shape[1] * x.shape[2] // 8, 8, x.shape[-1])
        hidden_state = infer_pipeline.infer(x)
        hidden_state = list(hidden_state.values())[0]
        return hidden_state[:, 0, :return_indexs]

    def softmax(self, x, axis):
        x_max = np.amax(x, axis=axis, keepdims=True)
        exp_x_shifted = np.exp(x - x_max)
        return exp_x_shifted / np.sum(exp_x_shifted, axis=axis, keepdims=True)

    def sample_top_p_k(self, probs, p, k, generator=None):
        if generator is None:
            generator = np.random
        probs_idx = np.argsort(-probs, axis=-1)
        probs_sort = np.take_along_axis(probs, probs_idx, -1)
        probs_sum = np.cumsum(probs_sort, axis=-1)
        mask = probs_sum - probs_sort > p
        probs_sort[mask] = 0.0
        mask = np.zeros(probs_sort.shape[-1])
        mask[:k] = 1
        probs_sort = probs_sort * mask
        probs_sort /= np.sum(probs_sort, axis=-1, keepdims=True)
        shape = probs_sort.shape
        probs_sort_flat = probs_sort.reshape(-1, shape[-1])
        probs_idx_flat = probs_idx.reshape(-1, shape[-1])
        next_token = np.stack([generator.choice(idxs, p=pvals) for pvals, idxs in zip(probs_sort_flat, probs_idx_flat)])
        next_token = next_token.reshape(*shape[:-1])
        return next_token

    def generate(self, prompt=None, batch_size=1, max_len=512, temp=1.0, top_p=0.98, top_k=20,
                 disable_patch_change=False, disable_control_change=False, disable_channels=None, generator=None):
        with InferVStreams(self.net, self.input_vstreams_params, self.output_vstreams_params) as infer_pipeline:
            with InferVStreams(self.net_token, self.input_vstreams_token_params, self.output_vstreams_token_params) as infer_pipeline_token:
                tokenizer = self.tokenizer
                if disable_channels is not None:
                    disable_channels = [tokenizer.parameter_ids["channel"][c] for c in disable_channels]
                else:
                    disable_channels = []
                max_token_seq = tokenizer.max_token_seq
                if prompt is None:
                    input_tensor = np.full((1, 1, max_token_seq), tokenizer.pad_id, dtype=np.int64)
                    input_tensor[0, 0, 0] = tokenizer.bos_id  # bos
                    input_tensor = np.repeat(input_tensor, repeats=batch_size, axis=0)
                else:
                    if len(prompt.shape) == 2:
                        prompt = prompt[None, :]
                        prompt = np.repeat(prompt, repeats=batch_size, axis=0)
                    elif prompt.shape[0] == 1:
                        prompt = np.repeat(prompt, repeats=batch_size, axis=0)
                    elif len(prompt.shape) != 3 or prompt.shape[0] != batch_size:
                        raise ValueError(f"invalid shape for prompt, {prompt.shape}")
                    prompt = prompt[..., :max_token_seq]
                    if prompt.shape[-1] < max_token_seq:
                        prompt = np.pad(prompt, ((0, 0), (0, 0), (0, max_token_seq - prompt.shape[-1])),
                                        mode="constant", constant_values=tokenizer.pad_id)
                    input_tensor = prompt

                cur_len = input_tensor.shape[1]
                bar = tqdm.tqdm(desc="generating", total=max_len - cur_len)
                with bar:
                    while cur_len < max_len:
                        end = [False] * batch_size
                        hidden = self.forward(infer_pipeline, input_tensor)[:, -1]
                        next_token_seq = None
                        event_names = [""] * batch_size
                        for i in range(max_token_seq):
                            mask = np.zeros((batch_size, tokenizer.vocab_size), dtype=np.int64)
                            for b in range(batch_size):
                                if end[b]:
                                    mask[b, tokenizer.pad_id] = 1
                                    continue
                                if i == 0:
                                    mask_ids = list(tokenizer.event_ids.values()) + [tokenizer.eos_id]
                                    if disable_patch_change:
                                        mask_ids.remove(tokenizer.event_ids["patch_change"])
                                    if disable_control_change:
                                        mask_ids.remove(tokenizer.event_ids["control_change"])
                                    mask[b, mask_ids] = 1
                                else:
                                    param_names = tokenizer.events[event_names[b]]
                                    if i > len(param_names):
                                        mask[b, tokenizer.pad_id] = 1
                                        continue
                                    param_name = param_names[i - 1]
                                    mask_ids = tokenizer.parameter_ids[param_name]
                                    if param_name == "channel":
                                        mask_ids = [i for i in mask_ids if i not in disable_channels]
                                    mask[b, mask_ids] = 1
                            mask = np.expand_dims(mask, 1)
                            x = next_token_seq
                            logits = self.forward_token(infer_pipeline_token, hidden, x)[:, -1:]
                            scores = self.softmax(logits / temp, axis=-1) * mask
                            samples = self.sample_top_p_k(scores, top_p, top_k, generator=generator)
                            if i == 0:
                                next_token_seq = samples
                                for b in range(batch_size):
                                    if end[b]:
                                        continue
                                    eid = samples[b].item()
                                    if eid == tokenizer.eos_id:
                                        end[b] = True
                                    else:
                                        event_names[b] = tokenizer.id_events[eid]
                            else:
                                next_token_seq = np.concatenate([next_token_seq, samples], axis=1)
                                if all([len(tokenizer.events[event_names[b]]) == i for b in range(batch_size) if not end[b]]):
                                    break
 
                        if next_token_seq.shape[1] < max_token_seq:
                            next_token_seq = np.pad(next_token_seq,
                                                    ((0, 0), (0, max_token_seq - next_token_seq.shape[-1])),
                                                    mode="constant", constant_values=tokenizer.pad_id)
                        next_token_seq = next_token_seq[:, None, :]
                        input_tensor = np.concatenate([input_tensor, next_token_seq], axis=1)
                        cur_len += 1
                        bar.update(1)
                        yield next_token_seq[:, 0]
                        if all(end):
                            break
