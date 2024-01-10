import ctypes
#import pathlib

# this is needed to read the WAV file properly from scipy.io import wavfile
from scipy.io import wavfile

import myenv
# myenv.LIB_PATH
# myenv.MODEL_PATH
# myenv.TEST_TARGET

# this needs to match the C struct in whisper.h
class WhisperFullParams(ctypes.Structure):
    _fields_ = [
        ("strategy", ctypes.c_int),
        #
        ("n_threads", ctypes.c_int),
        ("n_max_text_ctx", ctypes.c_int),
        ("offset_ms", ctypes.c_int),
        ("duration_ms", ctypes.c_int),
        #
        ("translate", ctypes.c_bool),
        ("no_context", ctypes.c_bool),
        ("no_timestamps", ctypes.c_bool),
        ("single_segment", ctypes.c_bool),
        ("print_special", ctypes.c_bool),
        ("print_progress", ctypes.c_bool),
        ("print_realtime", ctypes.c_bool),
        ("print_timestamps", ctypes.c_bool),
        #
        ("token_timestamps", ctypes.c_bool),
        ("thold_pt", ctypes.c_float),
        ("thold_ptsum", ctypes.c_float),
        ("max_len", ctypes.c_int),
        ("split_on_word", ctypes.c_bool),
        ("max_tokens", ctypes.c_int),
        #
        ("speed_up", ctypes.c_bool),
        ("debug_mode", ctypes.c_bool),
        ("audio_ctx", ctypes.c_int),
        #
        ("tbrz_enables", ctypes.c_bool),
        #
        ("initial_prompt", ctypes.c_char_p),
        ("prompt_tokens", ctypes.c_void_p),
        ("prompt_n_tokens", ctypes.c_int),
        #
        ("language", ctypes.c_char_p),
        ("detect_language", ctypes.c_bool),
        #
        ("suppress_blank", ctypes.c_bool),
        ("suppress_non_speech_tokens", ctypes.c_bool),
        #
        ("temperature", ctypes.c_float),
        ("max_initial_ts", ctypes.c_float),
        ("length_penalty", ctypes.c_float),
        #
        ("temperature_inc", ctypes.c_float),
        ("entropy_thold", ctypes.c_float),
        ("logprob_thold", ctypes.c_float),
        ("no_speech_thold", ctypes.c_float),
        #
        # struct { int }
        ("greedy", ctypes.c_int * 1),
        #
        # struct { int, float }
        ("beam_search", ctypes.c_int * 3),
        #
        ("new_segment_callback", ctypes.c_void_p),
        ("new_segment_callback_user_data", ctypes.c_void_p),
        #
        ("progress_callback", ctypes.c_void_p),
        ("progress_callback_user_data", ctypes.c_void_p),
        #
        ("encoder_begin_callback", ctypes.c_void_p),
        ("encoder_begin_callback_user_data", ctypes.c_void_p),
        #
        ("abort_callback", ctypes.c_void_p),
        ("abort_callback_user_data", ctypes.c_void_p),
        #
        ("logits_filter_callback", ctypes.c_void_p),
        ("logits_filter_callback_user_data", ctypes.c_void_p),
        #
        ("grammar_rules", ctypes.c_void_p),
        ("n_grammer_rules", ctypes.c_size_t),
        ("i_start_rule", ctypes.c_size_t),
        ("grammar_penalty", ctypes.c_float),
    ]


whisper = None
ctx = None
params = None

def initialize(lang='ja'):
    global whisper
    global ctx
    global params

    libname = myenv.LIB_PATH 
    whisper = ctypes.CDLL(libname)

    # tell Python what are the return types of the functions
    whisper.whisper_init_from_file.restype = ctypes.c_void_p
    whisper.whisper_full_default_params.restype = WhisperFullParams
    whisper.whisper_full_get_segment_text.restype = ctypes.c_char_p

    # initialize whisper.cpp context
    #ctx = whisper.whisper_init_from_file(fname_model.encode("utf-8"))
    ctx = whisper.whisper_init_from_file(myenv.MODEL_PATH.encode("utf-8"))

    # get default whisper parameters and adjust as needed
    params = whisper.whisper_full_default_params()
    params.print_special = False
    params.print_progress = False
    params.print_realtime = False
    params.print_timestamps = False

    #params.print_realtime = True
    #params.print_progress = False
    params.language = lang.encode() # b'ja'

    print(f"*********************{lang}********************")

    #params.no_speech_thold = 100 / 32768.0 # hack
    params.no_speech_thold = 0.001
    #params.temperature = 0.8

def ondata(data, seqnum=None):
    global whisper
    global ctx
    global params

    # convert to 32-bit float
    data = data.astype("float32") / 32768.0 #

    # run the inference
    result = whisper.whisper_full(
        ctypes.c_void_p(ctx),
        params,
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        len(data),
    )

    if result != 0:
        print("Error: {}".format(result))
        exit(1)

    # print results from Python
    n_segments = whisper.whisper_full_n_segments(ctypes.c_void_p(ctx))

    ret = []

    for i in range(n_segments):
        #t0 = whisper.whisper_full_get_segment_t0(ctypes.c_void_p(ctx), i)
        #t1 = whisper.whisper_full_get_segment_t1(ctypes.c_void_p(ctx), i)
        txt = whisper.whisper_full_get_segment_text(ctypes.c_void_p(ctx), i)
        decoded_text = txt.decode('utf-8')

        ret.append(decoded_text)
        #print(f"{seqnum}: {t0/1000.0:.3f} - {t1/1000.0:.3f} : {decoded_text}")

    return ret

def free():
    global whisper
    global ctx

    # free the memory
    whisper.whisper_free(ctypes.c_void_p(ctx))


    

if __name__ == "__main__":


    # load WAV file
    #samplerate, data = wavfile.read(fname_wav)
    samplerate, data = wavfile.read(myenv.TEST_TARGET)

    # convert to 32-bit float
    data = data.astype("float32") / 32768.0

    # run the inference
    result = whisper.whisper_full(
        ctypes.c_void_p(ctx),
        params,
        data.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        len(data),
    )

    if result != 0:
        print("Error: {}".format(result))
        exit(1)

    # print results from Python
    n_segments = whisper.whisper_full_n_segments(ctypes.c_void_p(ctx))
    for i in range(n_segments):
        t0 = whisper.whisper_full_get_segment_t0(ctypes.c_void_p(ctx), i)
        t1 = whisper.whisper_full_get_segment_t1(ctypes.c_void_p(ctx), i)
        txt = whisper.whisper_full_get_segment_text(ctypes.c_void_p(ctx), i)

        print(f"{t0/1000.0:.3f} - {t1/1000.0:.3f} : {txt.decode('utf-8')}")




