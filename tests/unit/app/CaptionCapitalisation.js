.pragma library

// Match a complete symbol token, so e.g. "d spacing" passes and "description" fails.
const symbol = /^(2θ|TOF|s\.u\.|h k l|μR|σ[₀₁₂]²|x[123]{2}|[abcdfhklqrxyzαβγφθ])(?=$|[\s(:/′])/;

function significant(text) {
    return symbol.test(text);
}

function expected(text) {
    if (significant(text))
        return text;
    for (let i = 0; i < text.length; ++i) {
        if (text[i].toLowerCase() !== text[i].toUpperCase())
            return text.slice(0, i) + text[i].toUpperCase() + text.slice(i + 1);
    }
    return text;
}
