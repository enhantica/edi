// Focused real-browser status action lifetime checks; no QML evaluator or state writer.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {restoreCanvasViewport} from './web_control_geometry.mjs';

const shared = ['statusBar.fit.outcome','statusBar.fit.reset','statusBar.fit.follow','statusBar.fit.button'];
const actionWords = new Set(['Fit','Continue','Refit','Stop','Reset','Follow']);
const property = (node, name) => (node.properties || []).find(p => p.name === name)?.value?.value;
const active = node => !node.ignored && node.role?.value === 'button' && property(node,'disabled') !== true;
const summary = node => ({nodeId:node.nodeId,backendDOMNodeId:node.backendDOMNodeId,
  ignored:node.ignored,role:node.role,name:node.name,properties:node.properties});
// Same pinned Qt integer rectangle domain as the running-control observer.
export const roundedStatusActionRect = item => {
  assert(item && ['x','y','width','height'].every(key=>Number.isFinite(item[key])),
    'Native accessible geometry is finite before Qt integer conversion');
  const qtRound = number => Math.trunc(Math.max(-2147483648,
    Math.min(2147483647, number + (number < 0 ? -0.5 : 0.5)))) || 0;
  return {x:qtRound(item.x),y:qtRound(item.y),
    width:qtRound(item.width),height:qtRound(item.height)};
};
const rounded = roundedStatusActionRect;
const borderRect = box => {
  const q=box.model.border;
  assert(Array.isArray(q) && q.length===8 && q.every(Number.isFinite),
    'A status action has an actual finite DOM border rectangle');
  return {x:Math.min(q[0],q[2],q[4],q[6]),y:Math.min(q[1],q[3],q[5],q[7]),
    width:Math.max(q[0],q[2],q[4],q[6])-Math.min(q[0],q[2],q[4],q[6]),
    height:Math.max(q[1],q[3],q[5],q[7])-Math.min(q[1],q[3],q[5],q[7])};
};
const equalRect = (a,b) => ['x','y','width','height'].every(k=>a[k]===b[k]);

export function statusActionLifetimeChecks({send,evaluate,frame,output,mode}) {
  const facts=[];
  const retain=async(stage,value)=>{
    facts.push({stage,value});
    await writeFile(join(output,`${mode}-status-action-lifetime.json`),JSON.stringify({
      scope:'Focused public project/example lifecycle before fitting; not fit/save/scientific acceptance',
      facts,criteria:{positive:['Fit first lifetime','Fit recreated lifetime'],
        inactive:shared},unexercisedByDesign:['outcome/results positive Press','scan Reset positive Press',
          'running-scan Follow positive Press','visible-but-unavailable Fit','disabled ancestor',
          'keyboard Enter/Space activation','synthetic detached-DOM click'],
    },null,2));
  };
  const geometry = name => evaluate(`(() => {try {
    return {present:true,item:window.ediControlGeometry(${JSON.stringify(name)})};
  } catch(error) {
    if ([${JSON.stringify("ediControlGeometry: no item is named '" )}+${JSON.stringify(name)}+"'",
         ${JSON.stringify("ediControlGeometry: no visible item is named '")}+${JSON.stringify(name)}+"'"].includes(error.message))
      return {present:false,reason:error.message};
    throw error;
  }})()`);
  const domFacts=async objectId => {
    const reply=await send('Runtime.callFunctionOn',{objectId,returnByValue:true,
      functionDeclaration:`function() {const root=this.getRootNode();const r=this.getBoundingClientRect();
        return {connected:this.isConnected,nodeName:this.nodeName,focused:root.activeElement===this,
          ariaHidden:this.getAttribute('aria-hidden'),rect:{x:r.x,y:r.y,width:r.width,height:r.height}};}`});
    assert(!reply.exceptionDetails && reply.result?.value,
      'The retained actual DOM representation remains observable without injected Qt behavior');
    return reply.result.value;
  };
  const noActions=async stage => {
    const children=[];
    for(const name of shared)children.push({name,...await geometry(name+'.accessibleAction')});
    const tree=await send('Accessibility.getFullAXTree');
    const exposed=tree.nodes.filter(n=>active(n)&&actionWords.has(n.name?.value));
    await retain(stage,{children,exposed:exposed.map(summary)});
    assert(children.every(row=>row.present===false),
      'The genuinely empty project exposes none of the shared named active representations');
    assert.equal(exposed.length,0,'Unavailable fit actions cannot advertise an enabled AX Button');
  };
  const live=async(stage,{oldBackendDOMNodeId}={}) => {
    await restoreCanvasViewport(evaluate);
    const deadline=Date.now()+45000;
    let last;
    do {
      const outer=await geometry('statusBar.fit.button');
      const tree=await send('Accessibility.getFullAXTree');
      const candidates=tree.nodes.filter(n=>!n.ignored&&n.name?.value==='Fit'&&n.backendDOMNodeId);
      const atRect=[];
      if(outer.present){
        const item=outer.item;
        assert(item.objectName==='statusBar.fit.button'&&item.visible===true&&item.enabled===true&&
          ['x','y','width','height'].every(k=>Number.isFinite(item[k]))&&item.width>0&&item.height>0,
          'The public native outer Fit owner is current, finite, visible and enabled');
        for(const node of candidates){
          const box=await send('DOM.getBoxModel',{backendNodeId:node.backendDOMNodeId});
          if(equalRect(borderRect(box),rounded(item)))atRect.push(node);
        }
      }
      last={outer,matching:atRect.map(summary),named:candidates.map(summary)};
      const buttons=atRect.filter(active);
      assert(buttons.length<=1,'Duplicate actionable Fit representations at one actual outer rectangle refuse');
      if(buttons.length===1){
        const node=buttons[0];
        const child=await geometry('statusBar.fit.button.accessibleAction');
        assert(child.present&&child.item.objectName==='statusBar.fit.button.accessibleAction'&&child.item.visible===true&&child.item.enabled===true,'An active Button is backed by the actual named Qt child, not a generic DOM substitute');
        assert.deepEqual(rounded(child.item),rounded(outer.item),
          'The one actual child representation has exactly its original outer control rectangle');
        assert.equal(typeof child.item.activeFocus,'boolean',
          'The existing read-only geometry must carry actual native hasActiveFocus(), never a synthetic focus proxy');
        if(oldBackendDOMNodeId!==undefined)assert.notEqual(node.backendDOMNodeId,oldBackendDOMNodeId,
          'A recreated action has a new DOM identity after actual project retirement');
        const inactive=[];
        for(const name of shared.filter(name=>name!=='statusBar.fit.button'))
          inactive.push({name,...await geometry(name+'.accessibleAction')});
        const group=await geometry('statusBar.fit');
        assert(group.present,'The actual Fit Row exists for a whole shared-consumer action census');
        const bounds=rounded(group.item),scoped=[];
        for(const candidate of tree.nodes.filter(n=>active(n)&&n.backendDOMNodeId)){
          const rect=borderRect(await send('DOM.getBoxModel',{backendNodeId:candidate.backendDOMNodeId}));
          if(rect.width>0&&rect.height>0&&rect.x>=bounds.x&&rect.y>=bounds.y&&
            rect.x+rect.width<=bounds.x+bounds.width&&rect.y+rect.height<=bounds.y+bounds.height)
            scoped.push({...summary(candidate),rect});
        }
        await retain(stage+'-shared-census',{group,inactive,activeButtons:scoped});
        assert(inactive.every(row=>row.present===false),
          'The fresh unfitted single/joint input cannot invent scan Reset/Follow or result actions');
        assert.equal(scoped.length,1,'Passive fit metrics and unavailable shared consumers expose no extra Button');
        assert.equal(scoped[0].backendDOMNodeId,node.backendDOMNodeId,
          'The sole action in this actual unfitted Fit Row is the same admitted Fit representation');
        const resolved=await send('DOM.resolveNode',{backendNodeId:node.backendDOMNodeId});
        const objectId=resolved.object?.objectId;assert(objectId,'The AX action owns a real DOM object');
        const dom=await domFacts(objectId);
        const listeners=await send('DOMDebugger.getEventListeners',{objectId});
        const types=listeners.listeners.map(listener=>listener.type);
        await retain(stage+'-before-focus',{...last,child,dom,listenerTypes:types});
        assert.equal(dom.nodeName,'BUTTON','Fixed Button action lifetime creates an actual DOM button');
        assert(dom.connected&&equalRect(dom.rect,rounded(outer.item)),
          'The connected DOM Button occupies the same actual Qt control rectangle');
        assert.equal(types.filter(type=>type==='click').length,1,
          'The sole Button representation has one real Qt browser click-to-action listener');
        assert.equal(types.filter(type=>type==='focus').length,1,
          'The same representation owns the real browser focus-to-SetFocus route');
        await send('DOM.focus',{backendNodeId:node.backendDOMNodeId});
        await restoreCanvasViewport(evaluate);
        let focus;
        do {
          const actual=await geometry('statusBar.fit.button.accessibleAction');
          const ax=await send('Accessibility.getFullAXTree');
          const current=ax.nodes.filter(n=>n.backendDOMNodeId===node.backendDOMNodeId&&!n.ignored);
          focus={child:actual,dom:await domFacts(objectId),ax:current.map(summary)};
          if(actual.present&&actual.item.activeFocus===true&&focus.dom.focused&&
            current.length===1&&property(current[0],'focused')===true){
            await retain(stage+'-focused',focus);
            return {backendDOMNodeId:node.backendDOMNodeId,nodeId:node.nodeId,objectId};
          }
          await frame();
        }while(Date.now()<deadline);
        await retain(stage+'-focus-refusal',focus);
        assert.fail('DOM focus, actual child native activeFocus and AX focused must agree within the same45s gate');
      }
      await frame();
    }while(Date.now()<deadline);
    await retain(stage+'-button-refusal',last);
    assert.fail('The actual available Fit must expose one AX Button at its own rectangle, not a generic role');
  };
  const retired=async(stage,previous)=>{
    await noActions(stage+'-unavailable');
    const deadline=Date.now()+45000;
    let last;
    do{
      const tree=await send('Accessibility.getFullAXTree');
      const stale=tree.nodes.filter(n=>!n.ignored&&n.backendDOMNodeId===previous.backendDOMNodeId);
      const dom=await domFacts(previous.objectId);
      last={stale:stale.map(summary),dom};
      assert.equal(stale.length,0,'The previously active AX action is no longer exposed after real project close');
      if(!dom.connected){await retain(stage+'-retired',last);return;}
      await frame();
    }while(Date.now()<deadline);
    await retain(stage+'-retirement-refusal',last);
    assert.fail('Ordinary Qt retirement must remove the retained old DOM representation without forced GC/destruction');
  };
  return {noActions,live,retired};
}
