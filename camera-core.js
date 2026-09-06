"use strict";

window.CameraCore = Object.freeze({
  isMobile(){return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)},
  constraints({deviceId="",facing="environment",width=1920,height=1080,fps=30}={}){
    const video=deviceId?{deviceId:{exact:deviceId}}:{facingMode:{ideal:facing}};
    Object.assign(video,{width:{ideal:width},height:{ideal:height},frameRate:{ideal:fps}});
    return {video,audio:false};
  },
  async request(options={}){
    if(!navigator.mediaDevices?.getUserMedia)throw new Error("Camera API unavailable");
    return navigator.mediaDevices.getUserMedia(this.constraints(options));
  }
});
