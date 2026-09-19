"use strict";
window.CapabilityReport = {
  build(track){
    const s=CameraCapabilities.read(track),c=s.capabilities;
    return {camera:s.settings,features:s.features,ranges:{width:c.width||null,height:c.height||null,frameRate:c.frameRate||null,zoom:c.zoom||null,focusDistance:c.focusDistance||null,exposureCompensation:c.exposureCompensation||null},browser:{userAgent:navigator.userAgent,webGPU:!!navigator.gpu,webAssembly:typeof WebAssembly==="object",workers:typeof Worker==="function",mediaRecorder:typeof MediaRecorder==="function",imageCapture:"ImageCapture"in window,indexedDB:"indexedDB"in window}}
  },
  text(track){return JSON.stringify(this.build(track),null,2)}
};