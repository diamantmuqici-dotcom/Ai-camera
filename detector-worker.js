/* Existing detector worker: scheduler + frame backpressure + optional native CV heuristics. */
"use strict";

let busy = false;
let lastRequest = 0;
let frameCounter = 0;

function luminance(r, g, b) {
  return (r * 77 + g * 150 + b * 29) >> 8;
}

function estimateRegion(image, width, height) {
  // Lightweight scene/edge proposal only. It is NOT an ML detector.
  const data = image?.data;
  if (!data || width < 8 || height < 8) return null;

  let sum = 0, edges = 0, samples = 0;
  const step = Math.max(2, Math.floor(Math.min(width, height) / 48));

  for (let y = step; y < height - step; y += step) {
    for (let x = step; x < width - step; x += step) {
      const i = (y * width + x) * 4;
      const l = luminance(data[i], data[i + 1], data[i + 2]);
      const ir = i + step * 4;
      const id = i + step * width * 4;
      const lr = luminance(data[ir], data[ir + 1], data[ir + 2]);
      const ld = luminance(data[id], data[id + 1], data[id + 2]);
      sum += l;
      edges += Math.abs(l - lr) + Math.abs(l - ld);
      samples++;
    }
  }

  if (!samples) return null;
  return {
    x: 0, y: 0, width: 1, height: 1,
    score: Math.min(1, edges / samples / 80),
    meanLuma: sum / samples
  };
}

self.onmessage = async event => {
  const message = event.data || {};

  if (message.type === "reset") {
    busy = false;
    frameCounter = 0;
    self.postMessage({ type: "reset-done" });
    return;
  }

  if (message.type === "load-model") {
    // Keep the existing no-bundled-model contract honest.
    self.postMessage({
      type: "model-ready",
      name: message.name || "native-heuristics",
      available: false,
      message: "No external ML model is bundled; native lightweight analysis remains available."
    });
    return;
  }

  if (message.type !== "detect" || busy) {
    if (message.type === "detect" && busy) {
      self.postMessage({ type: "dropped", id: message.id, reason: "backpressure" });
    }
    return;
  }

  busy = true;
  lastRequest = performance.now();
  const id = message.id ?? ++frameCounter;

  try {
    const result = estimateRegion(message.image, message.width, message.height);
    self.postMessage({
      type: "detections",
      id,
      detections: result ? [{ ...result, type: "scene-region", source: "heuristic" }] : [],
      elapsedMs: performance.now() - lastRequest,
      modelAvailable: false
    });
  } finally {
    busy = false;
  }
};
