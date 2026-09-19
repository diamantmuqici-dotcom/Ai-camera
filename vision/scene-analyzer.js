"use strict";
window.SceneAnalyzer = {
  analyze({mean=128,clipHi=0,clipLo=0,sharp=0,motion=0}={}){
    const low=mean<55,backlight=clipHi>.08&&clipLo>.08,highMotion=motion>.55;
    return {lowLight:low,backlight,highMotion,blur:sharp<35,recommendation:low?"LOW LIGHT":highMotion?"HIGH MOTION":backlight?"HDR RECOMMENDED":"READY"}
  }
};