.pragma library

function levelKey(preferences) {
    const keys = Object.keys(preferences).filter(key => /^tooltips?level$/i.test(key));
    if (keys.length !== 1) throw new Error("Preferences must expose one tooltip level");
    return keys[0];
}
function level(preferences) { return preferences[levelKey(preferences)]; }
function setLevel(preferences, value) { preferences[levelKey(preferences)] = value; }
