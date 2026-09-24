import { useCallback, useEffect, useRef, useState } from "react";

export function useAudioPlayer(src, startAt = 0) {
  const audioRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(startAt);
  const [duration, setDuration] = useState(0);
  const [volume, setVolumeState] = useState(0.76);

  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(startAt);
    setDuration(0);
    if (!src) return undefined;
    const audio = new Audio(src);
    audio.preload = "metadata";
    audio.volume = volume;
    audioRef.current = audio;

    const syncTime = () => setCurrentTime(audio.currentTime || 0);
    const syncDuration = () => {
      const nextDuration = Number.isFinite(audio.duration) ? audio.duration : 0;
      setDuration(nextDuration);
      if (audio.currentTime === 0 && startAt > 0 && nextDuration > startAt) {
        audio.currentTime = startAt;
        setCurrentTime(startAt);
      }
    };
    const syncEnded = () => setIsPlaying(false);

    audio.addEventListener("timeupdate", syncTime);
    audio.addEventListener("loadedmetadata", syncDuration);
    audio.addEventListener("durationchange", syncDuration);
    audio.addEventListener("ended", syncEnded);

    return () => {
      audio.pause();
      audio.removeEventListener("timeupdate", syncTime);
      audio.removeEventListener("loadedmetadata", syncDuration);
      audio.removeEventListener("durationchange", syncDuration);
      audio.removeEventListener("ended", syncEnded);
      audioContextRef.current?.close();
      audioContextRef.current = null;
      analyserRef.current = null;
      audioRef.current = null;
    };
  }, [src, startAt]);

  const ensureAnalyser = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return null;

    if (!audioContextRef.current) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return null;
      const context = new AudioContext();
      const source = context.createMediaElementSource(audio);
      const analyser = context.createAnalyser();
      analyser.fftSize = 128;
      analyser.smoothingTimeConstant = 0.82;
      source.connect(analyser);
      analyser.connect(context.destination);
      audioContextRef.current = context;
      analyserRef.current = analyser;
    }

    if (audioContextRef.current.state === "suspended") {
      await audioContextRef.current.resume();
    }
    return analyserRef.current;
  }, []);

  const toggle = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      await ensureAnalyser();
      await audio.play();
      setIsPlaying(true);
    } else {
      audio.pause();
      setIsPlaying(false);
    }
  }, [ensureAnalyser]);

  const seek = useCallback((time) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = Math.max(0, Math.min(time, audio.duration || 0));
    setCurrentTime(audio.currentTime);
  }, []);

  const skip = useCallback((seconds) => {
    const audio = audioRef.current;
    seek((audio?.currentTime || 0) + seconds);
  }, [seek]);

  const setVolume = useCallback((nextVolume) => {
    const value = Math.max(0, Math.min(1, nextVolume));
    if (audioRef.current) audioRef.current.volume = value;
    setVolumeState(value);
  }, []);

  return {
    analyserRef,
    currentTime,
    duration,
    isPlaying,
    seek,
    setVolume,
    skip,
    toggle,
    volume,
  };
}
