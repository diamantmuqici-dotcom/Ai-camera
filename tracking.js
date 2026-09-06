"use strict";

window.TrackingTools = Object.freeze({
  modes:["person","car","subject"],
  validMode(mode){return this.modes.includes(mode)?mode:"subject"},
  clampPoint(x,y){return {x:Math.min(1,Math.max(0,Number(x)||0)),y:Math.min(1,Math.max(0,Number(y)||0))}}
});
