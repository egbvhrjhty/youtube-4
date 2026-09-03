# =======================================================================
# 🟢 EASY CUSTOMIZATION BLOCK (सिर्फ इसे बदलें अपने 20 चैनल्स के लिए!) 🟢
# =======================================================================

BGM_FILE = "./bgm.mp3" 
BGM_VOLUME = 0.25      

VOICE_QUESTION = "hi-IN-MadhurNeural" 
VOICE_ANSWER = "hi-IN-SwaraNeural"    
VOICE_SPEED = "+0%"                   

TIMER_SECONDS = 5.0  

BG_COLORS = [
    (15, 32, 39),   
    (66, 39, 9),    
    (60, 10, 10)    
]

THUMB_TEMPLATE = "./thumb_template.jpg" 
THUMB_BG_COLORS = [(20, 20, 40), (40, 10, 10), (10, 40, 10), (30, 0, 30)] 
THUMB_HOOKS = ["99% लोग फेल! 🤔", "दिमाग हिला देने वाले सवाल! 🤯", "क्या आप जवाब दे पाएंगे? 👀"]

YT_TITLES = [
    "Most Important GK Questions in Hindi 🔥 | Test Mode",
]
YT_DESC_ADDON = "टेस्टिंग मोड वीडियो।"
YT_TAGS_POOL = [["gk", "hindi gk", "test"]]

HINDI_FONT = "./NirmalaB.ttf" 

# =======================================================================
# 🛑 STOP! DO NOT EDIT BELOW THIS LINE 🛑
# =======================================================================

import os, random, time, json, asyncio, sys, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

try: resample_filter = Image.Resampling.LANCZOS
except AttributeError: resample_filter = Image.ANTIALIAS
Image.ANTIALIAS = resample_filter

import edge_tts
from moviepy.editor import AudioFileClip, TextClip, ColorClip, ImageClip, CompositeVideoClip, CompositeAudioClip
from moviepy.audio.AudioClip import AudioClip
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

OUTPUT_FOLDER = "./output"
TEMP_FOLDER = "./temp"
JSON_FILE_PATH = "./questions.json"
TOKENS_FOLDER = "./tokens"  
THUMBNAIL_FILE = "./output/thumbnail.jpg"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

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

async def generate_voice(text, filename, voice_type="male"):
    filepath = os.path.join(TEMP_FOLDER, filename)
    voice_name = VOICE_QUESTION if voice_type == "male" else VOICE_ANSWER
    try:
        communicate = edge_tts.Communicate(text, voice_name, rate=VOICE_SPEED, volume="+50%")
        await communicate.save(filepath)
    except:
        tts = gTTS(text=text, lang='hi')
        tts.save(filepath)
    return filepath

def make_tick_sfx(duration=TIMER_SECONDS):
    def sound_wave(t):
        t_mod = t % 1.0
        click = np.sin(2 * np.pi * 1000 * t_mod) * np.exp(-60 * t_mod)
        return np.where(t_mod < 0.1, click, 0)
    return AudioClip(lambda t: np.vstack([sound_wave(t), sound_wave(t)]).T, duration=duration, fps=44100).volumex(1.5)

# 🧪 TEST MODE LOGIC (Fixed 4 Questions)
async def prepare_test_questions():
    print(f"🎯 Test Mode: सिर्फ 4 सवाल ले रहा हूँ...")
    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f: all_q = json.load(f)

    if len(all_q) < 4:
        print("❌ Error: JSON में 4 सवाल भी नहीं हैं!")
        sys.exit(1)

    used_quizzes = all_q[:4]

    for i, quiz in enumerate(used_quizzes):
        text_a = quiz['opt_a'].replace("A)", "").strip()
        text_b = quiz['opt_b'].replace("B)", "").strip()
        text_c = quiz['opt_c'].replace("C)", "").strip()
        correct_key = quiz['correct_key']
        correct_ans_text = text_a if correct_key == 'A' else text_b if correct_key == 'B' else text_c

        speech_q_opts = f"{quiz['question']}... ऑप्शन ए, {text_a}... ऑप्शन बी, {text_b}... ऑप्शन सी, {text_c}"
        speech_ans = f"सही जवाब है, {correct_ans_text}"

        q_path = await generate_voice(speech_q_opts, f"q_{i}.mp3", "male")
        a_path = await generate_voice(speech_ans, f"a_{i}.mp3", "female")

        quiz['q_audio'] = q_path
        quiz['a_audio'] = a_path

    # Last question suspense
    last_q = used_quizzes[-1]
    suspense_path = await generate_voice("इसका जवाब आप कमेंट्स में बताइए!", f"a_last.mp3", "female")
    last_q['a_audio'] = suspense_path

    remaining = all_q[4:]
    with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f: json.dump(remaining, f, ensure_ascii=False, indent=4)
    return used_quizzes

def create_thumbnail_intro(total_q):
    print(f"🎨 Template से Thumbnail Intro बना रहा है ({total_q} Questions)...")
    if os.path.exists(THUMB_TEMPLATE):
        img = Image.open(THUMB_TEMPLATE).convert('RGB')
        img = img.resize((1920, 1080))
    else:
        print("⚠️ thumb_template.jpg नहीं मिली! बैकअप कलर यूज़ कर रहा है।")
        img = Image.new('RGB', (1920, 1080), color=random.choice(THUMB_BG_COLORS))
        
    d = ImageDraw.Draw(img)
    try: font_super_large = ImageFont.truetype(HINDI_FONT, 200)
    except: font_super_large = ImageFont.load_default()

    dynamic_text = f"TOP {total_q}"
    d.text((550, 70), dynamic_text, fill=(255, 230, 0), font=font_super_large, stroke_width=15, stroke_fill=(0, 0, 0))
    
    if not os.path.exists(THUMB_TEMPLATE):
        try: f_small = ImageFont.truetype(HINDI_FONT, 80)
        except: f_small = ImageFont.load_default()
        d.text((100, 800), random.choice(THUMB_HOOKS), fill=(255, 50, 50), font=f_small)

    # 🛠️ BUG FIXED HERE (THUMBNAIL_FILE instead of THUMB_FILE)
    img.save(THUMBNAIL_FILE)
    intro_clip = ImageClip(THUMBNAIL_FILE).set_duration(3).set_fps(24)
    silent_audio = AudioClip(lambda t: [0, 0], duration=3, fps=44100)
    intro_clip = intro_clip.set_audio(silent_audio)
    
    intro_path = os.path.join(TEMP_FOLDER, "chunk_0_intro.mp4")
    intro_clip.write_videofile(intro_path, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
    intro_clip.close(); silent_audio.close()
    return intro_path

async def make_video_chunk(quiz, index, total_q):
    print(f"\n🎬 रेंडर: सवाल {index}/{total_q}")
    
    if index <= (total_q * 0.3): bg_color = BG_COLORS[0] 
    elif index <= (total_q * 0.7): bg_color = BG_COLORS[1] 
    else: bg_color = BG_COLORS[2] 

    text_a = quiz['opt_a'].replace("A)", "").strip()
    text_b = quiz['opt_b'].replace("B)", "").strip()
    text_c = quiz['opt_c'].replace("C)", "").strip()
    correct_key = quiz['correct_key']
    is_last = (index == total_q)

    aud_q_opts = AudioFileClip(quiz['q_audio']).volumex(1.5)
    aud_ans = AudioFileClip(quiz['a_audio']).volumex(1.5)

    t = 0.0; s_q_opts = t; t += aud_q_opts.duration + 0.5
    s_timer = t; t += TIMER_SECONDS
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

    tick = make_tick_sfx(TIMER_SECONDS).set_start(s_timer)
    timer_vis = [TextClip(f"{int(TIMER_SECONDS)-i}", fontsize=130, color='red' if int(TIMER_SECONDS)-i<=3 else 'yellow', font='Arial-Bold').set_position(('center', 800)).set_start(s_timer+i).set_duration(1.0) for i in range(int(TIMER_SECONDS))]

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

def merge_videos_and_add_bgm(chunk_files, total_q):
    print(f"🔄 {total_q + 1} वीडियो (Intro + Questions) जोड़े जा रहे हैं...")
    concat_txt = os.path.abspath(os.path.join(TEMP_FOLDER, "files.txt"))
    with open(concat_txt, "w") as f:
        for chunk in chunk_files: f.write(f"file '{os.path.abspath(chunk)}'\n")
    
    merged_no_bgm = os.path.abspath(os.path.join(OUTPUT_FOLDER, "merged_no_bgm.mp4"))
    final_output = os.path.abspath(os.path.join(OUTPUT_FOLDER, "FINAL_UPLOAD.mp4"))
    
    os.system(f"ffmpeg -f concat -safe 0 -i {concat_txt} -c copy {merged_no_bgm} -y")
    
    if os.path.exists(BGM_FILE) and os.path.exists(merged_no_bgm):
        bgm_abs = os.path.abspath(BGM_FILE)
        cmd = f'ffmpeg -i {merged_no_bgm} -stream_loop -1 -i {bgm_abs} -filter_complex "[1:a]volume={BGM_VOLUME}[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac {final_output} -y'
        os.system(cmd)
    else: 
        print("⚠️ bgm.mp3 नहीं मिला! बिना म्यूजिक के वीडियो बन रही है।")
        if os.path.exists(merged_no_bgm): os.rename(merged_no_bgm, final_output)
    return final_output

def upload_to_youtube(video_file, total_q):
    print("🌐 YouTube पर अपलोड हो रहा है...")
    token_files = sorted([os.path.join(TOKENS_FOLDER, f) for f in os.listdir(TOKENS_FOLDER) if f.endswith('.json')])
    
    yt_title = f"{total_q} {random.choice(YT_TITLES)}"
    yt_desc = f"{yt_title}\n\n{YT_DESC_ADDON}\n\n#quiz"
    yt_tags = random.choice(YT_TAGS_POOL)
    
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

async def main():
    print(f"🤖 Test Mode: वीडियो बनाने से पहले 5 सेकंड इंतज़ार कर रहा है...")
    time.sleep(5) 
    
    quizzes = await prepare_test_questions()
    total_q = len(quizzes)
    
    intro_path = create_thumbnail_intro(total_q)
    chunk_files = [intro_path]
    
    for i, quiz in enumerate(quizzes):
        chunk_path = await make_video_chunk(quiz, i+1, total_q)
        chunk_files.append(chunk_path)
        
    final_video = merge_videos_and_add_bgm(chunk_files, total_q)
    upload_to_youtube(final_video, total_q)

if __name__ == "__main__":
    asyncio.run(main())
