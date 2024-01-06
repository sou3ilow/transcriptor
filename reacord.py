
import pyaudio
import numpy as np
from pynput import keyboard
import wave

# オーディオストリーム設定
FORMAT = pyaudio.paInt16  # オーディオフォーマット（例：16ビットPCM）
SAMPLE_WIDTH = 2 # HACK これはpaInt16を使う場合の値。 ref. pyaudio.get_sample_size(format)
CHANNELS = 1              # チャンネル数（モノラル）
#RATE = 44100              # サンプリングレート（例：44.1kHz）
RATE = 16000
#CHUNK = 1024              # チャンクサイズ（一度に読み取るフレーム数）
CHUNK = 2048
input_device_index = 0

# 無音判定の閾値と持続時間
#SILENCE_THRESHOLD = 0.02  # 無音と判定する音量の閾値
SILENCE_THRESHOLD = 500
SILENCE_DURATION = 1.5      # 無音と判定する持続時間（秒）



isRecording = True

# キーボードをチェックして状態を変更
def on_press(key):
    global isRecording
    try:
        if ( key.char == 'q' ):
            isRecording = False
            print("q is pressed")
            
    except AttributeError:
        print('special key {0} pressed'.format(key))
    
    

def recorder():
    global isRecording

    # PyAudioインスタンスの初期化
    audio = pyaudio.PyAudio()

    # オーディオストリームの開始
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        input_device_index=input_device_index,
                        frames_per_buffer=CHUNK)

    # オーディオデータを格納するバッファ
    audio_buffer = []
    silence_start = None

    # オーディオのキャプチャループ
    while isRecording:

        # オーディオデータの読み取り
        data = stream.read(CHUNK)
        audio_buffer.append(data)

        # 音量レベルの計算
        amplitude = np.frombuffer(data, dtype=np.int16)
        volume = np.abs(amplitude).mean()


        # 無音区間の検出
        if volume < SILENCE_THRESHOLD:
            print(".", end='', flush=True)

            time_in_buff = len(audio_buffer) * CHUNK / RATE

            if silence_start is None:
                silence_start = time_in_buff
            elif time_in_buff - silence_start > SILENCE_DURATION:
                print("", flush=True) # 改行
                # 無音区間で区切る処理
                process_audio_chunk(audio_buffer)
                audio_buffer = []
                silence_start = None
            #else:
            #    print(time_in_buff - silence_start)
                
        else:
            #print(f"{volume}");
            print("o", end='', flush=True)
            silence_start = None

    # end loop
    # オーディオストリームの終了処理
    stream.stop_stream()
    stream.close()
    audio.terminate()


seqnum = 0

def process_audio_chunk(chunk):
    global seqnum

    # ここでオーディオチャンクを処理（例：文字起こし）

    filename = f"./data/{seqnum}.wav"
    seqnum += 1

    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(SAMPLE_WIDTH)
    wf.setframerate(RATE)
    wf.writeframes(b''.join(chunk))
    wf.close()

    print(f"{filename} ({len(chunk)} chunks {len(chunk)*CHUNK//RATE} sec)")

def main():
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    recorder()
    
main()



