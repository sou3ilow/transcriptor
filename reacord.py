
import pyaudio
import numpy as np
from pynput import keyboard
import wave
import threading
import queue
import asyncio

#import myenv
import whisperso
import notionif

# オーディオストリーム設定
FORMAT = pyaudio.paInt16  # オーディオフォーマット（例：16ビットPCM）
#FORMAT = pyaudio.paFloat32
#SAMPLE_WIDTH = 2         # HACK これはpaInt16を使う場合の値。 ref. pyaudio.get_sample_size(format)
CHANNELS = 1              # チャンネル数（モノラル）
#SAMPLE_RATE = 44100      # サンプリングレート（例：44.1kHz）
SAMPLE_RATE = 16000
#CHUNK_SIZE = 1024        # チャンクサイズ（一度に読み取るフレーム数）
CHUNK_SIZE = 2048
#gInputDeviceIndex = 0
gInputDeviceIndex = 3

# 無音判定の閾値と持続時間
#SILENCE_THRESHOLD = 0.02 # 無音と判定する音量の閾値
#SILENCE_THRESHOLD = 500   #for int16?
SILENCE_THRESHOLD = 500   #for int16?
SILENCE_DURATION = 0.5    # 無音と判定する持続時間（秒）

gIsRecording = True

# キーボードをチェックして状態を変更
def on_press(key):
    global gIsRecording
    try:
        if ( key.char == 'q' ):
            gIsRecording = False
            print("q is pressed")
    except AttributeError:
        print('special key {0} pressed'.format(key))
        gIsRecording = False

# 音声取得
def record(task_queue):
    # PyAudioインスタンスの初期化
    audio = pyaudio.PyAudio()

    # オーディオストリームの開始
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=SAMPLE_RATE, input=True,
                        input_device_index=gInputDeviceIndex,
                        frames_per_buffer=CHUNK_SIZE)

    # オーディオデータを格納するバッファ
    audio_buffer = []
    silence_start = None

    seqnum = 0
    status = 'A_waiting_start'
    voice_off_count = 0

    Threshold = SILENCE_DURATION * SAMPLE_RATE / CHUNK_SIZE

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
            print(f"o {volume}\n", end='', flush=True)
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

    # end loop

    task_queue.put(None)

    # オーディオストリームの終了処理
    stream.stop_stream()
    stream.close()
    audio.terminate()

    print("record() end")


# 文字起こし
def transcript(task_queue, upload_queue):

    whisperso.initialize()

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
                upload_queue.put({'seq': seqnum, 'text': ret} )
            else:
                print(f"\ntranscript: #{task['seq']} was empty")


    upload_queue.put(None)
    whisperso.free()
    print("transcript() end")

# notionへのアップロード
async def upload(upload_queue):
   
    print("upload() initilizing") 
    notionif.init()

    while True:
        task = upload_queue.get()
        if ( task == None ):
            break
        else:
            seqnum = task['seq']
            text = task['text'] # array
            await notionif.upload(f"{'〜'.join(text)}（自動")
            print(f"upload: #{seqnum} {text}")

    print('upload() end')

# uploadがasyncなのでthreadに渡すためラッパーをかける
def upload_thread(upload_queue):
    print("upload_thread initilizing") 
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(upload(upload_queue))
    loop.close()
    

def main():
    # keyboard
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    # queue
    task_queue = queue.Queue()
    upload_queue = queue.Queue()

    # producer & consumer
    recorder     = threading.Thread(target=record, args=(task_queue, ))
    transcripter = threading.Thread(target=transcript, args=(task_queue, upload_queue))
    uploader     = threading.Thread(target=upload_thread, args=(upload_queue, ))
  
    # 後段から開始
    uploader.start() 
    transcripter.start()
    recorder.start()

    # 前段から待ち
    recorder.join()
    transcripter.join()
    uploader.join() 

main()



