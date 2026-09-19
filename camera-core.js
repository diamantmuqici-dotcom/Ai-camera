"use strict";

window.CameraCore = Object.freeze({
  isMobile() {
    return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  },

  constraints({deviceId="",facing="environment",width=1920,height=1080,fps=30}={}) {
    const video = deviceId
      ? {deviceId:{exact:deviceId}}
      : {facingMode:{ideal:facing}};
    Object.assign(video,{
      width:{ideal:width},
      height:{ideal:height},
      frameRate:{ideal:fps}
    });
    return {video,audio:false};
  },

  async request(options={}) {
    if (!navigator.mediaDevices?.getUserMedia) {
      const e=new Error("Camera API unavailable"); e.name="NotSupportedError"; throw e;
    }
    try {
      return await navigator.mediaDevices.getUserMedia(this.constraints(options));
    } catch(e) {
      if(e?.name==="OverconstrainedError") {
        return navigator.mediaDevices.getUserMedia({
          video: options.deviceId
            ? {deviceId:{exact:options.deviceId}}
            : {facingMode:{ideal:options.facing||"environment"}},
          audio:false
        });
      }
      throw e;
    }
  },

  async apply(track,constraints) {
    if(!track?.applyConstraints) return false;
    try { await track.applyConstraints({advanced:[constraints]}); return true; }
    catch {
      try { await track.applyConstraints(constraints); return true; }
      catch { return false; }
    }
  },

  inspect(track) {
    if(!track) return {capabilities:{},settings:{}};
    let capabilities={},settings={};
    try { capabilities=track.getCapabilities?.()||{}; } catch {}
    try { settings=track.getSettings?.()||{}; } catch {}
    return {capabilities,settings};
  }
});
