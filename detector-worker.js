"use strict";

/*
 * Lightweight detector scheduler.
 * No model is bundled, so this worker never pretends to provide ML detections.
 * It provides bounded native scene/edge analysis and strict backpressure.
 */
let busy=false;

function luminance(r,g,b){return (r*77+g*150+b*29)>>8;}

function analyze(image,width,height){
  const data=image?.data;
  if(!data||width<8||height<8) return null;
  const step=Math.max(2,Math.floor(Math.min(width,height)/48));
  let sum=0,edges=0,n=0;
  for(let y=step;y<height-step;y+=step){
    for(let x=step;x<width-step;x+=step){
      const i=(y*width+x)*4;
      const l=luminance(data[i],data[i+1],data[i+2]);
      const ir=i+step*4,id=i+step*width*4;
      const lr=luminance(data[ir],data[ir+1],data[ir+2]);
      const ld=luminance(data[id],data[id+1],data[id+2]);
      sum+=l; edges+=Math.abs(l-lr)+Math.abs(l-ld); n++;
    }
  }
  if(!n) return null;
  return {x:0,y:0,width:1,height:1,score:Math.min(1,edges/n/80),meanLuma:sum/n};
}

self.onmessage=async e=>{
  const m=e.data||{};
  if(m.type==="reset"){busy=false;self.postMessage({type:"reset-done"});return;}
  if(m.type==="load-model"){
    self.postMessage({type:"model-ready",name:m.name||"native-analysis",available:false,
      message:"No external ML model is bundled; native analysis is available."});
    return;
  }
  if(m.type!=="detect") return;
  if(busy){self.postMessage({type:"dropped",id:m.id,reason:"backpressure"});return;}
  busy=true;
  const started=performance.now();
  try{
    const result=analyze(m.image,m.width,m.height);
    self.postMessage({
      type:"detections",id:m.id,
      detections:result?[{...result,type:"scene-region",source:"heuristic"}]:[],
      elapsedMs:performance.now()-started,
      modelAvailable:false
    });
  }finally{busy=false;}
};
