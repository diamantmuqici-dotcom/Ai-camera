"use strict";
class LensManager {
  constructor(){this.devices=[]}
  update(devices){this.devices=Array.isArray(devices)?devices:[];return this.devices}
  classify(d){
    const l=String(d?.label||"").toLowerCase();
    if(/ultra.?wide|ultrawide|0\.5x|wide angle/.test(l))return "ULTRAWIDE";
    if(/telephoto|tele|periscope|3x|5x|70mm|120mm/.test(l))return "TELEPHOTO";
    if(/front|user|selfie/.test(l))return "FRONT";
    if(/back|rear|environment|main/.test(l))return "MAIN";
    return "UNKNOWN";
  }
  find(type,currentId=""){return this.devices.find(d=>d.deviceId!==currentId&&this.classify(d)===type)||null}
  sourceForZoom(z){if(z<=.75)return "ULTRAWIDE";if(z>=3)return "TELEPHOTO";return "MAIN"}
}
window.LensManager=LensManager;