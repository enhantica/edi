// Private FILE1 candidate. Uses the EXISTING driver/CDP process, not another browser harness.
// No browser provider/read claim: those tool-result facts belong to real core/VM consumers.
import assert from 'node:assert/strict';
import {writeFile, mkdir} from 'node:fs/promises';
import {join} from 'node:path';

export async function inspectAssistantSelectedFiles({send,evaluate,frame,click,waitAX,event,lastEvents,shot,scratch,output,mode}) {
  const root=join(scratch,'assistant-selected'); await mkdir(root);
  const name='selected-Å-<b>.txt', text='12\tαβ🙂\r\n7.5000\n';
  const file=join(root,name); await writeFile(file,text,'utf8');
  const names=async()=> (await send('Accessibility.getFullAXTree')).nodes.filter(n=>!n.ignored).map(n=>n.name?.value || '');
  const present=async()=> (await names()).some(n=>n.includes(name));
  const waitAbsent=async()=> {
    const end=Date.now()+15000;
    do {if(!await present())return;await frame();} while(Date.now()<end);
    assert.fail('I15/files: removed/cancelled selected file remains visible');
  };
  await click(/^Show or hide assistant$/,'button','assistant.toggle');
  await waitAX(/Add files/i,true,'button');
  const picker=async()=> {
    lastEvents.delete('Page.fileChooserOpened');
    const opened=event('Page.fileChooserOpened');
    const [result]=await Promise.all([opened,click(/Add files/i,'button')]);
    assert(result.backendNodeId,'I15/FILE1: actual plus must open a genuine browser chooser');
    const input=await send('DOM.resolveNode',{backendNodeId:result.backendNodeId});
    const objectId=input.object.objectId;
    const genuine=await send('Runtime.callFunctionOn',{objectId,returnByValue:true,
      functionDeclaration:'function(){return this instanceof HTMLInputElement && this.type === "file" && this.multiple;}'});
    assert.equal(genuine.result.value,true,'I15/files: actual picker transfers genuine multi-file FileList authority');
    return {objectId};
  };
  // Actual user cancellation must not publish the planted name or consume future admission.
  const cancelled=await picker();
  await send('Runtime.callFunctionOn',{...cancelled,functionDeclaration:'function(){this.dispatchEvent(new Event("cancel"));}'});
  await frame(); await waitAbsent();
  const selected=await picker();
  await send('DOM.setFileInputFiles',{...selected,files:[file]});
  await waitAX(new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
  const actualFiles=await send('Runtime.callFunctionOn',{...selected,returnByValue:true,
    functionDeclaration:'async function(){const f=this.files[0];return {name:f.name,size:f.size,text:await f.text()};}'});
  assert.deepEqual(actualFiles.result.value,{name,size:Buffer.byteLength(text),text},'I11/I15/files: browser delivered exact independently planted File bytes, not a typed path or fake chip');
  await shot('assistant-selected-original');
  await click(/Remove.*selected-Å-/i,'button');
  await waitAbsent();
  // A real FileList above the declared count must be refused atomically, not partially admitted.
  const many=[];
  for(let i=0;i<33;++i) {const p=join(root,'count-'+i+'.txt');await writeFile(p,'x');many.push(p);}
  const over=await picker();
  await send('DOM.setFileInputFiles',{...over,files:many});
  await waitAX(/(?:too many|limit|maximum|exceed|resource)/i);
  assert(!(await names()).some(n=>/count-\d+\.txt/.test(n)),'I3/I15/files: count refusal cannot publish a partial selected collection');
  const note={scope:'actual browser chooser/cancel/selected literal chip/removal/count preflight only',genuineFileBytes:Buffer.byteLength(text),nativeOSChooser:false,drop:false,providerRead:false};
  await writeFile(join(output,mode+'-assistant-selected-files.json'),JSON.stringify(note,null,2));
}
