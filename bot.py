# =======================================================================
# 🟢 EASY CUSTOMIZATION BLOCK 🟢
# =======================================================================

BGM_FILE = "./bgm.mp3" 
BGM_VOLUME = 0.25      

VOICE_QUESTION = "hi-IN-MadhurNeural" 
VOICE_ANSWER = "hi-IN-SwaraNeural"    
VOICE_SPEED = "+0%"                   

TIMER_SECONDS = 5.0  

# 👻 WATERMARK SETTINGS
CHANNEL_WATERMARK = "Zoom Mind" 

THUMB_TEMPLATE = "./thumb_template.jpg" 
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

OUTPUT_FOLDER = "./output"
TEMP_FOLDER = "./temp"
JSON_FILE_PATH = "./questions.json"
BG_FOLDER = "./bgs" 

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(BG_FOLDER, exist_ok=True)

# 🌟 ADVANCED TEXT GENERATOR: 2 शब्दों को लाल करने वाला लॉजिक
def get_multicolor_hindi_image_clip(text, filename, font_size, default_color, highlight_color=(200, 0, 0), width_limit=45, highlight=False):
    font = ImageFont.truetype(HINDI_FONT, font_size)
    words = text.split()
    
    highlight_indices = []
    if highlight and len(words) > 3:
        # सिर्फ बड़े शब्दों को लाल करेगा (ताकि 'है', 'का' जैसे शब्द लाल न हों)
        valid_indices = [i for i, w in enumerate(words) if len(w) > 2]
        if len(valid_indices) >= 2:
            highlight_indices = random.sample(valid_indices, 2)
        elif valid_indices:
            highlight_indices = valid_indices

    lines = []
    current_line = []; current_length = 0
    for i, word in enumerate(words):
        if current_length + len(word) > width_limit and current_line:
            lines.append(current_line)
            current_line = [(word, i)]
            current_length = len(word) + 1
        else:
            current_line.append((word, i))
            current_length += len(word) + 1
    if current_line: lines.append(current_line)
        
    dummy_img = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    
    max_w = 0; y_text = 0
    line_heights = []; line_widths = []
    
    for line in lines:
        line_str = " ".join([w[0] for w in line])
        bbox = draw.textbbox((0, 0), line_str, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        max_w = max(max_w, lw)
        line_widths.append(lw)
        line_heights.append(lh)
        y_text += lh + 15
        
    img = Image.new('RGBA', (max_w + 40, y_text + 40), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    y_pos = 10
    for idx, line in enumerate(lines):
        x_pos = ((max_w + 40) - line_widths[idx]) / 2 # Center Align
        for word, orig_i in line:
            color = highlight_color if orig_i in highlight_indices else default_color
            draw.text((x_pos, y_pos), word, font=font, fill=color)
            x_pos += draw.textlength(word + " ", font=font)
        y_pos += line_heights[idx] + 15
        
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

async def prepare_test_questions():
    print(f"🎯 Test Mode: सिर्फ 4 सवाल ले रहा हूँ...")
    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f: all_q = json.load(f)
    if len(all_q) < 4:
        print("❌ Error: JSON में 4 सवाल भी नहीं हैं!")
        sys.exit(1)
    
    used_quizzes = all_q[:4]
    for i, quiz in enumerate(used_quizzes):
        text_a = quiz['opt_a'].replace("A)", "").replace("A.", "").strip()
        text_b = quiz['opt_b'].replace("B)", "").replace("B.", "").strip()
        text_c = quiz['opt_c'].replace("C)", "").replace("C.", "").strip()
        correct_key = quiz['correct_key']
        correct_ans_text = text_a if correct_key == 'A' else text_b if correct_key == 'B' else text_c

        speech_q_opts = f"{quiz['question']}... ऑप्शन ए, {text_a}... ऑप्शन बी, {text_b}... ऑप्शन सी, {text_c}"
        speech_ans = f"सही जवाब है, {correct_ans_text}"

        quiz['q_audio'] = await generate_voice(speech_q_opts, f"q_{i}.mp3", "male")
        quiz['a_audio'] = await generate_voice(speech_ans, f"a_{i}.mp3", "female")

    last_q = used_quizzes[-1]
    last_q['a_audio'] = await generate_voice("इसका जवाब आप कमेंट्स में बताइए!", f"a_last.mp3", "female")
    return used_quizzes

async def make_video_chunk(quiz, index, total_q, bg_image_path):
    print(f"\n🎬 रेंडर: सवाल {index}/{total_q}")
    
    # 🔠 Options With A, B, C
    text_a = "A) " + quiz['opt_a'].replace("A)", "").replace("A.", "").strip()
    text_b = "B) " + quiz['opt_b'].replace("B)", "").replace("B.", "").strip()
    text_c = "C) " + quiz['opt_c'].replace("C)", "").replace("C.", "").strip()
    correct_key = quiz['correct_key']
    is_last = (index == total_q)

    aud_q_opts = AudioFileClip(quiz['q_audio']).volumex(1.5)
    aud_ans = AudioFileClip(quiz['a_audio']).volumex(1.5)

    t = 0.0; s_q_opts = t; t += aud_q_opts.duration + 0.5
    s_timer = t; t += TIMER_SECONDS
    s_ans = t; t += aud_ans.duration + 1.5; total = t

    # 🖼️ Background Logic
    if bg_image_path:
        bg = ImageClip(bg_image_path).resize((1920, 1080)).set_duration(total).set_fps(24)
    else:
        bg = ColorClip(size=(1920, 1080), color=(240, 240, 240)).set_duration(total).set_fps(24)
    
    watermark = TextClip(CHANNEL_WATERMARK, fontsize=120, color='black', font='Arial-Bold').set_opacity(0.04).set_position('center').set_duration(total)

    lvl_bg = ColorClip(size=(350, 80), color=(10, 30, 20)).set_position((50, 40)).set_duration(total)
    lvl_clip = TextClip("LEVEL: EASY", fontsize=45, color='yellow', font='Arial-Bold').set_position((80, 55)).set_duration(total)
    
    prog_bg = ColorClip(size=(300, 80), color=(10, 20, 40)).set_position((1550, 40)).set_duration(total)
    prog_clip = TextClip(f"Q: {index}/{total_q}", fontsize=45, color='white', font='Arial-Bold').set_position((1600, 55)).set_duration(total)

    # 🔠 Question (BLACK with RED HIGHLIGHTS)
    q_text = f"प्रश्न {index}: {quiz['question']}"
    q_color = (0, 0, 0) # Black
    red_highlight = (200, 0, 0) # Red
    q_clip = get_multicolor_hindi_image_clip(q_text, f"img_q_{index}.png", 95, q_color, highlight_color=red_highlight, width_limit=45, highlight=True).set_position(('center', 180)).set_start(0).set_duration(total)
    
    divider = ColorClip(size=(1200, 4), color=(100, 50, 20)).set_position(('center', 420)).set_duration(total)

    # 🔠 Options (DARK BLUE) with A, B, C
    opt_color = (0, 0, 51) 
    y_opts = 480
    
    opt_a_white = get_multicolor_hindi_image_clip(text_a, f"img_a_{index}.png", 80, opt_color, width_limit=50)
    opt_b_white = get_multicolor_hindi_image_clip(text_b, f"img_b_{index}.png", 80, opt_color, width_limit=50)
    opt_c_white = get_multicolor_hindi_image_clip(text_c, f"img_c_{index}.png", 80, opt_color, width_limit=50)

    ans_color = (0, 100, 0) # Dark Green
    
    if correct_key == 'A':
        opt_a_clip = opt_a_white.set_position(('center', y_opts)).set_start(0).set_end(s_ans)
        ans_clip = get_multicolor_hindi_image_clip(text_a, f"ans_{index}.png", 80, ans_color, width_limit=50).set_position(('center', y_opts)).set_start(s_ans).set_duration(total - s_ans)
        opt_b_clip = opt_b_white.set_position(('center', y_opts+130)).set_duration(total)
        opt_c_clip = opt_c_white.set_position(('center', y_opts+260)).set_duration(total)
    elif correct_key == 'B':
        opt_a_clip = opt_a_white.set_position(('center', y_opts)).set_duration(total)
        opt_b_clip = opt_b_white.set_position(('center', y_opts+130)).set_start(0).set_end(s_ans)
        ans_clip = get_multicolor_hindi_image_clip(text_b, f"ans_{index}.png", 80, ans_color, width_limit=50).set_position(('center', y_opts+130)).set_start(s_ans).set_duration(total - s_ans)
        opt_c_clip = opt_c_white.set_position(('center', y_opts+260)).set_duration(total)
    else:
        opt_a_clip = opt_a_white.set_position(('center', y_opts)).set_duration(total)
        opt_b_clip = opt_b_white.set_position(('center', y_opts+130)).set_duration(total)
        opt_c_clip = opt_c_white.set_position(('center', y_opts+260)).set_start(0).set_end(s_ans)
        ans_clip = get_multicolor_hindi_image_clip(text_c, f"ans_{index}.png", 80, ans_color, width_limit=50).set_position(('center', y_opts+260)).set_start(s_ans).set_duration(total - s_ans)

    tick = make_tick_sfx(TIMER_SECONDS).set_start(s_timer)
    timer_vis = []
    for i in range(int(TIMER_SECONDS)):
        t_val = int(TIMER_SECONDS)-i
        t_color = 'red' if t_val <= 3 else 'blue'
        timer_vis.append(TextClip(f"0{t_val}" if t_val<10 else f"{t_val}", fontsize=140, color=t_color, font='Arial-Bold').set_position(('center', 850)).set_start(s_timer+i).set_duration(1.0))

    final_audio = CompositeAudioClip([aud_q_opts.set_start(s_q_opts), tick, aud_ans.set_start(s_ans)])
    
    visuals = [bg, watermark, lvl_bg, lvl_clip, prog_bg, prog_clip, divider, q_clip, opt_a_clip, opt_b_clip, opt_c_clip] + timer_vis
    
    if not is_last: visuals.append(ans_clip)
    
    if is_last:
        suspense = get_multicolor_hindi_image_clip("- कमेंट में अपना जवाब दें! -", f"img_susp_{index}.png", 85, (200, 0, 0)).set_position(('center', 850)).set_start(s_ans).set_duration(total - s_ans)
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
    
    os.system(f"ffmpeg -f concat -safe 0 -i {concat_txt} -c:v copy -c:a aac -b:a 192k {merged_no_bgm} -y")
    
    if os.path.exists(BGM_FILE) and os.path.exists(merged_no_bgm):
        bgm_abs = os.path.abspath(BGM_FILE)
        cmd = f'ffmpeg -i {merged_no_bgm} -stream_loop -1 -i {bgm_abs} -filter_complex "[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a0];[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume={BGM_VOLUME}[a1];[a0][a1]amix=inputs=2:duration=first[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac {final_output} -y'
        os.system(cmd)
    else: 
        if os.path.exists(merged_no_bgm): os.rename(merged_no_bgm, final_output)
    return final_output

async def main():
    print(f"🤖 Test Mode: 2 सेकंड इंतज़ार...")
    time.sleep(2) 
    
    quizzes = await prepare_test_questions()
    total_q = len(quizzes)
    
    bg_files = [f for f in os.listdir(BG_FOLDER) if f.endswith(('.png', '.jpg', '.jpeg'))]
    if bg_files:
        selected_bg = os.path.join(BG_FOLDER, random.choice(bg_files))
        print(f"🖼️ बैकग्राउंड सेलेक्ट किया गया: {os.path.basename(selected_bg)}")
    else:
        selected_bg = None
        print("⚠️ 'bgs' फोल्डर खाली है! सफ़ेद बैकग्राउंड यूज़ कर रहा हूँ।")
    
    chunk_files = []
    for i, quiz in enumerate(quizzes):
        chunk_path = await make_video_chunk(quiz, i+1, total_q, selected_bg)
        chunk_files.append(chunk_path)
        
    final_video = merge_videos_and_add_bgm(chunk_files)
    print("🎉 वीडियो तैयार है! GitHub Artifacts से डाउनलोड करें।")

if __name__ == "__main__":
    asyncio.run(main())
