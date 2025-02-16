import os
from transformers import AutoProcessor, AutoConfig
import onnxruntime as ort
import time
import numpy as np
from tokenizers import Tokenizer as TokenizerFast
from hailo_platform import VDevice, FormatType, HailoSchedulingAlgorithm
import clip
import torch
from picamera2 import Picamera2
import argparse


CAPTION_EMBEDDING = "resources/embeddings/caption_embedding.npy"
WORD_EMBEDDING = "resources/embeddings/word_embedding.npy"
ENCODER_PATH = "resources/models/florence2_transformer_encoder.hef"
DECODER_PATH = "resources/models/florence2_transformer_decoder.hef"
VISION_ENCODER_PATH = "resources/models/vision_encoder.onnx"
DECODER_INPUT_SHAPE = (1, 1, 32, 768)
ENCODER_OUTPUT_KEY = "resources/transformer_decoder/input_layer1"
DECODER_INPUT_KEY = "resources/transformer_decoder/input_layer2"
TOKENIZER_PATH = "resources/tokenizer/tokenizer.json"
START_TOKEN = 2
TIMEOUT_MS = 1000
COSINE_SIMILARITY_THRESHOLD = 0.7

def argparser():
    parser = argparse.ArgumentParser(description="Configurations for Flourence.")
    parser.add_argument('--no-speaker', action="store_true", help='Use this flag in case you did not connected a speaker')

    return parser.parse_args()

def match_texts(model, text1, text2):
    # Load the CLIP model and preprocess function
    device = "cpu"
    #model, preprocess = clip.load("ViT-B/32", device)

    # Tokenize the texts and encode them into embeddings
    texts = [text1, text2]
    text_inputs = clip.tokenize(texts)

    # Get the text features (embeddings) from CLIP
    text_features = model.encode_text(text_inputs)

    # Normalize the features to unit vectors (important for similarity comparisons)
    text_features /= text_features.norm(dim=-1, keepdim=True)

    # Compute cosine similarity between the two text embeddings
    similarity = torch.cosine_similarity(text_features[0], text_features[1], dim=0)
    #print (f"similarity between '{text1}' and '{text2}' is: {similarity.item()}")
    return similarity.item()



def create_processor():
    size={'height':384, 'width':384}
    return AutoProcessor.from_pretrained('microsoft/florence-2-base', trust_remote_code=True, size=size, crop_size=size)

def infer_davit(inputs, processor, davit_session):
    start = time.time()    
    image_features = davit_session.run(None, {'pixel_values':inputs.pixel_values.numpy()})[0]
    duration = time.time() - start
    #print(f"Davit model on onnx took {duration} seconds")
    return image_features

def infer_encoder(encoder, image_text_embeddings):
    start = time.time()
    encoder_hidden_state = np.empty((1,153,768), dtype=np.float32)
    bindings = encoder.create_bindings()
    bindings.input().set_buffer(image_text_embeddings)
    bindings.output().set_buffer(encoder_hidden_state)
    job = encoder.run_async([bindings], lambda completion_info: None)
    job.wait(TIMEOUT_MS)
    end = time.time()
    #print("Encoder model on h8 took %s seconds" % (end - start))
    return encoder_hidden_state

def infer_decoder(decoder, encoder_output, input_embeds):
    start = time.time()
    decoder_output = np.empty((32,51289), dtype=np.float32)
    bindings = decoder.create_bindings()
    bindings.input('florence2_transformer_decoder/input_layer1').set_buffer(encoder_output)
    bindings.input('florence2_transformer_decoder/input_layer2').set_buffer(input_embeds)
    bindings.output().set_buffer(decoder_output)
    job = decoder.run_async([bindings], lambda completion_info: None)
    job.wait(TIMEOUT_MS)
    end = time.time()
    #print("Decoder model on h8 took %s seconds" % (end - start))
    return decoder_output

def infer_florence2(image, processor, davit_session, encoder, decoder, tokenizer):
    inputs = processor(text='<CAPTION>', images=image, return_tensors='pt')
    image_features = infer_davit(inputs, processor, davit_session)
    image_text_embeddings = np.concatenate([np.expand_dims(image_features, axis=0), np.load(CAPTION_EMBEDDING)], axis=2)
    encoder_hidden_state = infer_encoder(encoder, image_text_embeddings)
    
    word_embedding = np.load(WORD_EMBEDDING)
    decoder_input = np.insert(np.zeros(DECODER_INPUT_SHAPE).astype(np.float32), 0, word_embedding[START_TOKEN], axis=2)[:, :, :-1, :]
    dataset = {
        ENCODER_OUTPUT_KEY : encoder_hidden_state,
        DECODER_INPUT_KEY : decoder_input
    }
    next_token_id = -1
    token_index = 0
    generated_ids = [START_TOKEN]
    start = time.time()
    while next_token_id != START_TOKEN and token_index < 32:
        decoder_output = infer_decoder(decoder, dataset[ENCODER_OUTPUT_KEY], dataset[DECODER_INPUT_KEY])
        res = decoder_output.squeeze()[token_index]
        next_token_id = np.argmax(res)
        token_index += 1
        generated_ids.append(next_token_id)
        decoder_input = np.insert(decoder_input, token_index, word_embedding[next_token_id], axis=2)[:, :, :-1, :]
        dataset[DECODER_INPUT_KEY] = decoder_input
    res = tokenizer.decode(np.array(generated_ids), skip_special_tokens=True)
    end = time.time()
    #print("third model h8 took %s seconds" % (end - start))
    return res

def picam_init():
    picam2 = Picamera2()
    preview_config = picam2.create_preview_configuration(main={"size": (2464, 3280, 3)})
    capture_config = picam2.create_still_configuration(main={"size": (2464, 3280, 3), "format": "RGB888"})
    picam2.configure(preview_config)
    picam2.start(show_preview=True)
    return picam2, preview_config, capture_config

def picam_capture(picam2, capture_config, preview_config):
    picam2.switch_mode(capture_config)
    array = picam2.capture_array("main")
    picam2.switch_mode(preview_config)
    return array

def caption_loop(picam2, capture_config, preview_config, processor, davit_session, encoder, decoder, tokenizer, clip_model, no_speaker):
    last_caption = None
    while True:
        start = time.time()
        caption = infer_florence2(picam_capture(picam2, capture_config, preview_config), processor, davit_session, encoder, decoder, tokenizer)
        if last_caption is None or match_texts(clip_model, last_caption, caption) < COSINE_SIMILARITY_THRESHOLD:
            print(f"NEW EVENT ALERT!!!!! - {caption}")
            if not no_speaker:
                os.system(f'espeak "{caption}" -s 130')
        end = time.time()
        #print("took %s seconds" % (end - start))
        last_caption = caption

def main():
    print("Initializing...")
    args = argparser()
    processor = create_processor()
    davit_session = ort.InferenceSession(VISION_ENCODER_PATH)
    tokenizer = TokenizerFast.from_file(TOKENIZER_PATH)
    clip_model, _ = clip.load("ViT-B/32", "cpu")
    params = VDevice.create_params()
    params.scheduling_algorithm = HailoSchedulingAlgorithm.ROUND_ROBIN    
    with VDevice(params) as vd:
        encoder_infer_model = vd.create_infer_model(ENCODER_PATH)
        encoder_infer_model.input().set_format_type(FormatType.FLOAT32)
        encoder_infer_model.output().set_format_type(FormatType.FLOAT32)
        with encoder_infer_model.configure() as encoder:
            decoder_infer_model = vd.create_infer_model(DECODER_PATH)
            decoder_infer_model.input('florence2_transformer_decoder/input_layer1').set_format_type(FormatType.FLOAT32)
            decoder_infer_model.input('florence2_transformer_decoder/input_layer2').set_format_type(FormatType.FLOAT32)
            decoder_infer_model.output().set_format_type(FormatType.FLOAT32)
            with decoder_infer_model.configure() as decoder:
                picam2, preview_config, capture_config = picam_init()
                print("Initialized succesfully")
                caption_loop(picam2, capture_config, preview_config, processor, davit_session, encoder, decoder, tokenizer, clip_model, args.no_speaker)
                    

if __name__=="__main__":
    main()
