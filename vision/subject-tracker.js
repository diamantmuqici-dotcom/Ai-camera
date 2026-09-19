"use strict";
class SubjectTracker{
  constructor(){this.box=null;this.confidence=0;this.lost=0}
  update(box,confidence=.5){if(!box){this.lost++;if(this.lost>8)this.box=null;return this.box}this.lost=0;this.confidence=confidence;this.box=this.box?TrackingTools.smoothBox(this.box,box,.22):box;return this.box}
  reset(){this.box=null;this.confidence=0;this.lost=0}
}
window.SubjectTracker=SubjectTracker;