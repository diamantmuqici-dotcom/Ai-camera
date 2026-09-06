"use strict";

export function isMobile() {
  return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

export function cameraConstraints({deviceId = "", facing = "environment", width = 1920, height = 1080, fps = 30} = {}) {
  const video = deviceId
    ? {deviceId: {exact: deviceId}}
    : {facingMode: {ideal: facing}};
  video.width = {ideal: width};
  video.height = {ideal: height};
  video.frameRate = {ideal: fps};
  return {video, audio: false};
}

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}
