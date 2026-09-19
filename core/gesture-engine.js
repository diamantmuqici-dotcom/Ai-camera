"use strict";
class GestureEngine {
  constructor(el,{onPinch,onTap,onDoubleTap,onSwipe}={}){this.el=el;this.cb={onPinch,onTap,onDoubleTap,onSwipe};this.points=new Map();this.pinchStart=0;this.zoomStart=1;this.pinching=false;this.lastTap=0;this.tapTimer=0;this.startX=0;this.startY=0;this.bind()}
  distance(){const a=[...this.points.values()];return a.length===2?Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y):0}
  bind(){
    this.el.style.touchAction="none";
    this.el.addEventListener("pointerdown",e=>{this.points.set(e.pointerId,{x:e.clientX,y:e.clientY,t:performance.now()});try{this.el.setPointerCapture(e.pointerId)}catch{};if(this.points.size===1){this.startX=e.clientX;this.startY=e.clientY}else if(this.points.size===2){this.pinching=true;this.pinchStart=Math.max(1,this.distance());this.zoomStart=this.cb.getZoom?.()??1}});
    this.el.addEventListener("pointermove",e=>{if(!this.points.has(e.pointerId))return;this.points.set(e.pointerId,{x:e.clientX,y:e.clientY,t:performance.now()});if(this.points.size===2){const d=this.distance();if(d>0){e.preventDefault();this.cb.onPinch?.(this.zoomStart,this.pinchStart,d)}}},{passive:false});
    const end=e=>{const p=this.points.get(e.pointerId);this.points.delete(e.pointerId);try{this.el.releasePointerCapture(e.pointerId)}catch{};if(!p)return;if(this.points.size)return;if(this.pinching){this.pinching=false;return}const dt=performance.now()-p.t,dx=e.clientX-this.startX,dy=e.clientY-this.startY;if(dt<260&&Math.hypot(dx,dy)<14){const n=performance.now();if(n-this.lastTap<300){clearTimeout(this.tapTimer);this.lastTap=0;this.cb.onDoubleTap?.(e);return}this.lastTap=n;this.tapTimer=setTimeout(()=>{if(this.lastTap===n){this.lastTap=0;this.cb.onTap?.(e)}},310)}else if(dt<500&&Math.abs(dx)>70&&Math.abs(dx)>Math.abs(dy))this.cb.onSwipe?.(dx<0?"left":"right")};
    this.el.addEventListener("pointerup",end);this.el.addEventListener("pointercancel",e=>{this.points.delete(e.pointerId);this.pinching=false});
  }
}
window.GestureEngine=GestureEngine;