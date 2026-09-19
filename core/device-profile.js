"use strict";
window.DeviceProfile = {
  classify({caps={},settings={},fps=60}={}){
    const cores=navigator.hardwareConcurrency||4, ram=Number(navigator.deviceMemory)||4;
    if(!/Android/i.test(navigator.userAgent)) return cores>=8?"DESKTOP_HIGH":"DESKTOP";
    if(cores>=8&&ram>=6&&Math.max(Number(caps?.width?.max)||0,Number(settings?.width)||0)>=1920) return "HIGH_END_ANDROID";
    if(cores>=6||ram>=4) return "MID_RANGE_ANDROID";
    return "LOW_POWER_ANDROID";
  },
  summary(){return {profile:this.classify(),cores:navigator.hardwareConcurrency||null,deviceMemory:navigator.deviceMemory||null,platform:navigator.platform||"",userAgent:navigator.userAgent}}
};