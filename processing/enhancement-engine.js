"use strict";
window.EnhancementEngine = {
  async run(canvas,{gain=1,contrast=100,saturation=100,sharpen=0}={},signal){
    const ctx=canvas.getContext("2d",{willReadFrequently:true}),img=ctx.getImageData(0,0,canvas.width,canvas.height),d=img.data;
    for(let i=0;i<d.length;i+=4){if(signal?.aborted)throw new DOMException("Cancelled","AbortError");const l=.299*d[i]+.587*d[i+1]+.114*d[i+2];d[i]=Math.max(0,Math.min(255,((l+(d[i]*gain-l)*(saturation/100))-127.5)*(contrast/100)+127.5));d[i+1]=Math.max(0,Math.min(255,((l+(d[i+1]*gain-l)*(saturation/100))-127.5)*(contrast/100)+127.5));d[i+2]=Math.max(0,Math.min(255,((l+(d[i+2]*gain-l)*(saturation/100))-127.5)*(contrast/100)+127.5))}
    ctx.putImageData(img,0,0);return canvas
  }
};