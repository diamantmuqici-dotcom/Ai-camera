"use strict";
window.CameraCapabilities = {
  read(track){
    if(!track) return {capabilities:{},settings:{},features:{}};
    let capabilities={},settings={};
    try{capabilities=track.getCapabilities?.()||{}}catch{}
    try{settings=track.getSettings?.()||{}}catch{}
    const has=k=>Object.prototype.hasOwnProperty.call(capabilities,k);
    return {capabilities,settings,features:{
      zoom:has("zoom"),focusMode:has("focusMode"),focusDistance:has("focusDistance"),
      exposureCompensation:has("exposureCompensation"),torch:has("torch"),
      whiteBalanceMode:has("whiteBalanceMode"),frameRate:has("frameRate"),
      resolution:has("width")&&has("height")
    }};
  },
  range(caps,key){const v=caps?.[key];return v&&Number.isFinite(v.min)&&Number.isFinite(v.max)?{min:v.min,max:v.max,step:Number.isFinite(v.step)?v.step:null}:null},
  supports(track,key){return !!this.read(track).features[key]},
  label(state,key){return state?.features?.[key]?"AVAILABLE":"UNAVAILABLE"}
};