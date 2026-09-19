"use strict";

/* Shared camera utilities. No external dependencies. */
export function isMobile() {
  return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

export function clamp(value, min, max) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : min;
}

export function lerp(a, b, t) {
  return a + (b - a) * clamp(t, 0, 1);
}

export function cameraConstraints({
  deviceId = "",
  facing = "environment",
  width = 1920,
  height = 1080,
  fps = 30,
  aspectRatio
} = {}) {
  const video = deviceId
    ? { deviceId: { exact: deviceId } }
    : { facingMode: { ideal: facing } };

  video.width = { ideal: width };
  video.height = { ideal: height };
  video.frameRate = { ideal: fps };

  if (Number.isFinite(aspectRatio) && aspectRatio > 0) {
    video.aspectRatio = { ideal: aspectRatio };
  }

  return { video, audio: false };
}

export function capabilityRange(capabilities, key) {
  const c = capabilities?.[key];
  if (!c || typeof c !== "object") return null;
  if (!Number.isFinite(c.min) || !Number.isFinite(c.max)) return null;
  return { min: c.min, max: c.max, step: Number.isFinite(c.step) ? c.step : undefined };
}

export function supportsImageCapture() {
  return typeof window.ImageCapture === "function";
}

export function supportsOffscreenCanvas() {
  return typeof window.OffscreenCanvas === "function";
}

export function supportsImageBitmap() {
  return typeof window.createImageBitmap === "function";
}
