// Model only the external boundary; execute the consumer's real visual-observer helpers.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const actor=process.argv[2]||join(root,'tests/system/manual/project_browser_storage.mjs');
const source=await readFile(actor,'utf8');
const qml=await readFile(join(root,'app/qml/Main.qml'),'utf8');
const {waitControlGeometry}=await import(join(root,'tests/system/manual/web_control_geometry.mjs'));
// The concrete declarations determine the two target types, independently of the actor's requests.
assert.match(qml,/Column\s*\{\s*id:\s*saveAsChoiceColumn\s*objectName:\s*"project\.saveChoice"/,
  'The positive observation target must be the declared visual Column');
assert.match(qml,/AppDialog\s*\{\s*id:\s*saveAsChoice\s*objectName:\s*"saveAs\.choice"/,
  'The rejected observation target must be the declared QObject Popup');
const targets=new Map([['project.saveChoice','QQuickItem'],['saveAs.choice','QObject']]);
const begin=source.indexOf("      if(scenario==='example-warning-save-as'){");
const end=source.indexOf('      await pointer(observation.warningOk)',begin);
assert(begin>=0&&end>begin,'The controlled check must execute the actual warning branch');
const branch=source.slice(begin,end);
function helper(name,next){
  const start=source.indexOf('    const '+name+'=');
  const stop=source.indexOf('    const '+next+'=',start);
  assert(start>=0&&stop>start,'The actual observation helper must remain extractable: '+name);
  return source.slice(start+('    const '+name+'=').length,stop).trim().replace(/;$/,'');
}
const nativeSource=helper('native','pointer');
const hiddenSource=helper('hidden','warning');
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
async function run(body,{eager=false,invisible=false,staysVisible=false}={}){
  let visible=false,confirmed=false;
  const observations=[],actions=[];
  const window={__downloadBoundary:{calls:[],storage:['original-storage-save'],cancel(){actions.push('cancel');}},
    ediControlGeometry(name){
      observations.push(name);
      if(targets.get(name)!=='QQuickItem')throw Error("no item is named '"+name+"'");
      if(!visible)throw Error("no visible item is named '"+name+"'");
      return {objectName:name,visible:true,enabled:true,x:200,y:200,width:300,height:200};
    }};
  const evaluate=async(expression,arg)=>{
    const previous=globalThis.window;globalThis.window=window;
    try{return typeof expression==='string'?new Function('window','return '+expression)(window):expression(arg);}
    finally{globalThis.window=previous;}
  };
  const page={waitForFunction:async(expression,arg)=>{
    assert(await evaluate(expression,arg),'The actual observation/request predicate must be satisfied');
  }};
  const frame=async()=>{};
  const geometry=async name=>waitControlGeometry(expression=>evaluate(expression),frame,name,{timeoutMs:1});
  const native=new Function('evaluate','return ('+nativeSource+');')(evaluate);
  const hidden=new Function('page','return ('+hiddenSource+');')(page);
  const observation={warningSaveAs:'actual-warning-action'};
  const pointer=async name=>{assert.equal(name,observation.warningSaveAs,'The consumer must press the warning Save-as action');actions.push('warning');visible=!invisible;if(eager)window.__downloadBoundary.calls.push('early');};
  const click=async(regex,role)=>{assert.equal(regex.source,'^OK$','Confirmation must select the actual OK action');assert.equal(role,'button','Confirmation must use the actual button role');assert(visible,'The actual OK requires a visible confirmation');actions.push('confirm');confirmed=true;visible=staysVisible;window.__downloadBoundary.calls.push('requested');};
  const fn=new AsyncFunction('assert','scenario','observation','pointer','geometry','native','evaluate','click','hidden','page','frame','events','receipts','first','mode','console',`for(const once of [0]) { ${body} }`);
  await fn(assert,'example-warning-save-as',observation,pointer,geometry,native,evaluate,click,hidden,page,frame,{downloads:0},{},{},'controlled-route',{log(){}});
  assert(confirmed,'The warning route must confirm its surviving dialog');
  assert.deepEqual(actions,['warning','confirm','cancel'],'Confirmation must precede the retained pending-download cancellation');
  assert(observations.length>=3&&observations.every(name=>targets.get(name)==='QQuickItem'),
    'Positive, native and closure observations must all use the visual hook domain');
}
await run(branch);
console.log('PASS visual-observations');
for(const call of ['geometry','native','hidden']){
  const old=call+"('project.saveChoice')",replacement=call+"('saveAs.choice')";
  const changed=branch.replace(old,replacement);
  assert.notEqual(changed,branch,'Each Popup-observation escape must actually change the consumer: '+call);
  await assert.rejects(()=>run(changed),/declared native control|must open|no item is named/,
    'Each observation path must reject the QObject Popup: '+call);
  console.log('PASS popup-'+call);
}
await assert.rejects(()=>run(branch,{eager:true}),/before dialog confirmation/,'The download cannot precede actual confirmation');
console.log('PASS early-download');
await assert.rejects(()=>run(branch,{invisible:true}),/declared native control/,'The visual column must actually be shown');
console.log('PASS not-visible');
await assert.rejects(()=>run(branch,{staysVisible:true}),/predicate must be satisfied/,'Confirmation must hide the actual visual target');
console.log('PASS not-closed');
const omitted=branch.replace("await click(/^OK$/,'button');await hidden('project.saveChoice');",'');
assert.notEqual(omitted,branch,'The omitted-confirmation escape must actually change the consumer');
await assert.rejects(()=>run(omitted),/predicate must be satisfied/,'The consumer must still perform real confirmation');
console.log('PASS no-confirmation');
console.log('Actual visual observers passed; three Popup-target escapes and four confirmation/visibility escapes rejected');
