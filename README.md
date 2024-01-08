

## 概要

文字起こし用ツールです。

PCで再生中の音声をリアルタイムに拾って文字に起こし、notionにアップロードすることを目的としています。

## インストール

1. libwhisper.so
2. loopback
3. notion
4. myenv.py

### libwhisper.so

文字起こしのためにlibwhisper.soを使います。
libwhisper.soはwhisper.cppの一部で、レポジトリをクローンした後下記のコマンドで生成できます。
```
	make libwhisper.so
```

モデルをダウンロードしておく必要があります。モデルはxxxとggmlの2つがあるようですが、
ggmlのほうを推奨しているように見受けられたのでこちらを使うようにしました。
m2 macbook airではlargeモデルで十分動くようですのでlargeモデルを取得しておきます。
```
	cd models
	bash download-ggml-models.sh large-v3-q5_0.bin"
```

libwhisper.soとmodelのパスはmyenv.pyに書いておく必要があります。

### Loopback

音声出力を入力に回すことができるツールのようです。
体験版は20分後に音質が劣化するそうですがあまり影響がないかもしれません(n=1)

https://rogueamoeba.com/loopback/ 

`looback audio`のようなものを作って、sourceにchromeを追加し、chromeからoutputにつなげると準備が整います。
```
	% python3 list-device.py 
	Input Device id  0  -  MacBook Airのマイク
	Input Device id  2  -  Microsoft Teams Audio
	Input Device id  3  -  Loopback Audio
```
recorder.pyのgInputDeviceIndexに対象のid(ここでは3)を指定します。0だとマイクの音をそのまま拾います。

### Notion

結果をnotionに書き込むために準備しておきます。

https://www.notion.so/my-integrations
から新しいintegrationを作成しsecret_xxxを控えておきます。myenv.NOTION_TOKENにしていします。

commentの読み書き、ユーザー情報へのアクセスは不要です。
Update contentのみで良さそうですが、Read content, Insert content権限も必要かもしれません。

文字起こし結果のアップロード先pageIDを控えておきます。
適当なページを作成した後、URLを確認し、下記のXXXXXXXXXXの部分を使います。

https://www.notion.so/Integration-XXXXXXXXXXXXXXXXXXXXXX

### myenv.py

一連の情報をmyenv.pyに保存しておきます。

```
LIB_PATH = "(path to whisper.cpp)/libwhisper.so"
MODEL_PATH = "(path to whisper.cpp)/models/ggml-large-v3-q5_0.bin"
TEST_TARGET = "./data/1.wav"
NOTION_TOKEN = "secret_XXXXXXXXXXXX"
PAGE_ID = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
```

## 調整

### record.py

* SILENCE_THRESHOOLD

無音と有音の境になるボリュームレベルを指定します。`python record.py`を実行し、音声を取得できるようになるとコマンドライン上に下の例のような記載が並びます。o始まりは有音と判定、続く数字がvolumeです。無音区間は行をリフレッシュして表示するのでコンソールに残りません。
```
  o 1077.37060546875
  o 1076.40478515625
  o 1067.57958984375
```

* SILENCE_DURATION

無音区間と判定する秒数を指定します。スクリプトはrecorder, transcripter, uploaderの3つのスレッドで動作しており、recorderは無音区間ごとにバッファを切り出してキューに積み後段のtranscripter, uploaderに渡します。
ニュース映像などでは 1秒前後が良さそうでした。一般のYoutubeビデオではBGMなども流れ、あまり無音にならない様にしているようで上のTHRESHOLDと合わせて調整が必要かもしれません。

### gInputDeviceIndex

Loopbackのインストールを参照

## そのほか

libwhisper.soの利用については下記のサイトを参考にしました。
https://zenn.dev/k41531/articles/ab1b42c044117b

掲載されているスクリプトを改修したものが`test-whisper-so.py`です。
whisper.hの内容が大きく変更されているためWhisperFullParamsの定義の修正が必要でした。

whisperに渡すパラメタの調整について下記を参考にしました（今後します）。
https://note.com/asahi_ictrad/n/nf3ca329f17df

whisper.cppに関連する網羅的な検討がなされています。temperature設定や、音声の区切り方について参考になりそうです。
