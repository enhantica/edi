// Parse the tests' JavaScript with the Acorn copy bundled in the pinned Node.
// Native procedures execute in Qt. This file only exposes the original lexical
// fixture bindings to the real QML caller and captures the observer's output.
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(0, 'utf8');
const moduleObject = {exports:{}};
const parser = process.binding('natives')['internal/deps/acorn/acorn/dist/acorn'];
if (typeof parser !== 'string') throw Error('The pinned Node must provide its actual Acorn parser');
vm.runInNewContext(parser, {exports:moduleObject.exports,module:moduleObject});
const ast = moduleObject.exports.parse(source, {ecmaVersion:'latest'});
const edits = [];
const calls = [];
const scopes = [{parent:null, names:new Set(), function:true}];
function names(pattern, found=[]) {
    if (!pattern) return found;
    if (pattern.type === 'Identifier') found.push(pattern.name);
    else if (pattern.type === 'RestElement') names(pattern.argument, found);
    else if (pattern.type === 'AssignmentPattern') names(pattern.left, found);
    else if (pattern.type === 'ArrayPattern') for (const item of pattern.elements) names(item,found);
    else if (pattern.type === 'ObjectPattern') for (const item of pattern.properties) names(item.type === 'RestElement' ? item.argument : item.value,found);
    return found;
}
function walk(node, scope) {
    if (!node || typeof node !== 'object' || !node.type) return;
    if (node.type === 'FunctionDeclaration' && node.id) scope.names.add(node.id.name);
    let own = scope;
    if (/^(FunctionDeclaration|FunctionExpression|ArrowFunctionExpression)$/.test(node.type)) {
        own = {parent:scope,names:new Set(),function:true};scopes.push(own);
        for (const param of node.params) for (const name of names(param)) own.names.add(name);
        if (node.type === 'FunctionExpression' && node.id) own.names.add(node.id.name);
    } else if (/^(BlockStatement|ForStatement|ForOfStatement|ForInStatement|CatchClause)$/.test(node.type)) {
        own = {parent:scope,names:new Set(),function:false};scopes.push(own);
        if (node.type === 'CatchClause') for (const name of names(node.param)) own.names.add(name);
    }
    if (node.type === 'WithStatement') {
        if (node.object.type !== 'Identifier') throw Error('A wiring fixture with-scope must name its original context object');
        own={parent:scope,names:new Set(),function:false,withObject:source.slice(node.object.start,node.object.end)};scopes.push(own);
        walk(node.object,scope);walk(node.body,own);return;
    }
    if (node.type === 'VariableDeclaration') {
        let holder = own;
        if (node.kind === 'var') while (!holder.function) holder = holder.parent;
        for (const item of node.declarations) for (const name of names(item.id)) holder.names.add(name);
    }
    if (node.type === 'ClassDeclaration' && node.id) own.names.add(node.id.name);
    if (node.type === 'CallExpression' && node.callee.type === 'MemberExpression' && node.callee.object.type === 'Identifier') {
        if (node.callee.object.name === 'ApplicationInfo' || (node.callee.object.name === '__nativeFixture' && node.callee.property.name === 'reportDocument')) calls.push({node,scope:own});
        if (node.callee.object.name === 'console' && node.callee.property.name === 'log') edits.push({at:node.callee.start,end:node.callee.end,text:'__nativeOutput.push'});
    }
    if (node.type === 'CallExpression' && node.callee.type === 'MemberExpression'
        && node.callee.property.name === 'write' && node.callee.object.type === 'MemberExpression'
        && node.callee.object.property.name === 'stdout'
        && node.callee.object.object.type === 'Identifier' && node.callee.object.object.name === 'process') {
        edits.push({at:node.callee.start,end:node.callee.end,text:'__nativeOutput.push'});
    }
    for (const [key,value] of Object.entries(node)) {
        if (['type','start','end','id','params','param'].includes(key)) continue;
        if (Array.isArray(value)) for (const item of value) walk(item,own);
        else if (value && typeof value.type === 'string') walk(value,own);
    }
}
walk(ast,scopes[0]);
if (!calls.length) {
    if (process.argv.includes('--inspect')) { process.stdout.write(JSON.stringify({native:false})); process.exit(0); }
    throw Error('A native witness must reach at least one actual ApplicationInfo operation');
}
for (const {node,scope} of calls) {
    const visible = new Set();
    for (let current=scope;current;current=current.parent) for (const name of current.names) visible.add(name);
    visible.delete('ApplicationInfo');
    const publish = [...visible].filter(n=>!n.startsWith('__native')).map(name=>
        '__nativeFixture.expose('+JSON.stringify(name)+',()=>'+name+',__nativeValue=>{'+name+'=__nativeValue});').join('');
    const scopeObjects=[];
    for(let current=scope;current;current=current.parent) if(current.withObject) scopeObjects.unshift(current.withObject);
    const frames=['this',...scopeObjects].map(object=>'__nativeFixture.exposeScope('+object+','+JSON.stringify([...visible])+');').join('');
    edits.push({at:node.start,end:node.start,text:'(()=>{'+publish+frames+'__nativeInvocations++;return '});
    edits.push({at:node.end,end:node.end,text:';})()'});
}
edits.sort((a,b)=>b.at-a.at || b.end-a.end);
let output = source;
for (const edit of edits) output=output.slice(0,edit.at)+edit.text+output.slice(edit.end);
output='let __nativeInvocations=0;__nativeFixture.expose("__nativeInvocations",()=>__nativeInvocations,v=>{__nativeInvocations=v});\n'+output;
process.stdout.write(process.argv.includes('--inspect') ? JSON.stringify({native:true,program:output}) : output);
