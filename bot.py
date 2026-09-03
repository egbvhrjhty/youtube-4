# =======================================================================
# 🟢 EASY CUSTOMIZATION BLOCK (सिर्फ इसे बदलें) 🟢
# =======================================================================

BGM_FILE = "./bgm.mp3" 
BGM_VOLUME = 0.25      

VOICE_QUESTION = "hi-IN-MadhurNeural" 
VOICE_ANSWER = "hi-IN-SwaraNeural"    
VOICE_SPEED = "+0%"                   

TIMER_SECONDS = 5.0  

BG_COLORS = [(15, 32, 39), (66, 39, 9), (60, 10, 10)]

# 👻 WATERMARK SETTINGS (चैनल का नाम)
CHANNEL_WATERMARK = "Zoom Mind" # यहाँ अपने चैनल का नाम लिखें

THUMB_TEMPLATE = "./thumb_template.jpg" 
HINDI_FONT = "./NirmalaB.ttf" 

# =======================================================================
# 🛑 STOP! DO NOT EDIT BELOW THIS LINE 🛑
# =======================================================================

import os, random, time, json, asyncio, sys, textwrap, urllib.request, urllib.parse
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

try: resample_filter = Image.Resampling.LANCZOS
except AttributeError: resample_filter = Image.ANTIALIAS
Image.ANTIALIAS = resample_filter

import edge_tts
from moviepy.editor import AudioFileClip, TextClip, ColorClip, ImageClip, CompositeVideoClip, CompositeAudioClip
from moviepy.audio.AudioClip import AudioClip

OUTPUT_FOLDER = "./output"
TEMP_FOLDER = "./temp"
JSON_FILE_PATH = "./questions.json"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# 🔍 AUTO WIKIPEDIA IMAGE FETCHER
def fetch_related_image(keyword, index):
    print(f"🔍 '{keyword}' के लिए फोटो ढूँढ रहा हूँ...")
    img_path = os.path.join(TEMP_FOLDER, f"img_{index}.jpg")
    try:
        encoded_kw = urllib.parse.quote(keyword)
        url = f"https://hi.wikipedia.org/w/api.php?action=query&prop=pageimages&titles={encoded_kw}&format=json&pithumbsize=600"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req).read().decode('utf-8')
        data = json.loads(response)
        pages = data['query']['pages']
        for page_id in pages:
            if 'thumbnail' in pages[page_id]:
                img_url = pages[page_id]['thumbnail']['source']
                urllib.request.urlretrieve(img_url, img_path)
                print("✅ फोटो मिल गई!")
                return img_path
    except Exception as e:
        print(f"⚠️ फोटो नहीं मिली: {e}")
    return None

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
        # Align Left
        draw.text((10, y_text), line, font=font, fill=color_rgb)
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

        quiz['q_audio'] = await generate_voice(speech_q_opts, f"q_{i}.mp3", "male")
        quiz['a_audio'] = await generate_voice(speech_ans, f"a_{i}.mp3", "female")

    last_q = used_quizzes[-1]
    last_q['a_audio'] = await generate_voice("इसका जवाब आप कमेंट्स में बताइए!", f"a_last.mp3", "female")
    return used_quizzes

async def make_video_chunk(quiz, index, total_q):
    print(f"\n🎬 रेंडर: सवाल {index}/{total_q}")
    
    bg_color = BG_COLORS[0] # Test mode color
    text_a = quiz['opt_a'].replace("A)", "").strip()
    text_b = quiz['opt_b'].replace("B)", "").strip()
    text_c = quiz['opt_c'].replace("C)", "").strip()
    correct_key = quiz['correct_key']
    is_last = (index == total_q)
    correct_ans_text = text_a if correct_key == 'A' else text_b if correct_key == 'B' else text_c

    aud_q_opts = AudioFileClip(quiz['q_audio']).volumex(1.5)
    aud_ans = AudioFileClip(quiz['a_audio']).volumex(1.5)

    t = 0.0; s_q_opts = t; t += aud_q_opts.duration + 0.5
    s_timer = t; t += TIMER_SECONDS
    s_ans = t; t += aud_ans.duration + 1.5; total = t

    bg = ColorClip(size=(1920, 1080), color=bg_color).set_duration(total).set_fps(24)
    
    # 👻 WATERMARK
    watermark = TextClip(CHANNEL_WATERMARK, fontsize=120, color='white', font='Arial-Bold').set_opacity(0.05).set_position('center').set_duration(total)

    lvl_clip = TextClip("LEVEL: EASY", fontsize=45, color='yellow', font='Arial-Bold').set_position((50, 40)).set_duration(total)
    prog_clip = TextClip(f"Q: {index}/{total_q}", fontsize=45, color='white', font='Arial-Bold').set_position((1700, 40)).set_duration(total)

    # 🖼️ Auto Image on Right Side
    side_image_clip = None
    img_path = fetch_related_image(correct_ans_text, index)
    if img_path:
        side_image_clip = ImageClip(img_path).resize(width=600).set_position((1200, 'center')).set_duration(total)

    q_clip = get_hindi_image_clip(quiz['question'], f"img_q_{index}.png", 85, (255,255,255), 45).set_position((100, 150)).set_start(0).set_duration(total)
    
    y_opts = 450
    # 🌟 EXACT TEXT REPLACEMENT LOGIC (No Bounce)
    opt_a_white = get_hindi_image_clip(f"A) {text_a}", f"img_a_{index}.png", 75, (255,255,255), 45)
    opt_b_white = get_hindi_image_clip(f"B) {text_b}", f"img_b_{index}.png", 75, (255,255,255), 45)
    opt_c_white = get_hindi_image_clip(f"C) {text_c}", f"img_c_{index}.png", 75, (255,255,255), 45)

    if correct_key == 'A':
        opt_a_clip = opt_a_white.set_position((150, y_opts)).set_start(0).set_end(s_ans)
        ans_clip = get_hindi_image_clip(f"A) {text_a}", f"ans_{index}.png", 75, (0,255,0), 45).set_position((150, y_opts)).set_start(s_ans).set_duration(total - s_ans)
        opt_b_clip = opt_b_white.set_position((150, y_opts+130)).set_duration(total)
        opt_c_clip = opt_c_white.set_position((150, y_opts+260)).set_duration(total)
    elif correct_key == 'B':
        opt_a_clip = opt_a_white.set_position((150, y_opts)).set_duration(total)
        opt_b_clip = opt_b_white.set_position((150, y_opts+130)).set_start(0).set_end(s_ans)
        ans_clip = get_hindi_image_clip(f"B) {text_b}", f"ans_{index}.png", 75, (0,255,0), 45).set_position((150, y_opts+130)).set_start(s_ans).set_duration(total - s_ans)
        opt_c_clip = opt_c_white.set_position((150, y_opts+260)).set_duration(total)
    else:
        opt_a_clip = opt_a_white.set_position((150, y_opts)).set_duration(total)
        opt_b_clip = opt_b_white.set_position((150, y_opts+130)).set_duration(total)
        opt_c_clip = opt_c_white.set_position((150, y_opts+260)).set_start(0).set_end(s_ans)
        ans_clip = get_hindi_image_clip(f"C) {text_c}", f"ans_{index}.png", 75, (0,255,0), 45).set_position((150, y_opts+260)).set_start(s_ans).set_duration(total - s_ans)

    tick = make_tick_sfx(TIMER_SECONDS).set_start(s_timer)
    timer_vis = [TextClip(f"0{int(TIMER_SECONDS)-i}" if (int(TIMER_SECONDS)-i)<10 else f"{int(TIMER_SECONDS)-i}", fontsize=130, color='red' if int(TIMER_SECONDS)-i<=3 else 'yellow', font='Arial-Bold').set_position(('center', 800)).set_start(s_timer+i).set_duration(1.0) for i in range(int(TIMER_SECONDS))]

    final_audio = CompositeAudioClip([aud_q_opts.set_start(s_q_opts), tick, aud_ans.set_start(s_ans)])
    visuals = [bg, watermark, lvl_clip, prog_clip, q_clip, opt_a_clip, opt_b_clip, opt_c_clip] + timer_vis
    
    if side_image_clip: visuals.append(side_image_clip)
    if not is_last: visuals.append(ans_clip)
    
    if is_last:
        suspense = get_hindi_image_clip("👇 कमेंट में अपना जवाब दें! 👇", f"img_susp_{index}.png", 85, (0, 255, 255)).set_position(('center', 800)).set_start(s_ans).set_duration(total - s_ans)
        visuals.append(suspense)

    video = CompositeVideoClip(visuals).set_audio(final_audio)
    out_path = os.path.join(TEMP_FOLDER, f"chunk_{index}.mp4")
    video.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
    
    for c in visuals: c.close()
    video.close(); final_audio.close(); aud_q_opts.close(); aud_ans.close()
    return out_path

def merge_videos_and_add_bgm(chunk_files):
    print(f"🔄 वीडियो जोड़े जा रहे हैं...")
    concat_txt = os.path.abspath(os.path.join(TEMP_FOLDER, "files.txt"))
    with open(concat_txt, "w") as f:
        for chunk in chunk_files: f.write(f"file '{os.path.abspath(chunk)}'\n")
    
    merged_no_bgm = os.path.abspath(os.path.join(OUTPUT_FOLDER, "merged_no_bgm.mp4"))
    final_output = os.path.abspath(os.path.join(OUTPUT_FOLDER, "FINAL_UPLOAD.mp4"))
    
    # 🎵 BGM STUTTER FIX: Enforced strict audio formatting during merge
    os.system(f"ffmpeg -f concat -safe 0 -i {concat_txt} -c:v copy -c:a aac -b:a 192k {merged_no_bgm} -y")
    
    if os.path.exists(BGM_FILE) and os.path.exists(merged_no_bgm):
        bgm_abs = os.path.abspath(BGM_FILE)
        # 🎵 Flawless Audio Mixing
        cmd = f'ffmpeg -i {merged_no_bgm} -stream_loop -1 -i {bgm_abs} -filter_complex "[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a0];[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume={BGM_VOLUME}[a1];[a0][a1]amix=inputs=2:duration=first[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac {final_output} -y'
        os.system(cmd)
    else: 
        if os.path.exists(merged_no_bgm): os.rename(merged_no_bgm, final_output)
    return final_output

async def main():
    print(f"🤖 Test Mode: 5 सेकंड इंतज़ार...")
    time.sleep(5) 
    
    quizzes = await prepare_test_questions()
    total_q = len(quizzes)
    
    chunk_files = []
    for i, quiz in enumerate(quizzes):
        chunk_path = await make_video_chunk(quiz, i+1, total_q)
        chunk_files.append(chunk_path)
        
    final_video = merge_videos_and_add_bgm(chunk_files)
    print("🎉 वीडियो तैयार है! GitHub Artifacts से डाउनलोड करें।")

if __name__ == "__main__":
    asyncio.run(main())
