"use strict";

window.CameraUtils=Object.freeze({
  isMobile(){return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);},
  clamp(value,min,max){
    const n=Number(value);
    return Number.isFinite(n)?Math.min(max,Math.max(min,n)):min;
  },
  lerp(a,b,t){return a+(b-a)*this.clamp(t,0,1);},
  cameraConstraints({
    deviceId="",facing="environment",width=1920,height=1080,fps=30,aspectRatio
  }={}){
    const video=deviceId?{deviceId:{exact:deviceId}}:{facingMode:{ideal:facing}};
    video.width={ideal:width};video.height={ideal:height};video.frameRate={ideal:fps};
    if(Number.isFinite(aspectRatio)&&aspectRatio>0)video.aspectRatio={ideal:aspectRatio};
    return {video,audio:false};
  },
  capabilityRange(capabilities,key){
    const c=capabilities?.[key];
    if(!c||typeof c!=="object"||!Number.isFinite(c.min)||!Number.isFinite(c.max))return null;
    return {min:c.min,max:c.max,step:Number.isFinite(c.step)?c.step:undefined};
  },
  supportsOffscreenCanvas(){return typeof window.OffscreenCanvas==="function";},
  supportsImageBitmap(){return typeof window.createImageBitmap==="function";}
});
