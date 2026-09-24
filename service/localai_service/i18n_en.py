"""English versions of the service's user-facing messages, keyed by the Chinese source."""

EN: dict[str, str] = {
    # jobs.py: job states
    "排队中": "Queued",
    "正在准备": "Preparing",
    "完成": "Done",
    "已取消": "Cancelled",
    "生成失败": "Failed",
    "本地引擎出错：{error}": "Local engine error: {error}",

    # uploads.py
    "找不到输入文件，请重新选择": "Input file not found. Please choose it again.",

    # server.py: API errors
    "不支持打开这个链接": "This link can't be opened.",
    "模型不存在": "Model not found",
    "有任务正在进行，请完成后再删除模型": "A job is running. Wait for it to finish before deleting models.",
    "未知的任务类型": "Unknown job type",
    "任务不存在": "Job not found",
    "作品不存在": "Item not found",
    "任务仍在进行，请先取消": "This job is still running. Cancel it first.",
    "文件不存在": "File not found",
    "没有收到文件": "No file received",
    "不支持这种文件格式": "Unsupported file format",
    "文件太大（上限 2 GB）": "File too large (2 GB max)",
    "图片文件已损坏或无法识别": "The image is damaged or not recognized.",

    # server.py: Kokoro voices (speech.KOKORO_VOICES)
    "晓晓 · 女声": "Xiaoxiao · Female",
    "晓伊 · 女声": "Xiaoyi · Female",
    "晓北 · 女声": "Xiaobei · Female",
    "晓妮 · 女声": "Xiaoni · Female",
    "云希 · 男声": "Yunxi · Male",
    "云健 · 男声": "Yunjian · Male",
    "云扬 · 男声": "Yunyang · Male",
    "云夏 · 男声": "Yunxia · Male",

    # downloads.py
    "这个模型需要先在 Hugging Face 上同意许可证，并在设置里填写访问令牌":
        "This model requires accepting its license on Hugging Face and adding an access token in Settings.",
    "无法获取模型文件列表（{status}）": "Couldn't get the model's file list ({status})",
    "下载服务器返回 {status}": "Download server returned {status}",
    "{name} 大小不对，请重试": "{name} has the wrong size. Please try again.",
    "{name} 校验失败，文件已删除，请重试": "{name} failed verification and was deleted. Please try again.",
    "磁盘空间不足：需要约 {size} GB": "Not enough disk space: about {size} GB needed",
    "下载失败：{error}": "Download failed: {error}",

    # catalog.py: model names, licenses, license notes
    "写作助手（歌词与提示词）": "Writing Assistant (lyrics and prompts)",
    "YuE2 3B（中文精唱）": "YuE2 3B (Chinese vocals)",
    "SenseVoice Small（极速识别）": "SenseVoice Small (fastest)",
    "Kokoro 82M（快速配音）": "Kokoro 82M (fast voiceover)",
    "LTX-2.5 Distilled（实验）": "LTX-2.5 Distilled (experimental)",
    "CC BY-NC 4.0（仅限非商用）": "CC BY-NC 4.0 (non-commercial only)",
    "YuE2 采用 CC BY-NC 4.0：仅限非商业用途，生成的歌曲请勿用于商业目的。":
        "YuE2 is licensed under CC BY-NC 4.0: non-commercial use only. Do not use generated songs commercially.",
    "FLUX.2 klein 9B 采用 FLUX 非商用许可证：仅限个人和非商业用途。":
        "FLUX.2 klein 9B uses the FLUX Non-Commercial License: personal and non-commercial use only.",
    "LTX-2.x 社区许可证：个人和非商用免费；年收入超过 1000 万美元的公司商用需另行授权；须遵守其使用政策。":
        "LTX-2.x Community License: free for personal and non-commercial use; companies with over $10M annual "
        "revenue need a separate commercial license; its acceptable use policy applies.",
    "LTX-2.x 社区许可证：个人和非商用免费；年收入超过 1000 万美元的公司商用需另行授权；须遵守其使用政策。"
    "文本编码器和解码器来自 Lightricks 官方仓库：请先登录 Hugging Face 同意许可证，并在设置里填写访问令牌。":
        "LTX-2.x Community License: free for personal and non-commercial use; companies with over $10M annual "
        "revenue need a separate commercial license; its acceptable use policy applies. The text encoder and "
        "decoders come from the official Lightricks repository: sign in to Hugging Face, accept the license, "
        "and add an access token in Settings.",

    # catalog.py: features
    "写歌 · 标准": "Song · Standard",
    "写歌 · 中文精唱": "Song · Chinese vocals",
    "一句话写词": "Lyrics from a sentence",
    "文字生成图片": "Text to image",
    "图片编辑": "Image editing",
    "文字 / 图片生成视频": "Text / image to video",
    "语音转文字": "Speech to text",
    "文字转语音 / 声音克隆": "Text to speech / voice cloning",

    # shared progress labels (image, video, sdcpp)
    "正在加载模型": "Loading model",
    "正在绘制": "Drawing",
    "正在解码": "Decoding",

    # engines/image.py
    "请先描述你想要的画面": "Describe the image you want first.",
    "图片模型未安装，请在设置里下载": "Image model not installed. Download it in Settings.",
    "生成完成，但没有找到图片": "Generation finished, but no image was found.",
    "请描述想怎么修改这张图": "Describe how you want to change this image.",
    "图片编辑模型未安装，请在设置里下载": "Image editing model not installed. Download it in Settings.",
    "编辑 · {text}": "Edit · {text}",
    "编辑完成，但没有找到图片": "Editing finished, but no image was found.",

    # engines/video.py
    "正在理解描述": "Reading the prompt",
    "正在加载视频模型": "Loading video model",
    "正在生成画面与声音": "Generating video and sound",
    "正在解码视频": "Decoding video",
    "正在合成视频与声音": "Muxing video and sound",
    "请描述想看到的画面和动作": "Describe the scene and motion you want to see.",
    "视频生成需要 24 GB 以上内存，这台电脑暂不支持": "Video generation needs 24 GB of memory or more. This computer isn't supported yet.",
    "视频模型未安装，请在设置里下载": "Video model not installed. Download it in Settings.",
    "正在补充镜头描述": "Expanding the shot description",
    "动起来 · {text}": "Animate · {text}",
    "生成完成，但没有找到视频": "Generation finished, but no video was found.",

    # engines/llm.py
    "写作助手模型未安装，请在设置里下载后再试，或切换到“我的歌词”模式":
        "Writing assistant model not installed. Download it in Settings, or switch to “My lyrics” mode.",
    "歌词生成失败，请换个描述再试一次": "Couldn't write lyrics. Try a different description.",

    # engines/music.py
    "本地新作": "New song",
    "请先输入歌曲描述或歌词": "Enter a song description or lyrics first.",
    "正在写歌词": "Writing lyrics",
    "纯音乐 · {text}": "Instrumental · {text}",
    "音乐模型未安装，请在设置里下载": "Music model not installed. Download it in Settings.",
    "正在规划旋律与结构": "Planning melody and structure",
    "正在生成演唱与编曲": "Generating vocals and arrangement",
    "正在完成混音": "Finishing the mix",
    "生成完成，但没有找到音频文件": "Generation finished, but no audio file was found.",
    "正在完成音频文件": "Finishing audio file",
    "请先生成一首可用的歌曲": "Generate a song first.",
    "歌曲": "Song",
    "{title} · 动效视频": "{title} · Visualizer video",

    # engines/media.py
    "正在渲染声音动效画面": "Rendering visualizer",

    # engines/speech.py
    "语音识别模型未安装，请在设置里下载": "Speech recognition model not installed. Download it in Settings.",
    "{name} · 文字稿": "{name} · Transcript",
    "正在读取音频": "Reading audio",
    "没有检测到有效的音频": "No usable audio found.",
    "正在切分语句": "Splitting into sentences",
    "没有检测到说话的声音": "No speech detected.",
    "正在识别文字": "Transcribing",
    "没有识别出文字": "No text was recognized.",
    "快速配音模型未安装，请在设置里下载": "Fast voiceover model not installed. Download it in Settings.",
    "请输入要朗读的文字": "Enter the text to read aloud.",
    "一次最多朗读 5000 字，请分段生成": "Up to 5,000 characters at a time. Split the text into parts.",
    "配音 · {text}": "Voiceover · {text}",
    "正在朗读": "Reading aloud",
    "配音模型未安装，请在设置里下载": "Voiceover model not installed. Download it in Settings.",
    "正在准备音色": "Preparing voice",
    "正在分析参考声音": "Analyzing reference voice",
    "参考录音太短，请提供 5 到 20 秒的清晰人声": "Reference recording is too short. Provide 5 to 20 seconds of clear speech.",
    "生成完成，但没有找到音频": "Generation finished, but no audio was found.",

    # Model picker (catalog.TASKS)
    "画质细腻，中英文字写得最准": "Fine detail; renders Chinese and English text most accurately",
    "速度最快，适合快速出草图，写字较弱": "Fastest, great for quick drafts; weaker at text",
    "质感和细节更好，适合人像和写实场景": "Richer texture and detail; good for portraits and realistic scenes",
    "改图最准，原图细节保留最好": "Most accurate edits; keeps the original details best",
    "速度快，16 GB 电脑也能用": "Fast; works on 16 GB computers",
    "文字或图片生成带声音的短视频，画面稳定": "Short videos with sound from text or an image; stable motion",
    "速度快、风格多，可以设定时长，中英文都能唱": "Fast, many styles, adjustable length; sings Chinese and English",
    "中文咬字最准，时长跟随歌词（仅限非商用）": "Clearest Chinese diction; length follows the lyrics (non-commercial only)",
    "准确又快，支持普通话、英语等多种语言": "Accurate and fast; Mandarin, English and many more languages",
    "方言和口音识别更稳，速度稍慢": "Better with dialects and accents; a bit slower",
    "速度极快，适合很长的录音": "Very fast; best for long recordings",
    "速度最快，中文预设音色；遇到英文自动换用 Qwen3-TTS": "Fastest, Chinese preset voices; switches to Qwen3-TTS for English words",
    "更自然，支持中英混读和声音克隆": "More natural; mixed Chinese and English, voice cloning",
    "约 40 秒": "about 40 s",
    "约 15 秒": "about 15 s",
    "约 20 秒": "about 20 s",
    "约 1 分钟": "about 1 min",
    "5 秒视频约 2 分钟": "about 2 min for 5 s of video",
    "1 分钟歌曲约 40 秒": "about 40 s for a 1-minute song",
    "1 小时录音约 3 分钟": "about 3 min per hour of audio",
    "1 小时录音约 5 分钟": "about 5 min per hour of audio",
    "1 小时录音约 1 分钟": "about 1 min per hour of audio",
    "几秒": "a few seconds",
    "十几秒": "10–20 s",
    # Prompt polishing
    "先写一句想法，再让写作助手润色": "Write an idea first, then let the writing assistant polish it.",
    "正在润色": "Polishing",
    "润色失败，请重试": "Polishing failed. Please try again.",
}
