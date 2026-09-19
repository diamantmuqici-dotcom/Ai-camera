"use strict";
class VideoCapture{
  constructor(){this.recorder=null;this.chunks=[];this.started=0;this.mime=""}
  pickMime(){const list=["video/mp4;codecs=avc1","video/webm;codecs=vp9","video/webm;codecs=vp8","video/webm"];return list.find(x=>window.MediaRecorder?.isTypeSupported?.(x))||""}
  start(stream,{fps=30,bitrate=12000000}={}){if(!window.MediaRecorder)throw new Error("MediaRecorder unavailable");this.mime=this.pickMime();this.chunks=[];this.recorder=new MediaRecorder(stream,{mimeType:this.mime||undefined,videoBitsPerSecond:bitrate});this.recorder.ondataavailable=e=>e.data?.size&&this.chunks.push(e.data);this.started=Date.now();this.recorder.start(1000);return this.recorder}
  stop(){return new Promise(resolve=>{if(!this.recorder){resolve(null);return}this.recorder.onstop=()=>resolve(new Blob(this.chunks,{type:this.mime||"video/webm"}));this.recorder.stop()})}
}
window.VideoCapture=VideoCapture;