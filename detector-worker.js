/* Lightweight worker bridge. Add a compatible model under models/ to enable ML detection. */
"use strict";

let detector = null;

self.onmessage = async event => {
  const message = event.data || {};
  if (message.type === "load-model") {
    detector = {name: message.name || "unconfigured"};
    self.postMessage({type: "model-ready", name: detector.name, available: false,
      message: "No model is bundled. Add a compatible model under models/."});
    return;
  }
  if (message.type === "detect") {
    self.postMessage({type: "detections", id: message.id, detections: [],
      message: detector ? "Model bridge ready; no model loaded." : "Load a model first."});
  }
};
