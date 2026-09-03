import os
import random
import time
import json
import asyncio
import sys
import numpy as np
import textwrap
import urllib.request
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

# 🛠️ MoviePy PIL Deprecation Fix
try:
    resample_filter = Image.Resampling.LANCZOS
except AttributeError:
    resample_filter = Image.ANTIALIAS
Image.ANTIALIAS = resample_filter

import edge_tts
from moviepy.editor import AudioFileClip, TextClip, ColorClip, ImageClip, CompositeVideoClip, CompositeAudioClip
from moviepy.audio.AudioClip import AudioClip

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# ================== CONFIGURATION ==================
OUTPUT_FOLDER = "./output"
TEMP_FOLDER = "./temp"
JSON_FILE_PATH = "./questions.json"
TOKENS_FOLDER = "./tokens"  
HINDI_FONT = "./NirmalaB.ttf"
BGM_FILE = "./bgm.mp3"
THUMBNAIL_FILE = "./output/thumbnail.jpg"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

HOOKS = ["99% लोग फेल! 🤔", "दिमाग हिला देने वाले सवाल! 🤯", "क्या आप जवाब दे पाएंगे? 👀", "IAS इंटरव्यू के सवाल! 💼"]
COLORS = [(20, 20, 40), (40, 10, 10), (10, 40, 10), (30, 0, 30), (0, 30, 40)] 

TAGS_POOL = [
    ["gk", "hindi gk", "mega quiz", "gk test", "education"],
    ["general knowledge", "gk in hindi", "top gk", "gk challenge"],
    ["upsc gk", "ssc gk", "competitive exams gk", "hindi questions"]
]

# ================== AUTO DOWNLOAD BGM ==================
if not os.path.exists(BGM_FILE):
    try: urllib.request.urlretrieve("https://cdn.pixabay.com/download/audio/2022/05/16/audio_91b2c451db.mp3", BGM_FILE)
    except: pass

# ================== PERFECT HINDI TEXT ==================
def get_hindi_image_clip(text, filename, font_size, color_rgb, width_limit=50):
    font = ImageFont.truetype(HINDI_FONT, font_size)
    lines = textwrap.wrap(text, width=width_limit) 
    dummy_img = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    y_text = 0; max_w = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        max_w = max(max_w, bbox[2] - bbox[0])
        y_text += (bbox[3] - bbox[1]) + 15
    img = Image.new('RGBA', (max_w + 20, y_text + 20), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    y_text = 10
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((max_w - w) / 2 + 10, y_text), line, font=font, fill=color_rgb)
        y_text += (bbox[3] - bbox[1]) + 15
    filepath = os.path.join(TEMP_FOLDER, filename)
    img.save(filepath)
    return ImageClip(filepath)

# ================== TTS ==================
async def generate_voice(text, filename, voice_type="male"):
    filepath = os.path.join(TEMP_FOLDER, filename)
    voice_name = "hi-IN-MadhurNeural" if voice_type == "male" else "hi-IN-SwaraNeural"
    try:
        communicate = edge_tts.Communicate(text, voice_name, rate="+0%", volume="+50%")
        await communicate.save(filepath)
    except:
        tts = gTTS(text=text, lang='hi')
        tts.save(filepath)
    return filepath

# ================== SFX ==================
def make_tick_sfx(duration=5.0):
    def sound_wave(t):
        t_mod = t % 1.0
        click = np.sin(2 * np.pi * 1000 * t_mod) * np.exp(-60 * t_mod)
        return np.where(t_mod < 0.1, click, 0)
    return AudioClip(lambda t: np.vstack([sound_wave(t), sound_wave(t)]).T, duration=duration, fps=44100).volumex(1.5)

# ================== DYNAMIC TIME CALCULATOR (THE BRAIN) ==================
async def prepare_questions_by_time():
    target_seconds = random.randint(13*60, 14*60) # 13 to 14 mins
    print(f"🎯 Target Time: {target_seconds // 60} min {target_seconds % 60} sec")

    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
        all_q = json.load(f)

    used_quizzes = []
    current_time = 3.0 # 3 seconds for intro

    for i, quiz in enumerate(all_q):
        text_a = quiz['opt_a'].replace("A)", "").strip()
        text_b = quiz['opt_b'].replace("B)", "").strip()
        text_c = quiz['opt_c'].replace("C)", "").strip()
        correct_key = quiz['correct_key']
        correct_ans_text = text_a if correct_key == 'A' else text_b if correct_key == 'B' else text_c

        speech_q_opts = f"{quiz['question']}... ऑप्शन ए, {text_a}... ऑप्शन बी, {text_b}... ऑप्शन सी, {text_c}"
        speech_ans = f"सही जवाब है, {correct_ans_text}"

        q_path = await generate_voice(speech_q_opts, f"q_{i}.mp3", "male")
        a_path = await generate_voice(speech_ans, f"a_{i}.mp3", "female")

        # Measure exact duration
        q_clip = AudioFileClip(q_path)
        a_clip = AudioFileClip(a_path)
        chunk_dur = q_clip.duration + 0.5 + 5.0 + a_clip.duration + 1.5
        q_clip.close(); a_clip.close()

        # Check if adding this question exceeds our target time
        if current_time + chunk_dur > target_seconds and len(used_quizzes) >= 15:
            print(f"✅ Target time reached! Total selected questions: {len(used_quizzes)}")
            break

        quiz['q_audio'] = q_path
        quiz['a_audio'] = a_path
        used_quizzes.append(quiz)
        current_time += chunk_dur

    # Change the last question's answer to Suspense!
    last_q = used_quizzes[-1]
    suspense_path = await generate_voice("इसका जवाब आप कमेंट्स में बताइए!", f"a_last.mp3", "female")
    last_q['a_audio'] = suspense_path

    # Delete used questions
    remaining = all_q[len(used_quizzes):]
    with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(remaining, f, ensure_ascii=False, indent=4)
        
    return used_quizzes

# ================== RANDOM THUMBNAIL INTRO ==================
def create_thumbnail_intro(first_question_text, total_q):
    print(f"🎨 Thumbnail Intro बना रहा है ({total_q} Questions)...")
    bg_color = random.choice(COLORS)
    hook_text = random.choice(HOOKS)
    
    img = Image.new('RGB', (1920, 1080), color=bg_color)
    d = ImageDraw.Draw(img)
    try: font_l = ImageFont.truetype(HINDI_FONT, 120); font_s = ImageFont.truetype(HINDI_FONT, 80)
    except: font_l = ImageFont.load_default(); font_s = font_l

    d.text((100, 150), f"🔥 {total_q} MEGA GK QUIZ 🔥", fill=(255, 200, 0), font=font_l)
    d.text((100, 400), first_question_text[:50] + "...", fill=(255, 255, 255), font=font_s)
    d.text((100, 800), hook_text, fill=(255, 50, 50), font=font_l)
    img.save(THUMBNAIL_FILE)
    
    intro_clip = ImageClip(THUMBNAIL_FILE).set_duration(3).set_fps(24)
    intro_path = os.path.join(TEMP_FOLDER, "chunk_0_intro.mp4")
    intro_clip.write_videofile(intro_path, codec="libx264", fps=24, preset="ultrafast", logger=None)
    intro_clip.close()
    return intro_path

# ================== VIDEO GENERATOR LOOP ==================
async def make_video_chunk(quiz, index, total_q):
    print(f"\n🎬 रेंडर: सवाल {index}/{total_q}")
    
    if index <= (total_q * 0.3): bg_color = (15, 32, 39) 
    elif index <= (total_q * 0.7): bg_color = (66, 39, 9) 
    else: bg_color = (60, 10, 10) 

    text_a = quiz['opt_a'].replace("A)", "").strip()
    text_b = quiz['opt_b'].replace("B)", "").strip()
    text_c = quiz['opt_c'].replace("C)", "").strip()
    correct_key = quiz['correct_key']
    is_last = (index == total_q)

    # Use pre-generated audio
    aud_q_opts = AudioFileClip(quiz['q_audio']).volumex(1.5)
    aud_ans = AudioFileClip(quiz['a_audio']).volumex(1.5)

    t = 0.0; s_q_opts = t; t += aud_q_opts.duration + 0.5
    timer_dur = 5.0; s_timer = t; t += timer_dur
    s_ans = t; t += aud_ans.duration + 1.5; total = t

    bg = ColorClip(size=(1920, 1080), color=bg_color).set_duration(total).set_fps(24)
    
    lvl_text = "LEVEL: EASY" if index <= (total_q * 0.3) else "LEVEL: MEDIUM" if index <= (total_q * 0.7) else "LEVEL: HARD 🔥"
    lvl_clip = TextClip(lvl_text, fontsize=45, color='yellow', font='Arial-Bold').set_position((50, 40)).set_start(0).set_duration(total)
    prog_clip = TextClip(f"Q: {index}/{total_q}", fontsize=45, color='white', font='Arial-Bold').set_position((1700, 40)).set_start(0).set_duration(total)

    q_clip = get_hindi_image_clip(quiz['question'], f"img_q_{index}.png", 85, (255,255,255)).set_position(('center', 150)).set_start(0).set_duration(total)
    
    y_opts = 450
    opt_a_clip = get_hindi_image_clip(f"A) {text_a}", f"img_a_{index}.png", 75, (255,255,255), 60).set_position((250, y_opts)).set_start(0).set_duration(total)
    opt_b_clip = get_hindi_image_clip(f"B) {text_b}", f"img_b_{index}.png", 75, (255,255,255), 60).set_position((250, y_opts+130)).set_start(0).set_duration(total)
    opt_c_clip = get_hindi_image_clip(f"C) {text_c}", f"img_c_{index}.png", 75, (255,255,255), 60).set_position((250, y_opts+260)).set_start(0).set_duration(total)

    tick = make_tick_sfx(timer_dur).set_start(s_timer)
    timer_vis = [TextClip(f"{int(timer_dur)-i}", fontsize=130, color='red' if int(timer_dur)-i<=3 else 'yellow', font='Arial-Bold').set_position(('center', 800)).set_start(s_timer+i).set_duration(1.0) for i in range(int(timer_dur))]

    ans_clip = None
    if not is_last:
        y_ans = y_opts if correct_key == 'A' else (y_opts+130) if correct_key == 'B' else (y_opts+260)
        ans_text = f"{correct_key}) " + (text_a if correct_key == 'A' else text_b if correct_key == 'B' else text_c)
        ans_clip = get_hindi_image_clip(ans_text, f"img_ans_{index}.png", 75, (0, 255, 0), 60).set_position((250, y_ans)).set_start(s_ans).set_duration(total - s_ans)
        ans_clip = ans_clip.resize(lambda t: min(1.15, 1 + t*1.5) if t < 0.1 else 1.15)

    final_audio = CompositeAudioClip([aud_q_opts.set_start(s_q_opts), tick, aud_ans.set_start(s_ans)])
    visuals = [bg, lvl_clip, prog_clip, q_clip, opt_a_clip, opt_b_clip, opt_c_clip] + timer_vis
    if ans_clip: visuals.append(ans_clip)
    
    if is_last:
        suspense = get_hindi_image_clip("👇 कमेंट में अपना जवाब दें! 👇", f"img_susp_{index}.png", 85, (0, 255, 255)).set_position(('center', 800)).set_start(s_ans).set_duration(total - s_ans)
        visuals.append(suspense)

    video = CompositeVideoClip(visuals).set_audio(final_audio)
    out_path = os.path.join(TEMP_FOLDER, f"chunk_{index}.mp4")
    video.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
    
    for c in visuals: c.close()
    video.close(); final_audio.close(); aud_q_opts.close(); aud_ans.close()
    return out_path

# ================== MERGE & BGM ==================
def merge_videos_and_add_bgm(chunk_files, total_q):
    print(f"🔄 {total_q} वीडियो जोड़े जा रहे हैं...")
    concat_txt = os.path.join(TEMP_FOLDER, "files.txt")
    with open(concat_txt, "w") as f:
        for chunk in chunk_files: f.write(f"file '{os.path.basename(chunk)}'\n")
    
    merged_no_bgm = os.path.join(OUTPUT_FOLDER, "merged_no_bgm.mp4")
    final_output = os.path.join(OUTPUT_FOLDER, "FINAL_UPLOAD.mp4")
    os.system(f"ffmpeg -f concat -safe 0 -i {concat_txt} -c copy {merged_no_bgm} -y")
    
    if os.path.exists(BGM_FILE):
        cmd = f'ffmpeg -i {merged_no_bgm} -stream_loop -1 -i {BGM_FILE} -filter_complex "[1:a]volume=0.25[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac {final_output} -y'
        os.system(cmd)
    else: os.rename(merged_no_bgm, final_output)
    return final_output

# ================== YOUTUBE UPLOAD ==================
def upload_to_youtube(video_file, total_q):
    print("🌐 YouTube पर अपलोड हो रहा है...")
    token_files = sorted([os.path.join(TOKENS_FOLDER, f) for f in os.listdir(TOKENS_FOLDER) if f.endswith('.json')])
    
    # 🎲 Dynamic Title logic
    TITLES = [
        f"{total_q} Most Important GK Questions in Hindi 🔥 | Mega Quiz",
        f"Top {total_q} GK Quiz in Hindi 🤔 | General Knowledge Test",
        f"{total_q} GK Questions That Will Blow Your Mind 🤯 | Hindi GK"
    ]
    yt_title = random.choice(TITLES)
    yt_desc = f"{yt_title}\n\nइस वीडियो में {total_q} महत्वपूर्ण GK के सवाल हैं। देखते हैं आप कितनों का सही जवाब दे पाते हैं!\n\nआखिरी सवाल का जवाब कमेंट में ज़रूर बताएं! 👇\n\n#gk #gkinhindi #education #quiz"
    yt_tags = random.choice(TAGS_POOL)
    
    request_body = {
        "snippet": {"title": yt_title, "description": yt_desc, "tags": yt_tags, "categoryId": "27"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }

    for token_path in token_files:
        try:
            creds = Credentials.from_authorized_user_file(token_path, ["https://www.googleapis.com/auth/youtube.upload"])
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, 'w') as tf: tf.write(creds.to_json())
                    
            youtube = build('youtube', 'v3', credentials=creds)
            media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
            request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
            response = request.execute()
            print(f"✅ तहलका! वीडियो LIVE: https://youtu.be/{response['id']}")
            return True
        except Exception as e:
            print(f"❌ अपलोड एरर: {e}")
            continue
    return False

# ================== MAIN EXECUTION ==================
async def main():
    wait_time = random.randint(300, 1800) 
    print(f"🤖 Anti-Bot: वीडियो बनाने से पहले {wait_time // 60} मिनट इंतज़ार कर रहा है...")
    time.sleep(wait_time) 
    
    # 1. AI Time & Question Selector
    quizzes = await prepare_questions_by_time()
    total_q = len(quizzes)
    
    # 2. Intro
    intro_path = create_thumbnail_intro(quizzes[0]['question'], total_q)
    chunk_files = [intro_path]
    
    # 3. Render
    for i, quiz in enumerate(quizzes):
        chunk_path = await make_video_chunk(quiz, i+1, total_q)
        chunk_files.append(chunk_path)
        
    # 4. Merge
    final_video = merge_videos_and_add_bgm(chunk_files, total_q)
    
    # 5. Upload
    upload_to_youtube(final_video, total_q)

if __name__ == "__main__":
    asyncio.run(main())
