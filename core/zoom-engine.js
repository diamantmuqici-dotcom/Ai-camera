"use strict";
class ZoomEngine {
  constructor({min=1,max=100}={}){this.min=min;this.max=max;this.target=1;this.current=1;this.velocity=0;this.last=performance.now()}
  setRange(min,max){this.min=Number.isFinite(min)?min:1;this.max=Math.max(this.min,Number(max)||this.max);this.target=this.clamp(this.target)}
  clamp(v){v=Number(v);return Number.isFinite(v)?Math.min(this.max,Math.max(this.min,v)):this.min}
  set(v){this.target=this.clamp(v);return this.target}
  pinch(startZoom,startDistance,distance){if(!(startDistance>0)||!(distance>0))return this.target;return this.set(startZoom*(distance/startDistance))}
  step(factor){return this.set(this.target*(Number(factor)||1))}
  tick(dt=16){const k=1-Math.exp(-dt/65);this.current+= (this.target-this.current)*k;if(Math.abs(this.target-this.current)<.001)this.current=this.target;return this.current}
  digital(hardwareMax=1){return Math.max(1,this.current/Math.max(1,hardwareMax))}
}
window.ZoomEngine=ZoomEngine;