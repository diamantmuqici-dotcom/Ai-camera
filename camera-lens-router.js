"use strict";

/*
 * Browser-safe lens routing.
 * 0.5x is real only when Chrome exposes another camera input representing the
 * ultrawide. When it does not, the app explicitly falls back instead of
 * pretending digital crop can create a wider field of view.
 */
window.LensRouter = {
  cameras:[],

  async refresh(){
    try{
      this.cameras=(await navigator.mediaDevices.enumerateDevices())
        .filter(d=>d.kind==="videoinput");
    }catch{this.cameras=[];}
    return this.cameras;
  },

  classify(device){
    const label=String(device?.label||"").toLowerCase();
    if(/ultra.?wide|ultrawide|0\.5x|0\.5|wide angle|uw/.test(label))return"ultrawide";
    if(/tele|telephoto|zoom|periscope|3x|5x|70mm|120mm/.test(label))return"tele";
    if(/front|user|selfie/.test(label))return"front";
    return"main";
  },

  findUltrawide(currentId){
    const list=this.cameras.filter(d=>d.deviceId!==currentId);
    return list.find(d=>this.classify(d)==="ultrawide")||null;
  },

  async selectHalfX(){
    const current=APP.track?.getSettings?.().deviceId||"";
    await this.refresh();
    const wide=this.findUltrawide(current);
    if(!wide){
      return {ok:false,reason:"not-exposed"};
    }
    await Cam.switchCamera(wide.deviceId);
    APP.lensGuess="ULTRAWIDE";
    if(window.Zoom)Zoom.wideActive=true;
    const chip=document.getElementById("chipLens");
    if(chip)chip.textContent="LENS ULTRAWIDE";
    return {ok:true,device:wide};
  },

  describe(){
    return this.cameras.map(d=>({id:d.deviceId,type:this.classify(d),label:d.label||"Camera"}));
  }
};
