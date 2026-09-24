// Example prompts shown on each page before anything is selected. Text is the Chinese
// source (translated with t() when shown and when run); thumbnails were generated with the
// app's own models from these prompts.
const img = (name) => `/examples/${name}.webp`;

export const IMAGE_EXAMPLES = [
  { id: "poster", title: "咖啡店海报", prompt: "一张秋日咖啡店海报，标题写着“秋日限定”，一杯南瓜拿铁，暖色调", styles: ["海报"], aspect: "3:4", thumb: img("img-poster"), focus: "top" },
  { id: "ink", title: "水墨山水", prompt: "云雾缭绕的山间小屋，远处有瀑布", styles: ["水墨"], aspect: "4:3", thumb: img("img-ink") },
  { id: "cat", title: "午后的猫", prompt: "窗台上晒太阳的橘猫，柔和的午后光线", styles: ["写实照片"], aspect: "1:1", thumb: img("img-cat") },
  { id: "city", title: "雨夜城市", prompt: "雨夜的未来城市街道，霓虹灯倒映在积水里", styles: ["电影感"], aspect: "16:9", thumb: img("img-city") },
  { id: "robot", title: "浇花机器人", prompt: "一个可爱的小机器人在阳台上给花浇水", styles: ["3D"], aspect: "1:1", thumb: img("img-robot") },
  { id: "anime", title: "樱花少女", prompt: "樱花树下的少女，微风吹起花瓣", styles: ["动漫"], aspect: "3:4", thumb: img("img-anime"), focus: "top" },
];

export const VIDEO_EXAMPLES = [
  { id: "waves", title: "海边日落", prompt: "海浪拍打礁石，夕阳下的海鸥飞过", thumb: img("vid-waves"), video: "/examples/vid-waves.mp4" },
  { id: "cat", title: "窗台上的猫", prompt: "一只橘猫在窗台上伸懒腰，窗外下着小雨", thumb: img("vid-cat"), video: "/examples/vid-cat.mp4" },
  { id: "city", title: "雨夜街头", prompt: "城市街道的雨夜，霓虹灯倒映在积水里，行人撑伞走过", thumb: img("vid-city"), video: "/examples/vid-city.mp4" },
  { id: "balloon", title: "峡谷热气球", prompt: "日出时热气球缓缓飞过峡谷，镜头慢慢推进", thumb: img("vid-balloon"), video: "/examples/vid-balloon.mp4" },
];

export const MUSIC_EXAMPLES = [
  { id: "summer", title: "夏日海边", prompt: "一首关于夏天海边的轻快华语流行歌，清爽男声，副歌朗朗上口", mode: "prompt", styles: ["华语流行", "欢快", "男声"], thumb: img("cover-summer") },
  { id: "night", title: "雨夜城市", prompt: "一首雨夜城市感的抒情歌，温柔女声，钢琴和弦乐", mode: "prompt", styles: ["华语流行", "温柔", "女声", "钢琴"], thumb: img("cover-night") },
  { id: "guofeng", title: "月下竹林", prompt: "一首中国风古风歌曲，古筝与笛子，意境悠远", mode: "prompt", styles: ["古风", "治愈"], thumb: img("cover-guofeng") },
  { id: "lofi", title: "雨天学习", prompt: "雨天书桌旁的 lo-fi 学习音乐，电钢琴与轻柔鼓点，放松专注", mode: "instrumental", styles: [], thumb: img("cover-lofi") },
];

export const TTS_EXAMPLES = [
  { id: "news", title: "新闻播报", prompt: "今天是个好天气，全国大部分地区晴到多云，气温适宜，适合外出活动。", voice: "zm_yunxi" },
  { id: "story", title: "睡前故事", prompt: "从前，森林里住着一只小兔子，它每天晚上都会抬头数星星，数着数着就睡着了。", voice: "zf_xiaoxiao" },
  { id: "product", title: "中英混读", prompt: "TopLocal Studio 可以在你的电脑上生成图片、视频、音乐和语音，完全离线运行。", voice: "zf_xiaoyi" },
];

export const ASR_EXAMPLES = [
  { id: "sample", title: "示例录音", prompt: "一段 15 秒的普通话介绍，看看转写效果和字幕", audio: "/examples/sample-speech.m4a" },
  { id: "sample-en", title: "英文录音", prompt: "一段英文介绍，自动识别语言并生成字幕", audio: "/examples/sample-speech-en.m4a" },
];
