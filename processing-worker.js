"use strict";

let cancelled=new Set();

const clamp=(v,a=0,b=255)=>Math.max(a,Math.min(b,v));

function enhanceRGBA(buffer,width,height,options={}){
  const data=new Uint8ClampedArray(buffer);
  const out=new Uint8ClampedArray(data.length);
  const gain=Number.isFinite(options.gain)?options.gain:1;
  const contrast=Number.isFinite(options.contrast)?options.contrast/100:1;
  const saturation=Number.isFinite(options.saturation)?options.saturation/100:1;

  for(let i=0;i<data.length;i+=4){
    let r=data[i]*gain,g=data[i+1]*gain,b=data[i+2]*gain;
    const l=r*.299+g*.587+b*.114;
    r=l+(r-l)*saturation; g=l+(g-l)*saturation; b=l+(b-l)*saturation;
    out[i]=clamp((r-127.5)*contrast+127.5);
    out[i+1]=clamp((g-127.5)*contrast+127.5);
    out[i+2]=clamp((b-127.5)*contrast+127.5);
    out[i+3]=data[i+3];
  }

  const sharpen=Math.max(0,Math.min(1,Number(options.sharpen)||0));
  if(sharpen>.01&&width>2){
    const amount=sharpen*.35;
    for(let y=0;y<height;y++){
      if(cancelled.size) break;
      for(let x=1;x<width-1;x++){
        const i=(y*width+x)*4;
        for(let c=0;c<3;c++){
          const center=out[i+c],blur=(out[i-4+c]+out[i+4+c])*.5;
          out[i+c]=clamp(center+(center-blur)*amount);
        }
      }
    }
  }
  return out.buffer;
}

self.onmessage=e=>{
  const m=e.data||{};
  if(m.type==="cancel"){if(m.id!=null)cancelled.add(m.id);return;}
  if(m.type==="ping"){self.postMessage({type:"pong",id:m.id});return;}
  if(m.type==="identity"){
    self.postMessage({type:"processed",id:m.id,buffer:m.buffer},m.buffer?[m.buffer]:[]);
    return;
  }
  if(m.type==="enhance"&&m.buffer){
    const id=m.id??performance.now();
    cancelled.delete(id);
    try{
      const buffer=enhanceRGBA(m.buffer,m.width,m.height,m.options);
      self.postMessage({type:"enhanced",id,width:m.width,height:m.height,buffer},[buffer]);
    }finally{cancelled.delete(id);}
  }
};
