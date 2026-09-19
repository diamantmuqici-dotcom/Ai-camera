"use strict";
class CameraSession {
  constructor(video){this.video=video;this.stream=null;this.track=null;this.state="idle";this.restarting=false}
  attach(stream){
    this.stopTracks();this.stream=stream;this.track=stream?.getVideoTracks?.()[0]||null;
    if(!this.track)throw new Error("No video track");
    this.video.srcObject=stream;this.state="ready";
    return this.track;
  }
  async play(){await this.video.play().catch(()=>{});return this}
  stopTracks(){if(this.stream)for(const t of this.stream.getTracks())try{t.stop()}catch{};this.stream=null;this.track=null}
  stop(){this.stopTracks();this.video.srcObject=null;this.state="stopped"}
  async apply(constraints){if(!this.track?.applyConstraints)return false;try{await this.track.applyConstraints(constraints);return true}catch{return false}}
  settings(){try{return this.track?.getSettings?.()||{}}catch{return{}}}
  capabilities(){try{return this.track?.getCapabilities?.()||{}}catch{return{}}}
}
window.CameraSession=CameraSession;