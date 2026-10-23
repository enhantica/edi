const fs=require('fs'),vm=require('vm');
const source=fs.readFileSync(process.argv[2],'utf8');
const trace=kind=>({kind,pane:'main',id:kind,label:kind,style:kind==='background'?'bkg':'structure.0',x:[40,52,64],y:[6,6,6],bar_low:[],bar_high:[]});
const model={pattern_styles:[{key:'bkg',light:'#8a8a8a',width_px:1,mark:'line+dash'},{key:'structure.0',light:'#d26e3c',width_px:1.5,mark:'line+fill'}],experiments:[{pattern:{series:[trace('background'),trace('structure')],legend:true,layout:[{pane:'main',stretch:1,fixed_px:0}],x:{title:'2θ',min:40,max:64},y_main:{title:'counts',min:0,max:40,segments:[]},excluded:[],hover:[]}}]};
const figure={dataset:{index:'0'},clientHeight:400};
let captured;
const context={document:{getElementById:()=>({textContent:JSON.stringify(model)}),querySelectorAll:selector=>selector==='.pattern-figure'?[figure]:[]},window:{Plotly:{newPlot:(figure,traces,layout)=>{captured={traces,layout};}}},console};
vm.runInNewContext(source,context,{timeout:1000});
process.stdout.write(JSON.stringify(captured));
