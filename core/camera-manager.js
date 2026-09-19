"use strict";
class CameraManager {
  constructor(video){this.session=new CameraSession(video);this.devices=[];this.lastRequest=null}
  async enumerate(){try{this.devices=(await navigator.mediaDevices.enumerateDevices()).filter(d=>d.kind==="videoinput")}catch{this.devices=[]}return this.devices}
  async request({deviceId="",facing="environment",width=1920,height=1080,fps=30}={}){
    if(!navigator.mediaDevices?.getUserMedia)throw Object.assign(new Error("Camera API unavailable"),{name:"NotSupportedError"});
    const video=deviceId?{deviceId:{exact:deviceId}}:{facingMode:{ideal:facing}};
    Object.assign(video,{width:{ideal:width},height:{ideal:height},frameRate:{ideal:fps}});
    this.lastRequest={deviceId,facing,width,height,fps};
    let stream;
    try{stream=await navigator.mediaDevices.getUserMedia({video,audio:false})}
    catch(e){stream=await navigator.mediaDevices.getUserMedia({video:deviceId?{deviceId:{exact:deviceId}}:{facingMode:{ideal:facing}},audio:false})}
    this.session.attach(stream);await this.session.play();await this.enumerate();
    return {track:this.session.track,settings:this.session.settings(),capabilities:this.session.capabilities(),devices:this.devices};
  }
  async switch(deviceId){return this.request({...this.lastRequest,deviceId})}
  stop(){this.session.stop()}
  async recover(){if(this.restarting||!this.lastRequest)return false;this.restarting=true;try{await this.request(this.lastRequest);return true}finally{this.restarting=false}}
}
window.CameraManager=CameraManager;