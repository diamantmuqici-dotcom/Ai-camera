"use strict";
class VisionEngine{
  constructor(){this.detector=null;this.queueBusy=false}
  setDetector(detector){this.detector=detector}
  async analyze(source){if(this.queueBusy||!this.detector)return null;this.queueBusy=true;try{return await this.detector(source)}finally{this.queueBusy=false}}
}
window.VisionEngine=VisionEngine;