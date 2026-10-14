// SPDX-License-Identifier: BSD-3-Clause
// CPU observer of the actual emitted shared-site mesh and legend. The vector
// operations are their closed-form definitions; no renderer output supplies values.
class Vector {
    constructor(x=0,y=0,z=0) { this.x=x;this.y=y;this.z=z; }
    fromArray(a) { [this.x,this.y,this.z]=a; return this; }
    copy(v) { return this.fromArray(v.toArray()); }
    clone() { return new Vector(this.x,this.y,this.z); }
    toArray() { return [this.x,this.y,this.z]; }
    multiplyScalar(k) { this.x*=k;this.y*=k;this.z*=k;return this; }
    add(v) { return this.addScaledVector(v,1); }
    addScaledVector(v,k) { this.x+=v.x*k;this.y+=v.y*k;this.z+=v.z*k;return this; }
    normalize() { return this.multiplyScalar(1/Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)); }
    crossVectors(a,b) { return this.fromArray([a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x]); }
}
class Colour {
    set(hex) {
        const channels=[1,3,5].map(at=>parseInt(hex.slice(at,at+2),16)/255);
        [this.r,this.g,this.b]=channels.map(v=>v<=0.04045?v/12.92:Math.pow((v+0.055)/1.055,2.4));
    }
}
class Geometry {
    constructor() { this.attributes={}; }
    setAttribute(key,value) { this.attributes[key]=value; }
    setIndex(values) { this.indices=values; }
}
const THREE={Vector3:Vector,Color:Colour,BufferGeometry:Geometry,
    Float32BufferAttribute:class { constructor(values,size) { this.values=Array.from(new Float32Array(values));this.size=size; } },
    Mesh:class { constructor(geometry,material) { this.geometry=geometry;this.material=material; } }};
const scene={frame:{view_direction:[0,0,1],view_up:[0,1,0]},
    atoms:[{centre:[1,2,3],radius:2.7,parts:[{fraction:0.25,color:'#ff0000'},{fraction:0.75,color:'#0000ff'},{fraction:0,color:'#00ff00'}]}],
    legend:[{element:'red',color:'#ff0000'},{element:'blue',color:'#0000ff'}]};
const wedgeMaterial={};
const document={createElement:kind=>({kind,children:[],style:{},append(...items){this.children.push(...items)},appendChild(item){this.children.push(item)}})};
const figure=document.createElement('div');
/* ACTUAL_SHARED_SITE_FUNCTION */
const mesh=sharedSites([0]);
/* ACTUAL_LEGEND */
JSON.stringify({positions:mesh.geometry.attributes.position.values,normals:mesh.geometry.attributes.normal.values,
    colours:mesh.geometry.attributes.color.values,indices:mesh.geometry.indices,
    legend:figure.children[0].children.map(row=>({color:row.children[0].style.background,text:row.children[1]}))});
