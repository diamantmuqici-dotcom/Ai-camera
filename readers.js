"use strict";

window.ReaderTools = Object.freeze({
  normalizeText(value){return String(value||"").replace(/\s+/g," ").trim()},
  looksLikePlate(value){return /^[A-Z0-9][A-Z0-9 -]{1,10}$/i.test(this.normalizeText(value))},
  async toBlob(canvas,quality=.92){return new Promise(resolve=>canvas.toBlob(resolve,"image/jpeg",quality))}
});
