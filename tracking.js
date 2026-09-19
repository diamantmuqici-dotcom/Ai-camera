"use strict";

window.TrackingTools = Object.freeze({
  modes:["person","car","plate","document","text","subject"],

  validMode(mode) {
    return this.modes.includes(mode)?mode:"subject";
  },

  clampPoint(x,y) {
    return {x:Math.min(1,Math.max(0,Number(x)||0)),y:Math.min(1,Math.max(0,Number(y)||0))};
  },

  smoothBox(previous,next,amount=.22) {
    if(!previous) return {...next};
    const a=Math.min(1,Math.max(0,amount));
    return {
      x:previous.x+(next.x-previous.x)*a,
      y:previous.y+(next.y-previous.y)*a,
      width:previous.width+(next.width-previous.width)*a,
      height:previous.height+(next.height-previous.height)*a
    };
  },

  confidenceFromSad(sad,maxSad) {
    if(!Number.isFinite(sad)||!Number.isFinite(maxSad)||maxSad<=0) return 0;
    return Math.min(1,Math.max(0,1-sad/maxSad));
  }
});
