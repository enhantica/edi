.pragma library

// These checks consume displayed text, never the Report model or native factors.
function field(text, key) {
    const names = {rint: "r[ _-]*\\(?int\\)?", rsigma: "r[ _-]*\\(?(?:sigma|σ)\\)?",
        measured:"measured", unique:"unique", used:"used", excluded:"excluded", absent:"absent",
        mode:"merge(?:[ _-]*mode)?"};
    const clean = String(text).replace(/<[^>]*>/g," ").replace(/&sigma;/gi,"σ").replace(/&nbsp;/gi," ");
    const pattern = new RegExp("(?:^|[^a-z])"+names[key]+"(?:\\s+reflections)?\\s*[:=]?\\s*(—|undefined|none|point[ _-]group|laue[ _-]class|[-+]?\\d+(?:\\.\\d+)?(?:e[-+]?\\d+)?\\s*%?)", "i");
    const match=clean.match(pattern);
    return match ? match[1].trim() : null;
}
function problem(text, expected) {
    for (const key of ["measured","unique","used","excluded","absent","mode","rint","rsigma"]) {
        const token=field(text,key);
        if (token===null) return "missing displayed "+key;
        if (key==="mode") {
            if(token.toLowerCase().replace(/[ -]/g,"_")!==expected[key]) return "wrong displayed mode";
        } else if(expected[key]===null) {
            if(!/^(—|undefined)$/.test(token)) return "wrong undefined state for "+key;
        } else if(key==="rint" || key==="rsigma") {
            const percent=/%/.test(token), value=parseFloat(token)/(percent?100:1);
            const numeric=token.replace(/\s*%/,""), mantissa=numeric.split(/e/i)[0];
            const decimals=mantissa.includes(".") ? mantissa.split(".")[1].length : 0;
            const exponent=numeric.includes("e") ? parseInt(numeric.split(/e/i)[1]) : 0;
            const rounding=Math.min(0.005,0.50001*Math.pow(10,exponent-decimals)/(percent?100:1));
            if(!isFinite(value) || Math.abs(value-expected[key])>rounding) return "wrong displayed "+key;
        } else if(Number(token)!==expected[key]) return "wrong displayed "+key;
    }
    return "";
}
function render(expected) {
    return ["measured","unique","used","excluded","absent","mode","rint","rsigma"].map(key =>
        (key==="mode"?"Merge":key)+": "+(expected[key]===null?"—":expected[key])).join("\n");
}
