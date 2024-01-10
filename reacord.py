
import pyaudio
import numpy as np
from pynput import keyboard
import wave
import threading
import queue
import asyncio

import sys
import signal
import argparse

#import myenv
import whisperso
import notionif

# オーディオストリーム設定
FORMAT = pyaudio.paInt16  # オーディオフォーマット（例：16ビットPCM）
CHANNELS = 1              # チャンネル数（モノラル）
SAMPLE_RATE = 16000       # 音声では16Khzで十分
#CHUNK_SIZE = 1024        # チャンクサイズ（一度に読み取るフレーム数）
CHUNK_SIZE = 2048
INPUT_DEVICE_INDEX = 0

# 無音判定の閾値と持続時間
SILENCE_THRESHOLD = 500   # 無音と判定する音量の閾値。無音だと50前後に見える
SILENCE_DURATION = 0.5    # 無音と判定する持続時間（秒）一人で話すと0.2~、複数人だと0.5~あたり。

gIsRecording = True

# キーボードをチェックして状態を変更
#def on_press(key):
#    global gIsRecording
#    try:
#        if ( key.char == 'q' ):
#            gIsRecording = False
#            print("q is pressed")
#    except AttributeError:
#        print('special key {0} pressed'.format(key))
#        gIsRecording = False

def signal_handler(signum, frame):
    global gIsRecording

    if gIsRecording:
        gIsRecording = False
        print("signal handled. process will terminate soon.")
    else:
        print("force eixi..")
        sys.exit(1)

def list_device():
    audio = pyaudio.PyAudio()

    # 使用可能なオーディオデバイスのリストを取得
    info = audio.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')

    # 各デバイスの情報を表示
    for i in range(0, num_devices):
        if (audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print("Input Device id ", i, " - ", audio.get_device_info_by_host_api_device_index(0, i).get('name'))

    print("specify ID in the following format --input ID")

# 音声取得
def record(task_queue, args):

    input_index=args.input

    print(f"******************{input_index}*********************")

    # PyAudioインスタンスの初期化
    audio = pyaudio.PyAudio()

    # オーディオストリームの開始
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=SAMPLE_RATE, input=True,
                        input_device_index=input_index,
                        frames_per_buffer=CHUNK_SIZE)

    # オーディオデータを格納するバッファ
    audio_buffer = []
    silence_start = None

    seqnum = 0
    status = 'A_waiting_start'
    voice_off_count = 0

    Threshold = SILENCE_DURATION * SAMPLE_RATE / CHUNK_SIZE

    try:
        # オーディオのキャプチャループ
        while gIsRecording:

            # オーディオデータの読み取り
            data = stream.read(CHUNK_SIZE)

            # 音量レベルの計算
            amplitude = np.frombuffer(data, dtype=np.int16)
            volume = np.abs(amplitude).mean()
            voice_on = volume > SILENCE_THRESHOLD
            #print(f"{volume}");

            if voice_on:
                print(f"o {volume}\r", end='', flush=True)
            else:
                print(f". {volume}\r", end='', flush=True)

            if ( status == 'A_waiting_start' ):
                if ( voice_on ):
                    audio_buffer.append(data)
                    status = 'B_in_voice'
                else:
                    pass # status = 'A_waiting_start'

            elif ( status == 'B_in_voice' ):
                if ( voice_on ):
                    audio_buffer.append(data)
                    voice_off_count = 0
                    # status = 'B_in_voice'
                else:
                    audio_buffer.append(data)
                    voice_off_count = 1
                    status = 'C_counting'

            elif ( status == 'C_counting' ):
                if ( voice_on ):
                    audio_buffer.append(data)
                    voice_off_count = 0
                    status = 'B_in_voice'
                else:
                    voice_off_count += 1
                    if ( voice_off_count >= Threshold ):
                        # HACK 多分 actual_bufでよいはず。
                        # actual_buf = audio_buffer[0:-voice_off_count]
                        print(f"\nrecord: #{seqnum} {len(audio_buffer) * CHUNK_SIZE // SAMPLE_RATE} sec")
                        #task_queue.put({'chunk':actual_buf, 'seq':seqnum})
                        task_queue.put({'chunk':audio_buffer, 'seq':seqnum})
                        seqnum += 1
                        audio_buffer = []
                        status = 'A_waiting_start'
                    else:
                        pass # status = 'C_counting'
            else:
                raise 'unknown status' # HACK

    except Exception as e:
        print(e)
        
    task_queue.put(None)

    # オーディオストリームの終了処理
    stream.stop_stream()
    stream.close()
    audio.terminate()

    print("record() end")


# 文字起こし
def transcript(task_queue, upload_queue, args):

    lang=args.lang

    whisperso.initialize(lang)

    while True:
        task = task_queue.get()
        if ( task == None ):
            break
        else:
            chunk = task['chunk']
            seqnum = task['seq']
            #print(f"\ntranscript: #{task['seq']} start")
            #print(f"({len(chunk)} chunks {len(chunk)*CHUNK_SIZE//SAMPLE_RATE} sec)")
            data_int = np.frombuffer(b''.join(chunk), dtype=np.int16)
            #data_float32 = data_int.astype(np.float32) / 32768.0
            ret = whisperso.ondata(data_int, task['seq'])
            if ( 0 < len(ret) ):
                print(f"\ntranscript: #{task['seq']} {'~'.join(ret)}" )
                if ( upload_queue ):
                    upload_queue.put({'seq': seqnum, 'text': ret} )
            else:
                print(f"\ntranscript: #{task['seq']} was empty")


    if ( upload_queue ):
        upload_queue.put(None)
    whisperso.free()
    print("transcript() end")

# notionへのアップロード
async def upload(upload_queue, args):
   
    print("upload() initilizing") 
    notionif.init(target_id=args.page)

    while True:
        task = upload_queue.get()
        if ( task == None ):
            break
        else:
            seqnum = task['seq']
            text = task['text'] # array
            await notionif.upload(f"{'〜'.join(text)}（自動）")
            print(f"upload: #{seqnum} {'〜'.join(text)}")

    print('upload() end')


def test_upload(args):
    notionif.init(target_id=args.page)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    test_string = "test test test"
    print(f"sending {test_string} to page id={args.page}")
    loop.run_until_complete(notionif.upload(test_string))
    loop.close()
    


# uploadがasyncなのでthreadに渡すためラッパーをかける
def upload_thread(upload_queue, args):
    print("upload_thread initilizing") 
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(upload(upload_queue, args))
    loop.close()
    

def main(args):
    # keyboard OBSOLETE
    #if ( args.keyboard ):
    #    listener = keyboard.Listener(on_press=on_press)
    #    listener.start()

    signal.signal(signal.SIGINT, signal_handler)

    # queue
    task_queue = queue.Queue()
    upload_queue = queue.Queue() if ( args.page ) else None

    # producer & consumer
    recorder     = threading.Thread(target=record, args=(task_queue, args))
    transcripter = threading.Thread(target=transcript, args=(task_queue, upload_queue, args))
    if ( args.page ):
        uploader     = threading.Thread(target=upload_thread, args=(upload_queue, args))
  
    # 後段から開始
    if ( args.page ):
        uploader.start() 
    transcripter.start()
    recorder.start()

    # 前段から待ち
    recorder.join()
    transcripter.join()
    if ( args.page ):
        uploader.join() 

parser = argparse.ArgumentParser(
    description = 'Realtime speach transcript & Uploder'
)
parser.add_argument("--input", type=int, default=INPUT_DEVICE_INDEX, help="device index")
parser.add_argument("--lang", default='ja', help="transcription base language")
parser.add_argument("--page", help="notion page id if not, no upload")

parser.add_argument("--vol_th", default=SILENCE_THRESHOLD, help="volume threshold")

#parser.add_argument("--keyboard", default=False, help="keyboard control")

parser.add_argument("--list", action="store_true", default=False, help="(one shot)show device list")
parser.add_argument("--upload", action="store_true", default=False, help="(one shot)test upload")

args = parser.parse_args()

if ( args.list ):
    list_device()
elif ( args.upload ):
    test_upload(args)
else:
    main(args)



