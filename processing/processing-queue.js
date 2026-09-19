"use strict";
class ProcessingQueue {
  constructor(limit=1){this.limit=limit;this.active=0;this.pending=[]}
  push(task){return new Promise((resolve,reject)=>{this.pending.push({task,resolve,reject});this.pump()})}
  pump(){while(this.active<this.limit&&this.pending.length){const x=this.pending.shift();this.active++;Promise.resolve().then(x.task).then(x.resolve,x.reject).finally(()=>{this.active--;this.pump()})}}
  get depth(){return this.pending.length+this.active}
}
window.ProcessingQueue=ProcessingQueue;