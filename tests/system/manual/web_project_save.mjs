// Observe the actual save UI; downloading bytes alone does not retire a popup.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {join} from 'node:path';

const controls=['project.saveChoice','saveAs.zip','saveAs.accept','webNotice.text',
  'appBar.button.save','open.folder','unsavedChanges.title','unsavedChanges.discard',
  'createProject.name','webStorageWarning.text','save.error'];
export const projectDialogExpression=`(() => {
  const controls={};
  for(const name of ${JSON.stringify(controls)}) {
    try {controls[name]={present:true,item:window.ediControlGeometry(name)};}
    catch(error) {
      if(error.message===\`ediControlGeometry: no item is named '\${name}'\` ||
         error.message===\`ediControlGeometry: no visible item is named '\${name}'\`)
        controls[name]={present:false,reason:error.message};
      else throw error;
    }
  }
  return {title:document.title,controls};
})()`;

export async function waitForSaveSettled(evaluate,frame,before,{timeoutMs=45000}={}) {
  assert(typeof before?.enabled==='boolean',
    'Save readiness requires the actual toolbar state observed before this download');
  const deadline=Date.now()+timeoutMs;
  let state;
  do {
    state=await evaluate(projectDialogExpression);
    const read=name=>{
      const found=state?.controls?.[name];
      assert(typeof found?.present==='boolean',
        'Save readiness requires a fresh native observation for every declared control');
      if(!found.present)return null;
      assert(found.item?.objectName===name && found.item.visible===true &&
        typeof found.item.enabled==='boolean',
        'Save readiness cannot reuse retargeted, hidden or malformed native controls');
      return found.item;
    };
    const blocked=['project.saveChoice','saveAs.zip','saveAs.accept','webNotice.text',
      'unsavedChanges.title','unsavedChanges.discard','webStorageWarning.text','save.error']
      .map(read).some(Boolean);
    const save=read('appBar.button.save');
    if(!blocked && save && save.enabled===before.enabled)return state;
    await frame();
  } while(Date.now()<deadline);
  throw Error('The previous save must visibly finish before the next guarded action: '+JSON.stringify(state));
}

export function projectFailureRecorder({send,output,mode,write=writeFile}) {
  let recording;
  return error=>{
    if(recording)return recording;
    recording=(async()=>{
      const state={trigger:error.message,capturedAt:new Date().toISOString()};
      const attempt=async(name,operation)=>{
        try {await operation();}
        catch(failure) {state[name+'Error']=failure.message;}
      };
      await Promise.all([
        attempt('screenshot',async()=>{
          const shot=await send('Page.captureScreenshot',{format:'png'});
          await write(join(output,`${mode}-failure.png`),Buffer.from(shot.data,'base64'));
        }),
        attempt('accessibility',async()=>{
          const tree=await send('Accessibility.getFullAXTree');
          await write(join(output,`${mode}-failure-accessibility.json`),JSON.stringify(tree,null,2));
        }),
        attempt('dialogs',async()=>{
          const reply=await send('Runtime.evaluate',{expression:projectDialogExpression,returnByValue:true});
          if(reply.exceptionDetails)state.dialogException=reply.exceptionDetails;
          assert(!reply.exceptionDetails && reply.result?.value,
            'Failure evidence must retain actual native dialog observations or their read error');
          state.dialogs=reply.result.value;
        }),
        attempt('pickers',async()=>{
          const reply=await send('Runtime.evaluate',{expression:'window.__e04PickerAttempts || []',returnByValue:true});
          if(reply.exceptionDetails)state.pickerException=reply.exceptionDetails;
          assert(!reply.exceptionDetails && Array.isArray(reply.result?.value),
            'Failure evidence must retain the actual browser picker attempts or their read error');
          await write(join(output,`${mode}-failure-pickers.json`),JSON.stringify(reply.result.value,null,2));
        }),
      ]);
      await write(join(output,`${mode}-failure-dialogs.json`),JSON.stringify(state,null,2));
    })();
    recording.catch(()=>{});
    return recording;
  };
}
