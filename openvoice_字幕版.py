# -*- coding: utf-8 -*-
"""OpenVoice 字幕版

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1MDRkW6RaapyoIAa6KIYMz0vIqN8o5TZ6
"""

# Commented out IPython magic to ensure Python compatibility.
!git clone https://github.com/KevinWang676/OpenVoice-for-srt.git
# %cd OpenVoice-for-srt
!pip install -r requirements.txt
import urllib.request
urllib.request.urlretrieve("https://huggingface.co/spaces/kevinwang676/OpenVoice/resolve/main/checkpoints_1226.zip", "checkpoints_1226.zip")
import zipfile
with zipfile.ZipFile("checkpoints_1226.zip", 'r') as zip_ref:
    zip_ref.extractall("")

import os
import torch
from openvoice import se_extractor
from openvoice.api import BaseSpeakerTTS, ToneColorConverter

if torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

ckpt_base = 'checkpoints/base_speakers/EN'
ckpt_converter = 'checkpoints/converter'
base_speaker_tts = BaseSpeakerTTS(f'{ckpt_base}/config.json', device=device)
base_speaker_tts.load_ckpt(f'{ckpt_base}/checkpoint.pth')

tone_color_converter = ToneColorConverter(f'{ckpt_converter}/config.json', device=device)
tone_color_converter.load_ckpt(f'{ckpt_converter}/checkpoint.pth')

#source_se = torch.load(f'{ckpt_base}/en_default_se.pth').to(device)
#source_se_style = torch.load(f'{ckpt_base}/en_style_se.pth').to(device)

def vc_en(text, audio_ref, style_mode, save_path):
  if style_mode=="default":
    source_se = torch.load(f'{ckpt_base}/en_default_se.pth').to(device)
    reference_speaker = audio_ref
    target_se, audio_name = se_extractor.get_se(reference_speaker, tone_color_converter, target_dir='processed', vad=True)
    save_path = f"output/{save_path}.wav"

    # Run the base speaker tts
    src_path = "tmp.wav"
    base_speaker_tts.tts(text, src_path, speaker='default', language='English', speed=1.0)

    # Run the tone color converter
    encode_message = "@MyShell"
    tone_color_converter.convert(
        audio_src_path=src_path,
        src_se=source_se,
        tgt_se=target_se,
        output_path=save_path,
        message=encode_message)

  else:
    source_se = torch.load(f'{ckpt_base}/en_style_se.pth').to(device)
    reference_speaker = audio_ref
    target_se, audio_name = se_extractor.get_se(reference_speaker, tone_color_converter, target_dir='processed', vad=True)

    save_path = f"output/{save_path}.wav"

    # Run the base speaker tts
    src_path = "tmp.wav"
    base_speaker_tts.tts(text, src_path, speaker=style_mode, language='English', speed=1.0)

    # Run the tone color converter
    encode_message = "@MyShell"
    tone_color_converter.convert(
        audio_src_path=src_path,
        src_se=source_se,
        tgt_se=target_se,
        output_path=save_path,
        message=encode_message)

  return f"output/{save_path}.wav"

class subtitle:
    def __init__(self,index:int, start_time, end_time, text:str):
        self.index = int(index)
        self.start_time = start_time
        self.end_time = end_time
        self.text = text.strip()
    def normalize(self,ntype:str,fps=30):
         if ntype=="prcsv":
              h,m,s,fs=(self.start_time.replace(';',':')).split(":")#seconds
              self.start_time=int(h)*3600+int(m)*60+int(s)+round(int(fs)/fps,2)
              h,m,s,fs=(self.end_time.replace(';',':')).split(":")
              self.end_time=int(h)*3600+int(m)*60+int(s)+round(int(fs)/fps,2)
         elif ntype=="srt":
             h,m,s=self.start_time.split(":")
             s=s.replace(",",".")
             self.start_time=int(h)*3600+int(m)*60+round(float(s),2)
             h,m,s=self.end_time.split(":")
             s=s.replace(",",".")
             self.end_time=int(h)*3600+int(m)*60+round(float(s),2)
         else:
             raise ValueError
    def add_offset(self,offset=0):
        self.start_time+=offset
        if self.start_time<0:
            self.start_time=0
        self.end_time+=offset
        if self.end_time<0:
            self.end_time=0
    def __str__(self) -> str:
        return f'id:{self.index},start:{self.start_time},end:{self.end_time},text:{self.text}'

def read_srt(filename):
    offset=0
    with open(filename,"r",encoding="utf-8") as f:
        file=f.readlines()
    subtitle_list=[]
    indexlist=[]
    filelength=len(file)
    for i in range(0,filelength):
        if " --> " in file[i]:
            is_st=True
            for char in file[i-1].strip().replace("\ufeff",""):
                if char not in ['0','1','2','3','4','5','6','7','8','9']:
                    is_st=False
                    break
            if is_st:
                indexlist.append(i) #get line id
    listlength=len(indexlist)
    for i in range(0,listlength-1):
        st,et=file[indexlist[i]].split(" --> ")
        id=int(file[indexlist[i]-1].strip().replace("\ufeff",""))
        text=""
        for x in range(indexlist[i]+1,indexlist[i+1]-2):
            text+=file[x]
        st=subtitle(id,st,et,text)
        st.normalize(ntype="srt")
        st.add_offset(offset=offset)
        subtitle_list.append(st)
    st,et=file[indexlist[-1]].split(" --> ")
    id=file[indexlist[-1]-1]
    text=""
    for x in range(indexlist[-1]+1,filelength):
        text+=file[x]
    st=subtitle(id,st,et,text)
    st.normalize(ntype="srt")
    st.add_offset(offset=offset)
    subtitle_list.append(st)
    return subtitle_list

subtitle_list = read_srt("subtitle.srt")
for i in subtitle_list:
  os.makedirs("output", exist_ok=True)
  print(f"正在合成第{i.index}条语音")
  print(f"语音内容：{i.text.splitlines()[0]}")
  vc_en(i.text.splitlines()[0], "trump.wav", "sad", i.text.splitlines()[1].replace(" ", "") + str(i.index))

