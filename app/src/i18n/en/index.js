import common from "./common.js";
import image from "./image.js";
import music from "./music.js";
import settings from "./settings.js";
import speech from "./speech.js";
import video from "./video.js";

export default { ...common, ...music, ...image, ...video, ...speech, ...settings };
