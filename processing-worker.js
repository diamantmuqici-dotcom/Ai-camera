"use strict";

/* Generic worker scheduler for future heavy image kernels. */
self.onmessage = event => {
  const message = event.data || {};
  if(message.type === "ping") self.postMessage({type:"pong",id:message.id});
  else if(message.type === "identity") self.postMessage({type:"processed",id:message.id,buffer:message.buffer},message.buffer?[message.buffer]:[]);
};
