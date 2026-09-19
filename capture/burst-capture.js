"use strict";
class BurstCapture {
  constructor({capture,score}={}){this.capture=capture;this.score=score||(()=>0);this.running=false}
  async run(count=4,{delay=70}={}){if(this.running)throw new Error("Burst already active");this.running=true;const frames=[];try{for(let i=0;i<count;i++){const frame=await this.capture();frames.push({frame,score:this.score(frame)});if(delay&&i<count-1)await new Promise(r=>setTimeout(r,delay))}return frames.sort((a,b)=>b.score-a.score)}finally{this.running=false}}
}
window.BurstCapture=BurstCapture;