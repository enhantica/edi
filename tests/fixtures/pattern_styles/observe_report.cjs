const fs=require('fs');
const trace=kind=>({kind,pane:'main',id:kind,label:kind,style:kind==='background'?'bkg':'structure.0',x:[40,52,64],y:[6,6,6],bar_low:[],bar_high:[]});
const model={pattern_styles:[{key:'bkg',light:'#8a8a8a',width_px:1,mark:'line+dash'},{key:'structure.0',light:'#d26e3c',width_px:1.5,mark:'line+fill'}],experiments:[{pattern:{series:[trace('background'),trace('structure')],legend:true,layout:[{pane:'main',stretch:1,fixed_px:0}],x:{title:'2θ',min:40,max:64},y_main:{title:'counts',min:0,max:40,segments:[]},excluded:[],hover:[]}}]};
if(process.argv[3]==='--model'){process.stdout.write(JSON.stringify(model));process.exit(0);}
// Use the same browser boundary as the other complete-renderer gates.
const path=require('node:path'),child=require('node:child_process');
const observed=child.spawnSync(process.execPath,[path.resolve(__dirname,'../report_units/observe_renderer.js'),process.argv[2],process.argv[3]],{encoding:'utf8'});
if(observed.status!==0){process.stderr.write(observed.stderr);process.exit(observed.status||1);}
const result=JSON.parse(observed.stdout),plot=result.plots[0];
if(!plot)throw Error('The actual report must deliver its pattern to Plotly');
process.stdout.write(JSON.stringify({traces:plot[1],layout:plot[2]}));
