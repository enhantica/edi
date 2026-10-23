.pragma library
// Ottosson's independent 2020/2021 matrices, also frozen in approved_palettes/reference.py.
function multiply(matrix, values) { return matrix.map(row => row.reduce((sum, coefficient, i) => sum + coefficient * values[i], 0)); }
function lab(colour) {
    const linear = [1,3,5].map(i => parseInt(colour.slice(i,i+2),16)/255).map(v => v <= 0.04045 ? v/12.92 : Math.pow((v+0.055)/1.055,2.4));
    const lms = multiply([[0.4122214708,0.5363325363,0.0514459929],[0.2119034982,0.6806995451,0.1073969566],[0.0883024619,0.2817188376,0.6299787005]],linear);
    return multiply([[0.2104542553,0.7936177850,-0.0040720468],[1.9779984951,-2.4285922050,0.4505937099],[0.0259040371,0.7827717662,-0.8086757660]],lms.map(Math.cbrt));
}
function gradient(first, second, t) {
    if (t === 0) return first.toLowerCase();
    if (t === 1) return second.toLowerCase();
    const a=lab(first), b=lab(second), mixed=a.map((v,i) => v+(b[i]-v)*t);
    const lms = multiply([[1,0.3963377774,0.2158037573],[1,-0.1055613458,-0.0638541728],[1,-0.0894841775,-1.2914855480]],mixed);
    const rgb = multiply([[4.0767416621,-3.3077115913,0.2309699292],[-1.2684380046,2.6097574011,-0.3413193965],[-0.0041960863,-0.7034186147,1.7076147010]],lms.map(v => v*v*v));
    return '#' + rgb.map(v => v <= 0.0031308 ? 12.92*v : 1.055*Math.pow(v,1/2.4)-0.055).map(v => ('0' + Math.floor(Math.min(1,Math.max(0,v))*255+0.5).toString(16)).slice(-2)).join('');
}
