"use strict";

window.ReaderTools = Object.freeze({
  normalizeText(value) {
    return String(value ?? "")
      .replace(/[\u0000-\u001F\u007F]+/g," ")
      .replace(/\s+/g," ")
      .trim();
  },

  cleanOCR(value) {
    return this.normalizeText(value)
      .replace(/[|]/g,"I")
      .replace(/\s+([,.!?])/g,"$1");
  },

  looksLikePlate(value) {
    const text=this.cleanOCR(value).toUpperCase().replace(/[^A-Z0-9 -]/g,"");
    const compact=text.replace(/[ -]/g,"");
    return compact.length>=2 && compact.length<=12 && /[A-Z]/.test(compact) && /\d/.test(compact);
  },

  plateScore(value) {
    const text=this.cleanOCR(value).toUpperCase().replace(/[^A-Z0-9]/g,"");
    if(!text) return 0;
    let score=0;
    if(text.length>=5&&text.length<=9) score+=.35;
    if(/[A-Z]/.test(text)) score+=.25;
    if(/\d/.test(text)) score+=.25;
    if(!/[IOQ]{3,}/.test(text)) score+=.15;
    return Math.min(1,score);
  },

  stabilizePlate(candidates,max=8) {
    const counts=new Map();
    for(const item of (Array.isArray(candidates)?candidates.slice(-max):[])){
      const text=this.cleanOCR(item?.text||"").toUpperCase().replace(/[^A-Z0-9]/g,"");
      if(!text) continue;
      const weight=Number.isFinite(item?.confidence)?Math.max(.05,item.confidence):.5;
      counts.set(text,(counts.get(text)||0)+weight);
    }
    let text="",score=0;
    for(const [k,v] of counts) if(v>score){text=k;score=v;}
    return {text,score,confidence:candidates?.length?Math.min(1,score/candidates.length):0};
  },

  async toBlob(canvas,quality=.92) {
    return new Promise(resolve=>canvas.toBlob(resolve,"image/jpeg",quality));
  }
});
