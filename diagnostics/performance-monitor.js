"use strict";
class PerformanceMonitor {
  constructor(video){this.video=video;this.samples=[];this.last=performance.now();this.fps=0;this.dropped=0;this.timer=0}
  tick(){const t=performance.now();if(t-this.timer<500)return;this.timer=t;const q=this.video?.getVideoPlaybackQuality?.();if(q){this.fps=q.totalVideoFrames-(this._frames??q.totalVideoFrames);this.dropped=q.droppedVideoFrames-(this._dropped??q.droppedVideoFrames);this._frames=q.totalVideoFrames;this._dropped=q.droppedVideoFrames}else this.fps=0}
  report(){return {fps:this.fps,droppedFrames:this.dropped,cores:navigator.hardwareConcurrency||null,deviceMemory:navigator.deviceMemory||null}}
}
window.PerformanceMonitor=PerformanceMonitor;