import { FilmSlate, ImageSquare, MusicNotes, Waveform } from "@phosphor-icons/react";

// The four creative modules, named by what the user gets out of them.
export const MODULES = [
  {
    id: "image",
    label: "图片",
    icon: ImageSquare,
    title: "画一张图，或改一张图",
    summary: "一句话生成图片，中英文字也能写对；上传图片后用一句话描述想怎么改。",
  },
  {
    id: "video",
    label: "视频",
    icon: FilmSlate,
    title: "让画面动起来",
    summary: "一句话或一张图，生成 5 秒带声音的短视频。",
  },
  {
    id: "music",
    label: "音乐",
    icon: MusicNotes,
    title: "写一首歌",
    summary: "一句话、自己的歌词或纯音乐，生成完整歌曲。",
  },
  {
    id: "speech",
    label: "语音",
    icon: Waveform,
    title: "声音和文字互转",
    summary: "录音转文字和字幕，文字转语音，用几秒录音克隆声音。",
  },
];

export const MUSIC_MODES = [
  {
    id: "prompt",
    label: "一句话",
    inputLabel: "描述你想要的歌",
    placeholder: "例如：一首雨夜城市感的华语流行歌，温柔女声，副歌有记忆点",
    defaultValue: "一首雨夜城市感的华语流行歌，温柔女声，副歌有记忆点",
    maxLength: 200,
  },
  {
    id: "lyrics",
    label: "我的歌词",
    inputLabel: "输入你的歌词",
    placeholder: "可用 [主歌]、[副歌]、[桥段] 标出段落",
    defaultValue:
      "[主歌]\n城市把雨写进霓虹\n我把你的名字藏进风中\n\n[副歌]\n雨落之后 我还在等候\n等一句迟来的温柔",
    maxLength: 2000,
  },
  {
    id: "instrumental",
    label: "纯音乐",
    inputLabel: "描述你想要的氛围",
    placeholder: "例如：雨夜城市，电钢琴与柔和合成器，缓慢推进，电影感",
    defaultValue: "雨夜城市氛围，电钢琴与柔和合成器，缓慢推进，电影感",
    maxLength: 200,
  },
];

export const MUSIC_STYLES = ["华语流行", "摇滚", "民谣", "电子", "古风", "温柔", "欢快", "伤感", "治愈", "女声", "男声", "钢琴", "电影感"];

export const VISUAL_STYLES = [
  { id: "flow", name: "流光", src: "/assets/visual-flow-city.png" },
  { id: "spectrum", name: "频谱", src: "/assets/visual-spectrum.png" },
  { id: "nebula", name: "星云", src: "/assets/visual-nebula.png" },
];

export const TIER_LABEL = { 16: "16 GB 级", 32: "24–32 GB 级", 64: "48 GB 以上" };
export const TIER_NEED = { 16: "16 GB", 32: "24 GB", 64: "48 GB" };
