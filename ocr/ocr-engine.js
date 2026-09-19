"use strict";
class OcrEngine {
  constructor(){this.worker=null;this.loading=null}
  async ensure(){if(this.worker)return this.worker;if(this.loading)return this.loading;this.loading=import("https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.esm.min.js").then(m=>m).finally(()=>{this.loading=null});this.worker=await this.loading;return this.worker}
}
window.OcrEngine=OcrEngine;