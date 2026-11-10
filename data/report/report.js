// SPDX-License-Identifier: BSD-3-Clause
// The HTML report's figures (edi ADR-0036): each experiment's pattern as a plotly.js chart and each structure as a
// three.js scene, from the report model in this page. The series, panes, error bars, ticks, colours, instances and
// views all come from the model; this file only places them.

// Decode only the native renderer-number transport; original raw model nulls remain null.
const model = JSON.parse(document.getElementById('edi-report-model').textContent, (_key, value) =>
  value !== null && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 1
    && Object.prototype.hasOwnProperty.call(value, 'edi_renderer_number')
    && typeof value.edi_renderer_number === 'string'
    && (value.edi_renderer_number === 'NaN' || value.edi_renderer_number === 'Infinity' || value.edi_renderer_number === '-Infinity')
    ? Number(value.edi_renderer_number) : value);
// A value of the page's stylesheet; empty where no stylesheet is computed, and the chart keeps plotly's own.
const pageStyle = name =>
  typeof getComputedStyle === 'function' ? getComputedStyle(document.documentElement).getPropertyValue(name).trim() : '';


// The Structure page's and the pattern chart's toolbar icons: Font Awesome Free 5 solid glyphs as SVG paths, [width, height, path] (icons CC
// BY 4.0, https://fontawesome.com/license/free).
const ICONS = {
  'long-arrow-alt-up': [256, 512,
    'M88.0 166.05859375V468.0C88.0 474.626953125 93.373046875 480.0 100.0 480.0H156.0C162.626953125 480.0' +
    ' 168.0 474.626953125 168.0 468.0V166.05859375H214.05859375C235.44140625 166.05859375 246.1494140625 ' +
    '140.2080078125 231.0302734375 125.087890625L144.970703125 39.029296875C135.59765625 29.65625 ' +
    '120.40234375 29.65625 111.0302734375 39.029296875L24.970703125 125.087890625C9.8515625 140.20703125 ' +
    '20.5595703125 166.05859375 41.9423828125 166.05859375Z'],
  'cube': [512, 512,
    'M239.099609375 6.2998046875 31.099609375 84.2998046875C12.400390625 91.2998046875 0.0 109.2998046875' +
    ' 0.0 129.2998046875V354.400390625C0.0 372.599609375 10.2998046875 389.2001953125 26.5 ' +
    '397.2998046875L234.5 501.2998046875C248.0 508.099609375 263.900390625 508.099609375 277.400390625 ' +
    '501.2998046875L485.400390625 397.2998046875C501.7001953125 389.2001953125 511.900390625 372.5 ' +
    '511.900390625 354.400390625V129.2998046875C511.900390625 109.2998046875 499.5 91.400390625 ' +
    '480.7998046875 84.400390625L272.7998046875 6.400390625C262.0 2.2001953125 250.0 2.2001953125 ' +
    '239.099609375 6.2998046875ZM256.0 68.400390625 448.0 140.400390625V141.5L256.0 219.5L64.0 ' +
    '141.5V140.400390625ZM288.0 424.400390625V275.5L448.0 210.5V344.400390625Z'],
  'atom': [448, 512,
    'M223.9990234375 224.0C206.341796875 224.00390625 192.0068359375 238.341796875 192.0068359375 256.0' +
    'C192.0068359375 273.6611328125 206.345703125 288.0 224.0068359375 288.0C241.66796875 288.0' +
    ' 256.0068359375 273.6611328125 256.0068359375 256.0C255.9716796875 238.3525390625 241.6474609375' +
    ' 224.03125 223.9990234375 224.0ZM438.1708984375 128.0C427.2939453125 108.5 397.6611328125 77.25' +
    ' 321.8955078125 86.125C300.3916015625 34.875 267.6337890625 0.0 223.9990234375 0.0C180.3642578125' +
    ' 0.0 147.6083984375 34.875 126.1025390625 86.125C50.3369140625 77.375 20.7060546875 108.5' +
    ' 9.8291015625 128.0C-6.5498046875 157.375 -5.1748046875 201.125 34.9580078125 256.0C-5.1748046875' +
    ' 310.875 -6.5498046875 354.625 9.8291015625 384.0C38.9599609375 436.375 111.4755859375 427.625' +
    ' 126.1025390625 425.875C147.6083984375 477.125 180.3642578125 512.0 223.9990234375 512.0' +
    'C267.6337890625 512.0 300.3916015625 477.125 321.8955078125 425.875C336.5244140625 427.625' +
    ' 409.0400390625 436.375 438.1708984375 384.0C454.5498046875 354.625 453.1748046875 310.875' +
    ' 413.0400390625 256.0C453.1748046875 201.125 454.5498046875 157.375 438.1708984375 128.0Z' +
    'M63.3388671875 352.0C59.3388671875 344.75 63.2138671875 327.25 78.3427734375 303.75C85.2197265625' +
    ' 310.25 92.4716796875 316.625 100.2236328125 322.875C101.8486328125 336.625 104.2236328125 350.0' +
    ' 106.9736328125 363.0C82.3447265625 363.875 67.0908203125 358.625 63.3388671875 352.0Z' +
    'M100.2236328125 189.125C92.4716796875 195.375 85.2197265625 201.75 78.3427734375 208.25' +
    'C63.2138671875 184.75 59.3388671875 167.25 63.3388671875 160.0C66.7158203125 153.875 79.7177734375' +
    ' 148.5 101.2236328125 148.5C102.9736328125 148.5 105.0986328125 148.875 106.9736328125 148.875' +
    'C104.0986328125 162.25 101.8486328125 175.625 100.2236328125 189.125ZM223.9990234375 64.0' +
    'C233.5009765625 64.0 246.2548828125 77.5 257.8818359375 101.25C246.6298828125 105.0 235.3779296875' +
    ' 109.25 223.9990234375 114.125C212.6220703125 109.25 201.3701171875 105.0 190.1162109375 101.25' +
    'C201.7451171875 77.5 214.4970703125 64.0 223.9990234375 64.0ZM223.9990234375 448.0C214.4970703125' +
    ' 448.0 201.7451171875 434.5 190.1162109375 410.75C201.3701171875 407.0 212.6220703125 402.75' +
    ' 223.9990234375 397.875C235.3779296875 402.75 246.6298828125 407.0 257.8818359375 410.75' +
    'C246.2548828125 434.5 233.5009765625 448.0 223.9990234375 448.0ZM223.9990234375 336.0C179.845703125' +
    ' 336.0 143.9990234375 300.1533203125 143.9990234375 256.0C143.9990234375 211.8466796875' +
    ' 179.845703125 176.0 223.9990234375 176.0C268.15234375 176.0 303.9990234375 211.8466796875' +
    ' 303.9990234375 256.0C303.9990234375 300.1533203125 268.15234375 336.0 223.9990234375 336.0Z' +
    'M384.6591796875 352.0C381.0341796875 358.625 365.6552734375 363.875 341.0244140625 363.0' +
    'C343.7763671875 350.0 346.1513671875 336.625 347.7763671875 322.875C355.5283203125 316.625' +
    ' 362.7802734375 310.25 369.6552734375 303.75C384.7841796875 327.25 388.6591796875 344.75' +
    ' 384.6591796875 352.0ZM369.6552734375 208.25C362.7802734375 201.75 355.5283203125 195.375' +
    ' 347.7763671875 189.125C346.1513671875 175.625 343.9013671875 162.25 341.0244140625 148.875' +
    'C342.8994140625 148.875 345.0263671875 148.5 346.7763671875 148.5C368.2802734375 148.5' +
    ' 381.2841796875 153.875 384.6591796875 160.0C388.6591796875 167.25 384.7841796875 184.75' +
    ' 369.6552734375 208.25Z'],
  'tag': [512, 512,
    'M0.0 252.1181640625C0.0 265.3642578125 5.3701171875 277.3701171875 14.05859375 286.05859375' +
    'L225.94140625 497.94140625C244.685546875 516.685546875 275.078125 516.685546875 293.8232421875' +
    ' 497.94140625L497.94140625 293.8232421875C516.685546875 275.078125 516.685546875 244.685546875' +
    ' 497.94140625 225.94140625L286.05859375 14.05859375C277.3701171875 5.3701171875 265.3642578125 0.0' +
    ' 252.1181640625 0.0H48.0C21.490234375 0.0 0.0 21.490234375 0.0 48.0ZM112.0 64.0C138.509765625 64.0' +
    ' 160.0 85.490234375 160.0 112.0C160.0 138.509765625 138.509765625 160.0 112.0 160.0C85.490234375' +
    ' 160.0 64.0 138.509765625 64.0 112.0C64.0 85.490234375 85.490234375 64.0 112.0 64.0Z'],
  'link': [512, 512,
    'M326.6123046875 185.390625C320.2607421875 179.0390625 313.4755859375 173.3515625 306.08984375' +
    ' 168.1943359375C299.6884765625 163.7255859375 291.02734375 164.404296875 285.505859375' +
    ' 169.9248046875L264.4521484375 190.98046875C256.1015625 199.330078125 252.3583984375 210.21875' +
    ' 252.75390625 220.7861328125C252.9541015625 226.017578125 255.650390625 230.6103515625' +
    ' 259.701171875 233.3916015625C262.61328125 235.3974609375 266.3408203125 238.2666015625' +
    ' 270.0419921875 241.9609375C298.115234375 270.0341796875 298.2333984375 315.599609375' +
    ' 270.0419921875 343.791015625L202.841796875 410.9814453125C174.6025390625 439.2197265625' +
    ' 128.541015625 439.0498046875 100.5166015625 410.470703125C72.7666015625 382.1708984375' +
    ' 73.646484375 336.537109375 101.671875 308.5107421875L114.7587890625 295.423828125C119.109375' +
    ' 291.07421875 120.5283203125 284.6337890625 118.5419921875 278.8115234375C112.677734375' +
    ' 261.6181640625 109.5 243.8134765625 108.8515625 226.0908203125C108.34375 212.1845703125 91.3984375' +
    ' 205.64453125 81.5576171875 215.4853515625L44.4521484375 252.5908203125C-14.818359375' +
    ' 311.8505859375 -14.818359375 408.291015625 44.4521484375 467.55078125C103.712890625 526.8134765625' +
    ' 200.1416015625 526.8212890625 259.412109375 467.55078125L326.6123046875 400.3505859375' +
    'C326.732421875 400.2314453125 326.8623046875 400.1005859375 326.9716796875 399.9814453125' +
    'C385.5390625 341.0888671875 386.359375 245.2001953125 326.6123046875 185.390625ZM467.546875' +
    ' 44.44921875C408.2861328125 -14.8134765625 311.857421875 -14.8212890625 252.5869140625 44.44921875' +
    'L185.38671875 111.6494140625C185.2666015625 111.7685546875 185.13671875 111.8994140625 185.02734375' +
    ' 112.0185546875C126.4609375 170.9111328125 125.6396484375 266.7998046875 185.38671875 326.609375' +
    'C191.73828125 332.9599609375 198.5224609375 338.6484375 205.908203125 343.8046875C212.3095703125' +
    ' 348.2734375 220.9716796875 347.59375 226.4921875 342.07421875L247.5458984375 321.0185546875' +
    'C255.896484375 312.6689453125 259.6396484375 301.7802734375 259.244140625 291.212890625' +
    'C259.0439453125 285.9814453125 256.34765625 281.388671875 252.296875 278.607421875C249.384765625' +
    ' 276.6015625 245.6572265625 273.732421875 241.9560546875 270.0380859375C213.8828125 241.96484375' +
    ' 213.7646484375 196.3994140625 241.9560546875 168.2080078125L309.15625 101.017578125C337.39453125' +
    ' 72.779296875 383.4560546875 72.94921875 411.4814453125 101.5283203125C439.2314453125 129.828125' +
    ' 438.3525390625 175.4619140625 410.326171875 203.48828125L397.2392578125 216.5751953125' +
    'C392.888671875 220.9248046875 391.4697265625 227.365234375 393.4560546875 233.1865234375' +
    'C399.3203125 250.380859375 402.498046875 268.185546875 403.146484375 285.908203125C403.6552734375' +
    ' 299.814453125 420.599609375 306.353515625 430.4404296875 296.513671875L467.5458984375' +
    ' 259.408203125C526.8173828125 200.1494140625 526.8173828125 103.708984375 467.546875 44.44921875Z'],
  'vector-square': [512, 512,
    'M512 128V32C512.0 14.330078125 497.669921875 0.0 480.0 0.0H384.0C366.330078125 0.0 352.0' +
    ' 14.330078125 352.0 32.0H160.0C160.0 14.330078125 145.669921875 0.0 128.0 0.0H32.0C14.330078125 0.0' +
    ' 0.0 14.330078125 0.0 32.0V128.0C0.0 145.669921875 14.330078125 160.0 32.0 160.0V352.0C14.330078125' +
    ' 352.0 0.0 366.330078125 0.0 384.0V480.0C0.0 497.669921875 14.330078125 512.0 32.0 512.0H128.0' +
    'C145.669921875 512.0 160.0 497.669921875 160.0 480.0H352.0C352.0 497.669921875 366.330078125 512.0' +
    ' 384.0 512.0H480.0C497.669921875 512.0 512.0 497.669921875 512.0 480.0V384.0C512.0 366.330078125' +
    ' 497.669921875 352.0 480.0 352.0V160.0C497.669921875 160.0 512.0 145.669921875 512.0 128.0ZM416.0' +
    ' 64.0H448.0V96.0H416.0ZM64.0 64.0H96.0V96.0H64.0ZM96.0 448.0H64.0V416.0H96.0ZM448.0 448.0H416.0' +
    'V416.0H448.0ZM416.0 352.0H384.0C366.330078125 352.0 352.0 366.330078125 352.0 384.0V416.0H160.0' +
    'V384.0C160.0 366.330078125 145.669921875 352.0 128.0 352.0H96.0V160.0H128.0C145.669921875 160.0' +
    ' 160.0 145.669921875 160.0 128.0V96.0H352.0V128.0C352.0 145.669921875 366.330078125 160.0 384.0' +
    ' 160.0H416.0Z'],
  'location-arrow': [512, 512,
    'M444.51953125 3.51953125 28.740234375 195.419921875C-19.23046875 217.8095703125 -3.240234375' +
    ' 288.169921875 47.9296875 288.169921875H223.83984375V464.080078125C223.83984375 515.25' +
    ' 294.2001953125 531.25 316.58984375 483.26953125L508.490234375 67.490234375C524.48046875' +
    ' 29.099609375 482.900390625 -12.48046875 444.51953125 3.51953125Z'],
  'home': [576, 512,
    'M280.3701171875 148.259765625 96.0 300.1103515625V464.0C96.0 472.8310546875 103.1689453125 480.0' +
    ' 112.0 480.0L224.0595703125 479.7099609375C232.853515625 479.666015625 239.98046875 472.513671875' +
    ' 239.98046875 463.7099609375V368.0C239.98046875 359.1689453125 247.1494140625 352.0 255.98046875' +
    ' 352.0H319.98046875C328.810546875 352.0 335.98046875 359.1689453125 335.98046875 368.0' +
    'V463.6396484375C335.9794921875 463.6572265625 335.9794921875 463.673828125 335.9794921875' +
    ' 463.69140625C335.9794921875 472.521484375 343.1494140625 479.6904296875 351.98046875' +
    ' 479.6904296875L464.0 480.0C472.8310546875 480.0 480.0 472.8310546875 480.0 464.0V300.0' +
    'L295.669921875 148.259765625C293.5791015625 146.57421875 290.9208984375 145.5654296875' +
    ' 288.0283203125 145.5654296875C285.1357421875 145.5654296875 282.4609375 146.57421875' +
    ' 280.3701171875 148.259765625ZM571.599609375 251.4697265625 488.0 182.5595703125V44.0498046875' +
    'C488.0 37.4267578125 482.623046875 32.0498046875 476.0 32.0498046875H420.0C413.376953125' +
    ' 32.0498046875 408.0 37.4267578125 408.0 44.0498046875V116.66015625L318.4697265625 43.0C310.1796875' +
    ' 36.177734375 299.5654296875 32.0791015625 288.0009765625 32.0791015625C276.4365234375' +
    ' 32.0791015625 265.7607421875 36.177734375 257.4697265625 43.0L4.33984375 251.4697265625C1.67578125' +
    ' 253.671875 -0.0224609375 257.0009765625 -0.0224609375 260.7236328125C-0.0224609375 263.6259765625' +
    ' 1.021484375 266.2939453125 2.740234375 268.3701171875L28.240234375 299.3701171875C30.44140625' +
    ' 302.046875 33.779296875 303.755859375 37.51171875 303.755859375C40.4111328125 303.755859375' +
    ' 43.0751953125 302.7138671875 45.150390625 301.0L280.3701171875 107.259765625C282.4609375' +
    ' 105.57421875 285.119140625 104.5654296875 288.01171875 104.5654296875C290.9033203125' +
    ' 104.5654296875 293.5791015625 105.57421875 295.669921875 107.259765625L530.900390625 301.0' +
    'C532.9765625 302.7177734375 535.6396484375 303.7509765625 538.54296875 303.7509765625C542.265625' +
    ' 303.7509765625 545.5986328125 302.0634765625 547.7998046875 299.400390625L573.2998046875' +
    ' 268.400390625C575.0029296875 266.328125 576.025390625 263.6767578125 576.025390625 260.7880859375' +
    'C576.025390625 257.03125 574.306640625 253.6708984375 571.599609375 251.4697265625Z'],
  'camera': [512, 512,
    'M512 144C512.0 117.5 490.5 96.0 464.0 96.0H376.0L363.599609375 63.099609375C356.599609375' +
    ' 44.400390625 338.7001953125 32.0 318.7001953125 32.0H193.2001953125C173.2001953125 32.0' +
    ' 155.2998046875 44.400390625 148.2998046875 63.099609375L136.0 96.0H48.0C21.5 96.0 0.0 117.5 0.0' +
    ' 144.0V432.0C0.0 458.5 21.5 480.0 48.0 480.0H464.0C490.5 480.0 512.0 458.5 512.0 432.0ZM376.0 288.0' +
    'C376.0 354.2001953125 322.2001953125 408.0 256.0 408.0C189.7998046875 408.0 136.0 354.2001953125' +
    ' 136.0 288.0C136.0 221.7998046875 189.7998046875 168.0 256.0 168.0C322.2001953125 168.0 376.0' +
    ' 221.7998046875 376.0 288.0ZM344.0 288.0C344.0 239.5 304.5 200.0 256.0 200.0C207.5 200.0 168.0' +
    ' 239.5 168.0 288.0C168.0 336.5 207.5 376.0 256.0 376.0C304.5 376.0 344.0 336.5 344.0 288.0Z'],
  'align-left': [448, 512,
    'M12.830078125 352.0H275.169921875H275.1806640625C282.255859375 352.0 288.0 346.255859375 288.0' +
    ' 339.1796875V339.169921875V300.830078125V300.8193359375C288.0 293.744140625 282.255859375 288.0' +
    ' 275.1796875 288.0H275.169921875H12.830078125H12.8193359375C5.744140625 288.0 0.0 293.744140625' +
    ' 0.0 300.8203125V300.830078125V339.169921875V339.1806640625C0.0 346.255859375 5.744140625 352.0' +
    ' 12.8203125 352.0ZM12.830078125 96.0H275.169921875H275.1806640625C282.255859375 96.0 288.0' +
    ' 90.255859375 288.0 83.1796875V83.169921875V44.830078125V44.8193359375C288.0 37.744140625' +
    ' 282.255859375 32.0 275.1796875 32.0H275.169921875H12.830078125H12.8193359375C5.744140625 32.0' +
    ' 0.0 37.744140625 0.0 44.8203125V44.830078125V83.169921875V83.1806640625C0.0 90.255859375' +
    ' 5.744140625 96.0 12.8203125 96.0ZM432.0 160.0H16.0C7.1689453125 160.0 0.0 167.1689453125 0.0' +
    ' 176.0V208.0C0.0 216.8310546875 7.1689453125 224.0 16.0 224.0H432.0C440.8310546875 224.0 448.0' +
    ' 216.8310546875 448.0 208.0V176.0C448.0 167.1689453125 440.8310546875 160.0 432.0 160.0ZM432.0' +
    ' 416.0H16.0C7.1689453125 416.0 0.0 423.1689453125 0.0 432.0V464.0C0.0 472.8310546875' +
    ' 7.1689453125 480.0 16.0 480.0H432.0C440.8310546875 480.0 448.0 472.8310546875 448.0 464.0V432.0' +
    'C448.0 423.1689453125 440.8310546875 416.0 432.0 416.0Z'],
  'comment-alt': [512, 512,
    'M448 0H64C28.7001953125 0.0 0.0 28.7001953125 0.0 64.0V352.0C0.0 387.2998046875 28.7001953125' +
    ' 416.0 64.0 416.0H160.0V500.0C160.0 509.7998046875 171.2001953125 515.5 179.099609375' +
    ' 509.7001953125L304.0 416.0H448.0C483.2998046875 416.0 512.0 387.2998046875 512.0 352.0V64.0' +
    'C512.0 28.7001953125 483.2998046875 0.0 448.0 0.0Z'],
  'layer-group': [512, 512,
    'M12.41015625 148.01953125 245.349609375 253.6904296875C252.150390625 256.7802734375 259.83984375' +
    ' 256.7802734375 266.6396484375 253.6904296875L499.580078125 148.01953125C516.1298828125' +
    ' 140.509765625 516.1298828125 115.5 499.580078125 107.990234375L266.650390625 2.3095703125' +
    'C263.4130859375 0.830078125 259.8154296875 0.005859375 256.0263671875 0.005859375C252.2373046875' +
    ' 0.005859375 248.5966796875 0.830078125 245.3603515625 2.3095703125L12.41015625 107.98046875' +
    'C-4.1396484375 115.490234375 -4.1396484375 140.509765625 12.41015625 148.01953125ZM499.58984375' +
    ' 236.2998046875 441.5 209.9697265625 279.8603515625 283.240234375C272.2998046875 286.669921875' +
    ' 264.26953125 288.41015625 256.0 288.41015625C247.73046875 288.41015625 239.7099609375' +
    ' 286.669921875 232.1396484375 283.240234375L70.509765625 209.9697265625L12.41015625' +
    ' 236.2998046875C-4.1396484375 243.7998046875 -4.1396484375 268.7998046875 12.41015625' +
    ' 276.2998046875L245.349609375 381.8896484375C252.150390625 384.9697265625 259.83984375' +
    ' 384.9697265625 266.6396484375 381.8896484375L499.58984375 276.2998046875C516.1396484375' +
    ' 268.7998046875 516.1396484375 243.7998046875 499.58984375 236.2998046875ZM499.58984375' +
    ' 364.099609375 441.7197265625 337.8701171875 279.8603515625 411.240234375C272.2998046875' +
    ' 414.669921875 264.26953125 416.41015625 256.0 416.41015625C247.73046875 416.41015625' +
    ' 239.7099609375 414.669921875 232.1396484375 411.240234375L70.2900390625 337.8701171875' +
    'L12.41015625 364.099609375C-4.1396484375 371.599609375 -4.1396484375 396.599609375 12.41015625' +
    ' 404.099609375L245.349609375 509.6904296875C252.150390625 512.76953125 259.83984375 512.76953125' +
    ' 266.6396484375 509.6904296875L499.58984375 404.099609375C516.1396484375 396.599609375' +
    ' 516.1396484375 371.599609375 499.58984375 364.099609375Z'],
  'eraser': [512, 512,
    'M497.94140625 273.94140625C516.685546875 255.1962890625 516.685546875 224.8037109375' +
    ' 497.94140625 206.05859375L337.94140625 46.05859375C319.1962890625 27.314453125 288.8046875' +
    ' 27.3134765625 270.0576171875 46.05859375L14.0576171875 302.05859375C-4.6865234375' +
    ' 320.8037109375 -4.6865234375 351.1962890625 14.0576171875 369.94140625L110.0576171875' +
    ' 465.94140625C118.7470703125 474.6298828125 130.75390625 480.0 144.0 480.0H500.0C506.626953125' +
    ' 480.0 512.0 474.626953125 512.0 468.0V428.0C512.0 421.373046875 506.626953125 416.0 500.0 416.0' +
    'H355.8828125ZM195.314453125 211.314453125 332.6865234375 348.6865234375 265.373046875 416.0' +
    'H150.6279296875L70.6279296875 336.0Z'],
  'chart-area': [512, 512,
    'M500 384H64V76C64.0 69.400390625 58.599609375 64.0 52.0 64.0H12.0C5.400390625 64.0 0.0' +
    ' 69.400390625 0.0 76.0V436.0C0.0 442.599609375 5.400390625 448.0 12.0 448.0H500.0C506.599609375' +
    ' 448.0 512.0 442.599609375 512.0 436.0V396.0C512.0 389.400390625 506.599609375 384.0 500.0 384.0' +
    'ZM372.7001953125 159.5 288.0 216.0 202.7001953125 102.2998046875C197.599609375 95.5' +
    ' 187.2001953125 96.0 182.7998046875 103.2998046875L96.0 248.0V352.0H480.0L390.099609375' +
    ' 164.2001953125C386.900390625 157.7001953125 378.7001953125 155.5 372.7001953125 159.5Z'],
  'arrows-alt': [512, 512,
    'M352.201171875 425.775390625C367.3203125 410.6552734375 356.6123046875 384.8037109375' +
    ' 335.23046875 384.8037109375H284.0V284.0H384.802734375V335.228515625C384.8017578125' +
    ' 356.611328125 410.654296875 367.3193359375 425.7734375 352.2001953125L504.96875 273.00390625' +
    'C514.341796875 263.6318359375 514.341796875 248.435546875 504.96875 239.0634765625L425.7734375' +
    ' 159.8671875C410.654296875 144.748046875 384.802734375 155.4560546875 384.802734375' +
    ' 176.837890625V228.0H283.9990234375V127.1962890625H335.1611328125C356.54296875 127.1962890625' +
    ' 367.2509765625 101.34375 352.1318359375 86.224609375L272.935546875 7.029296875C263.5634765625' +
    ' -2.34375 248.3681640625 -2.34375 238.9951171875 7.029296875L159.798828125 86.224609375' +
    'C144.6796875 101.3447265625 155.3876953125 127.1962890625 176.76953125 127.1962890625H228.0' +
    'V228.0H127.1962890625V176.771484375C127.1962890625 155.388671875 101.34375 144.6806640625' +
    ' 86.224609375 159.7998046875L7.029296875 238.99609375C-2.34375 248.3681640625 -2.34375' +
    ' 263.564453125 7.029296875 272.9365234375L86.224609375 352.1328125C101.3447265625 367.251953125' +
    ' 127.1962890625 356.5439453125 127.1962890625 335.162109375V284.0H228.0L228.0009765625' +
    ' 384.8046875H176.8388671875C155.45703125 384.8037109375 144.7490234375 410.65625 159.8681640625' +
    ' 425.775390625L239.064453125 504.970703125C248.4365234375 514.34375 263.6318359375 514.34375' +
    ' 273.0048828125 504.970703125Z'],
  'expand': [448, 512,
    'M0 180C0.0 186.599609375 5.400390625 192.0 12.0 192.0H52.0C58.599609375 192.0 64.0 186.599609375' +
    ' 64.0 180.0V96.0H148.0C154.599609375 96.0 160.0 90.599609375 160.0 84.0V44.0C160.0 37.400390625' +
    ' 154.599609375 32.0 148.0 32.0H24.0C10.7001953125 32.0 0.0 42.7001953125 0.0 56.0ZM288.0 44.0' +
    'V84.0C288.0 90.599609375 293.400390625 96.0 300.0 96.0H384.0V180.0C384.0 186.599609375' +
    ' 389.400390625 192.0 396.0 192.0H436.0C442.599609375 192.0 448.0 186.599609375 448.0 180.0V56.0' +
    'C448.0 42.7001953125 437.2998046875 32.0 424.0 32.0H300.0C293.400390625 32.0 288.0 37.400390625' +
    ' 288.0 44.0ZM436.0 320.0H396.0C389.400390625 320.0 384.0 325.400390625 384.0 332.0V416.0H300.0' +
    'C293.400390625 416.0 288.0 421.400390625 288.0 428.0V468.0C288.0 474.599609375 293.400390625' +
    ' 480.0 300.0 480.0H424.0C437.2998046875 480.0 448.0 469.2998046875 448.0 456.0V332.0C448.0' +
    ' 325.400390625 442.599609375 320.0 436.0 320.0ZM160.0 468.0V428.0C160.0 421.400390625' +
    ' 154.599609375 416.0 148.0 416.0H64.0V332.0C64.0 325.400390625 58.599609375 320.0 52.0 320.0' +
    'H12.0C5.400390625 320.0 0.0 325.400390625 0.0 332.0V456.0C0.0 469.2998046875 10.7001953125 480.0' +
    ' 24.0 480.0H148.0C154.599609375 480.0 160.0 474.599609375 160.0 468.0Z'],
};

// A figure that cannot be drawn says why.
function notice(figure, text) {
  figure.classList?.add('figure-note');
  figure.textContent = text;
}

// --- The pattern charts (edi ADR-0021) ---

// Each pane's y domain, top to bottom: a fixed pane takes its pixels of the plot's height, a stretching one its share
// of what the fixed panes and the gaps between the panes leave.
function paneDomains(layout, plotHeight, fixed, gap) {
  const between = gap * Math.max(0, layout.length - 1);
  const rest = Math.max(0, 1 - (fixed + between) / plotHeight);
  const domains = {};
  let top = 1;
  for (const pane of layout) {
    const share = pane.fixed_px > 0 ? pane.fixed_px / plotHeight : pane.stretch * rest;
    domains[pane.pane] = [Math.max(0, top - share), top];
    top -= share + gap / plotHeight;
  }
  return domains;
}

// The chart's x range: the pattern's own, or the range a notebook view zooms to (edi ADR-0079).
function xRange(figure, pattern) {
  const zoom = figure.dataset ?? {};
  const low = zoom.xMin === undefined ? pattern.x.min : Number(zoom.xMin);
  const high = zoom.xMax === undefined ? pattern.x.max : Number(zoom.xMax);
  return [low, high];
}

// Portable trace, colour, label and bar projections come from the native report writer.
function drawPattern(figure, pattern) {
  if (!window.Plotly) {
    notice(figure, 'The chart needs plotly.js, which could not be loaded.');
    return;
  }
  if (pattern.series.length === 0) {
    notice(figure, 'No pattern to show');
    return;
  }
  const font = pageStyle('--head-font');
  // A light grid, a frame a little darker than the grid (lighter than the tables' border), no zero lines.
  const grid = pageStyle('--chartgrid');
  const frame = pageStyle('--chartframe');
  // The toolbar (patternToolbar) sits above the plot's top right, clear of the legend.
  const margin = { l: 16, r: 16, t: 48, b: 16 };
  // As the app draws it: the panes one em apart, each framed on its four sides, the x labels and title under the
  // lowest one only.
  const gap = parseFloat(getComputedStyle(figure).fontSize) || 16;
  const plotHeight = figure.clientHeight - margin.t - margin.b;
  const domains = paneDomains(pattern.layout, plotHeight, pattern.browser.fixed_height, gap);
  const bottom = pattern.browser.bottom_axis;
  const axis = { automargin: true, showline: true, mirror: true, linecolor: frame, gridcolor: grid, zeroline: false };
  // Runtime CSS font decoration belongs to the browser renderer.
  const annotations = pattern.browser.annotations;
  for (const annotation of annotations) annotation.font = { family: font };
  const layout = {
    height: figure.clientHeight,
    margin,
    font: { family: font, color: pageStyle('--chart-ink') || undefined },
    // The model says whether a legend is drawn; without one the y titles name the series in their colours.
    showlegend: pattern.legend,
    legend: { x: 1, xanchor: 'right', y: 1, yanchor: 'top', bgcolor: 'rgba(255,255,255,0.8)' },
    hovermode: 'closest',
    // Box zoom on at the start, as the app's toolbar has it.
    dragmode: 'zoom',
    // The experiment's reliability in its last fit, above the plot's top left, as the app's selector shows it.
    annotations,
    yaxis: { ...axis, title: { text: pattern.browser.main_title }, domain: domains.main ?? [0, 1] },
    shapes: [],
  };
  if ('bragg' in domains) {
    const rows = pattern.browser.bragg_rows;
    layout.yaxis2 = {
      ...axis,
      domain: domains.bragg,
      range: [0, rows],
      showticklabels: false,
      showgrid: false,
      fixedrange: true,
    };
  }
  if ('residual' in domains) {
    layout.yaxis3 = { ...axis, title: { text: pattern.browser.residual_title }, domain: domains.residual };
  }
  // One x axis per pane, all showing one range; pane y, y2, y3 draws on x, x2, x3.
  const panes = ['y', 'y2', 'y3'].filter(y => layout[y.replace('y', 'yaxis')]);
  for (const y of panes) {
    const x = y.replace('y', 'x');
    const shown = y === bottom;
    layout[x.replace('x', 'xaxis')] = {
      ...axis,
      anchor: y,
      range: xRange(figure, pattern),
      ...(x === 'x' ? {} : { matches: 'x' }),
      showticklabels: shown,
      // The tick rows have no grid, as in the app.
      showgrid: y !== 'y2',
      ...(shown ? { title: { text: pattern.x.title } } : {}),
    };
    // An excluded region is a band in each pane, never across the gaps between them.
    for (const shape of pattern.browser.shapes) layout.shapes.push({ ...shape, xref: x, yref: `${y} domain` });
  }
  // A trace on another's grid names it (x_from); a structure's fill closes back along its lower edge (fill_back), which
  // may be another trace's curve (fill_back_from).
  const sent = pattern.browser.traces;
  const traces = sent.map(({ x_from: from, fill_back: back, fill_back_from: backFrom, ...trace }) => {
    const x = from === undefined ? trace.x : sent[from].x;
    const lower = backFrom === undefined ? back : sent[backFrom].y;
    return {
      ...trace,
      x: lower ? [...x, ...x.slice().reverse()] : x,
      y: lower ? [...trace.y, ...lower.slice().reverse()] : trace.y,
      xaxis: (trace.yaxis ?? 'y').replace('y', 'x'),
    };
  });
  const kinds = pattern.series.map(series => series.kind);
  // The app's read-out box of each measured point and tick, from the model's `hover` (hover_readout): lines by '\n',
  // each line's coloured pieces by '\x1e', each piece `<style key>\t<text>`.
  const colours = pattern.browser.readout_colours ?? {};
  const escape = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const readout = encoded => encoded.split('\n').map(line => line.split('\x1e').map(piece => {
    const [key, text] = piece.includes('\t') ? piece.split('\t') : ['', piece];
    return key ? `<span style="color:${colours[key]}">${escape(text)}</span>` : escape(text);
  }).join('')).join('<br>');
  // A series' read-outs come whole, or as their shared wording and a column per value, null where a point has none
  // (browser_readouts).
  const whole = hover => Array.isArray(hover) ? hover : hover.values[0].map((first, point) => first === null ? '' :
    hover.parts.reduce((text, part, k) => text + hover.values[k - 1][point] + part));
  (pattern.hover ?? []).map(whole).forEach((texts, i) => {
    if (texts.length && traces[i]) traces[i].text = texts.map(readout);
  });
  // The residual's point shows its measured point's read-out, as the app's residual pane does.
  const measured = kinds.indexOf('measured');
  const residual = kinds.indexOf('residual');
  if (measured >= 0 && residual >= 0 && traces[measured].text?.length === traces[residual].x.length) {
    traces[residual].text = traces[measured].text;
    traces[residual].hovertemplate = '%{text}<extra></extra>';
  }
  // The app's read-out box: light, framed in the grid's colour, the theme's text colour.
  layout.hoverlabel = { bgcolor: 'rgba(255,255,255,0.9)', bordercolor: frame, font: { family: font, color: '#000' },
    align: 'left' };
  // Each structure's curve starts hidden; the toolbar shows it.
  kinds.forEach((kind, i) => { if (kind === 'structure') traces[i].visible = false; });
  // The tick rows' labels are drawn by the page (patternLabels), with the structure's icon.
  const labels = layout.annotations.filter(annotation => annotation.yref === 'y2');
  layout.annotations = layout.annotations.filter(annotation => annotation.yref !== 'y2');
  window.Plotly.newPlot(figure, traces, layout, { responsive: true, displaylogo: false, displayModeBar: false });
  const toolbar = patternToolbar(figure, pattern, traces, layout);
  const place = patternLabels(figure, labels);
  figure.on?.('plotly_afterplot', () => { place(); alignPattern(figure, toolbar); });
  place();
  alignPattern(figure, toolbar);
}

// The tick rows' labels as the app writes them: the structure's icon and name in its colour, right of each row's
// label column, centred on the row.
function patternLabels(figure, labels) {
  const items = labels.map(label => {
    const element = document.createElement('div');
    element.className = 'pattern-row-label';
    const [width, height, path] = ICONS['layer-group'];
    element.innerHTML = `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true"><path d="${path}"/></svg>${label.text}`;
    const colour = /color:([^;"]+)/.exec(label.text)?.[1];
    if (colour) element.style.color = colour;
    figure.appendChild(element);
    return { element, centre: label.y };
  });
  return () => {
    const size = figure._fullLayout?._size;
    const axis = figure._fullLayout?.yaxis2;
    if (!size || !axis) return;
    for (const { element, centre } of items) {
      const [low, high] = axis.range;
      const top = axis._offset + axis._length * (1 - (centre - low) / (high - low));
      element.style.right = `${figure.clientWidth - size.l + 6}px`;
      element.style.top = `${top}px`;
    }
  };
}

// After each drawing: the toolbar's right edge on the plot's right frame line, and the y titles one gap from their
// tick numbers, the same on every pane so the titles line up.
function alignPattern(figure, toolbar) {
  const layout = figure._fullLayout;
  if (!layout?._size) return;
  if (toolbar) toolbar.style.right = `${layout._size.r}px`;
  const GAP = 10;
  const widths = {};
  for (const name of ['y', 'y3']) {
    const ticks = figure.querySelectorAll(`.${name}tick text`);
    widths[name] = Math.max(0, ...[...ticks].map(text => text.getBBox?.().width ?? 0));
  }
  const widest = Math.max(widths.y, widths.y3 ?? 0);
  const update = {};
  for (const name of ['y', 'y3']) {
    const axis = layout[name.replace('y', 'yaxis')];
    if (!axis?.title?.text) continue;
    const standoff = Math.round(GAP + widest - widths[name]);
    if (axis.title.standoff !== standoff) update[`${name.replace('y', 'yaxis')}.title.standoff`] = standoff;
  }
  if (Object.keys(update).length) window.Plotly.relayout(figure, update);
}

// Linear interpolation of the curve (xs, ys) at x; NaN outside it.
function interpolate(xs, ys, x) {
  let high = xs.findIndex(value => value >= x);
  if (high < 0) return NaN;
  if (xs[high] === x || high === 0) return xs[high] === x ? ys[high] : NaN;
  const low = high - 1;
  return ys[low] + ((ys[high] - ys[low]) * (x - xs[low])) / (xs[high] - xs[low]);
}

// The pattern chart's toolbar, as the app's (app/qml/Components/ChartToolbar.qml): the legend, the coordinates on
// hover, each structure's curve, only the included range, the background subtracted, a gap, pan, box zoom and reset.
// Every button works on the data in the page.
function patternToolbar(figure, pattern, traces, layout) {
  const kinds = pattern.series.map(series => series.kind);
  const original = traces.map(trace => trace.y.slice());
  const background = kinds.indexOf('background');
  const bands = pattern.browser.shapes.map(shape => [shape.x0, shape.x1]);
  const excluded = x => bands.some(([low, high]) => x > low && x < high);
  const fullRange = xRange(figure, pattern);
  // The included range: the data's range less the excluded regions at its ends.
  const includedRange = () => {
    let [low, high] = [pattern.x.min, pattern.x.max];
    for (const [start, end] of [...bands].sort((a, b) => a[0] - b[0])) if (start <= low && end > low) low = end;
    for (const [start, end] of [...bands].sort((a, b) => b[1] - a[1])) if (end >= high && start < high) high = start;
    return [low, high];
  };
  const state = { legend: layout.showlegend, hover: true, curves: false, included: false, subtract: false, mode: 'zoom' };
  const curvesAvailable = kinds.includes('structure');
  const backgroundAvailable = background >= 0;

  // The curves as the switches ask: each structure's curve shown or not, the measured points in the excluded regions
  // left out for the included range only, and every curve but the residual less the background.
  const redraw = () => {
    const bkg = backgroundAvailable ? traces[background] : null;
    const y = traces.map((trace, i) => {
      const kind = kinds[i];
      const values = original[i].slice();
      if (state.included && kind === 'measured') {
        trace.x.forEach((x, j) => { if (excluded(x)) values[j] = NaN; });
      }
      if (state.subtract && bkg && ['measured', 'calculated', 'background', 'structure'].includes(kind)) {
        trace.x.forEach((x, j) => {
          const base = trace.x === bkg.x ? original[background][j] : interpolate(bkg.x, original[background], x);
          values[j] = values[j] - base;
        });
      }
      return values;
    });
    const visible = kinds.map(kind => (kind === 'structure' ? state.curves : true));
    window.Plotly.restyle(figure, { y, visible });
    window.Plotly.relayout(figure, { 'yaxis.autorange': true });
  };
  const reset = () => {
    const [low, high] = state.included ? includedRange() : fullRange;
    window.Plotly.relayout(figure, { 'xaxis.range': [low, high], 'yaxis.autorange': true, 'yaxis3.autorange': true });
  };

  const toolbar = document.createElement('div');
  toolbar.className = 'viewer-toolbar';
  const buttons = [];
  const add = (icon, title, onClick, pressed) => {
    const element = button(icon, typeof title === 'function' ? title() : title, () => { onClick(); refresh(); });
    buttons.push({ element, title, pressed });
    toolbar.appendChild(element);
    return element;
  };
  const refresh = () => {
    for (const { element, title, pressed } of buttons) {
      if (pressed) element.setAttribute('aria-pressed', String(pressed()));
      element.title = typeof title === 'function' ? title() : title;
    }
  };
  if (pattern.legend !== undefined) {
    add('align-left', () => (state.legend ? 'Hide legend' : 'Show legend'), () => {
      state.legend = !state.legend;
      window.Plotly.relayout(figure, { showlegend: state.legend });
    }, () => state.legend);
  }
  add('comment-alt', 'Show coordinates tooltip on hover', () => {
    state.hover = !state.hover;
    window.Plotly.relayout(figure, { hovermode: state.hover ? 'closest' : false });
  }, () => state.hover);
  if (curvesAvailable) {
    add('layer-group', "Show each structure's curve", () => { state.curves = !state.curves; redraw(); }, () => state.curves);
  }
  add('eraser', 'Show only the included range', () => {
    state.included = !state.included;
    redraw();
    reset();
  }, () => state.included);
  const subtract = add('chart-area',
    () => (backgroundAvailable ? 'Subtract the background' : 'Subtract the background: this pattern has no background set'),
    () => { if (backgroundAvailable) { state.subtract = !state.subtract; redraw(); } },
    () => state.subtract && backgroundAvailable);
  subtract.disabled = !backgroundAvailable;
  const gap = document.createElement('span');
  gap.className = 'gap';
  toolbar.appendChild(gap);
  const mode = name => () => { state.mode = name; window.Plotly.relayout(figure, { dragmode: name }); };
  add('arrows-alt', 'Enable pan', mode('pan'), () => state.mode === 'pan');
  add('expand', 'Enable box zoom', mode('zoom'), () => state.mode === 'zoom');
  add('home', 'Reset axes', reset);
  const last = document.createElement('span');
  last.className = 'gap';
  toolbar.appendChild(last);
  add('camera', 'Save image', () => window.Plotly.downloadImage(figure, { format: 'png', filename: 'pattern' }));
  figure.appendChild(toolbar);
  refresh();
  if (curvesAvailable) redraw();
  return toolbar;
}

// A single crystal's chart (edi ADR-0049), as the app draws it: each reflection's F²meas with its s.u. bar against its
// F²calc, the y = x line a perfect model puts them on, one range on both axes; "Not calculated yet" before a
// calculation.
function drawSingleCrystal(figure, crystal) {
  if (!window.Plotly) {
    notice(figure, 'The chart needs plotly.js, which could not be loaded.');
    return;
  }
  if (crystal.calc.length === 0) {
    notice(figure, 'Not calculated yet');
    return;
  }
  const font = pageStyle('--head-font');
  const grid = pageStyle('--chartgrid');
  const frame = pageStyle('--chartframe');
  const range = crystal.browser.range;
  const axis = { automargin: true, showline: true, mirror: true, linecolor: frame, gridcolor: grid, zeroline: false, range };
  const points = {
    type: 'scatter',
    mode: 'markers',
    name: crystal.name,
    x: crystal.calc,
    y: crystal.meas,
    error_y: { type: 'data', array: crystal.su, visible: true, thickness: 1, width: 0, color: crystal.browser.color },
    // Each point's hover as the core writes it: its indices and values by the dictionary's labels and formats.
    text: crystal.hover,
    hovertemplate: '%{text}<extra></extra>',
    marker: { color: crystal.browser.color, size: 5 },
  };
  const diagonal = {
    type: 'scatter',
    mode: 'lines',
    x: range,
    y: range,
    hoverinfo: 'skip',
    line: { color: frame, width: 1 },
  };
  const layout = {
    height: figure.clientHeight,
    margin: { l: 16, r: 16, t: 36, b: 16 },
    font: { family: font, color: pageStyle('--chart-ink') || undefined },
    showlegend: false,
    hovermode: 'closest',
    annotations: crystal.title
      ? [{ text: crystal.title, xref: 'paper', yref: 'paper', x: 0, y: 1, xanchor: 'left', yanchor: 'bottom',
           showarrow: false, font: { family: font, color: pageStyle('--chart-ink') || undefined } }]
      : [],
    xaxis: { ...axis, title: { text: crystal.x_title } },
    yaxis: { ...axis, title: { text: crystal.y_title } },
  };
  window.Plotly.newPlot(figure, [diagonal, points], layout, { responsive: true, displaylogo: false, modeBarButtons: MODEBAR });
}

// One of a scan's evolution charts (edi ADR-0036): a parameter at each fitted dataset with its s.u. as an error bar,
// titled with its name and units; "No fitted results yet" before any dataset is fitted.
function drawEvolution(figure, series) {
  const font = pageStyle('--head-font');
  const grid = pageStyle('--chartgrid');
  const frame = pageStyle('--chartframe');
  const axis = { automargin: true, showline: true, mirror: true, linecolor: frame, gridcolor: grid, zeroline: false };
  if (series.points.length === 0) {
    notice(figure, 'No fitted results yet');
    return;
  }
  if (!window.Plotly) {
    notice(figure, 'The chart needs plotly.js, which could not be loaded.');
    return;
  }
  const trace = {
    // Points with their s.u. bars and no line, as the Evolution tab draws them.
    type: 'scatter',
    mode: 'markers',
    name: series.name,
    x: series.browser.x,
    y: series.browser.y,
    error_y: { type: 'data', array: series.browser.su, visible: true, thickness: 1, color: series.browser.color },
    text: series.browser.text,
    hovertemplate: '%{x}: %{text}<extra></extra>',
    marker: { color: series.browser.color, size: 6 },
  };
  const layout = {
    height: figure.clientHeight,
    // The toolbar stands at the right, clear of the title.
    margin: { l: 16, r: 40, t: 40, b: 16 },
    modebar: { orientation: 'v' },
    font: { family: font, color: pageStyle('--chart-ink') || undefined },
    title: { text: series.browser.title, x: 0.02, xanchor: 'left' },
    showlegend: false,
    hovermode: 'closest',
    xaxis: { ...axis, title: { text: series.x_title } },
    yaxis: { ...axis },
  };
  window.Plotly.newPlot(figure, [trace], layout, { responsive: true, displaylogo: false, modeBarButtons: MODEBAR });
}

// --- The structure views (edi ADR-0022) ---

// Save image: the file a browser downloads.
function saveBlob(blob, name) {
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = name;
  link.click();
  URL.revokeObjectURL(link.href);
}

// A Plotly chart's buttons with Save image last, in its own group, as on every chart of the app.
const MODEBAR = [['zoom2d', 'pan2d', 'autoScale2d', 'resetScale2d'], ['toImage']];

// A toolbar button with an icon (or a letter), its tooltip, and whether it is on.
function button(icon, title, onClick) {
  const element = document.createElement('button');
  element.type = 'button';
  element.className = 'viewer-button';
  element.dataset.icon = icon;
  element.title = title;
  if (ICONS[icon]) {
    const [width, height, path] = ICONS[icon];
    element.innerHTML = `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true"><path d="${path}"/></svg>`;
  } else {
    element.textContent = icon;
  }
  element.addEventListener('click', onClick);
  return element;
}

async function drawStructure(figure, structure) {
  // three.js as the page provides it: already loaded, else imported through the page's import map.
  let THREE, OrbitControls;
  try {
    THREE = globalThis.THREE ?? (await import('three'));
    OrbitControls =
      globalThis.OrbitControls ?? (await import('three/addons/controls/OrbitControls.js')).OrbitControls;
  } catch {
    notice(figure, 'The structure view needs three.js, which could not be loaded.');
    return;
  }
  const { scene, view, drawing } = structure;
  if (structure.browser.empty) {
    notice(figure, 'No structure to show');
    return;
  }
  const sceneStyle = key => structure.browser.styles[key] ?? {};
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setClearColor(sceneStyle('background').light);
  figure.appendChild(renderer.domElement);
  const world = new THREE.Scene();
  const value = key => sceneStyle(key).value;
  const material = new THREE.MeshPhongMaterial({
    specular: new THREE.Color().setScalar(value('material.specular')),
    shininess: value('material.shininess'),
  });
  const sphere = new THREE.SphereGeometry(1, 32, 16);
  const cylinder = new THREE.CylinderGeometry(1, 1, 1, 16);

  // What the toolbar shows, as the app's Structure view (StructureToolbar.qml): the colour scheme, the atoms (all, the
  // asymmetric unit, for a magnetic structure its magnetic atoms and their asymmetric unit, or none), the labels, the
  // bonds, the cell, the magnetic moments and the axes.
  const shown = {
    scheme: structure.browser.schemes[0].token, atoms: 'all', labels: false, bonds: true, cell: true, moments: true,
    axes: true,
  };
  const currentSubset = () => structure.browser.variants[shown.scheme][shown.atoms];

  // The drawing's instances on unit meshes: a sphere of radius 1, a cylinder of radius 1 and length 1 along +y. The
  // model's quaternions are w, x, y, z; three.js takes x, y, z, w.
  const instanced = (geometry, instances) => {
    const mesh = new THREE.InstancedMesh(geometry, material, Math.max(1, instances.length));
    mesh.count = instances.length;
    const matrix = new THREE.Matrix4();
    const position = new THREE.Vector3();
    const rotation = new THREE.Quaternion();
    const scale = new THREE.Vector3();
    const colour = new THREE.Color();
    instances.forEach((item, i) => {
      const [w, x, y, z] = item.rotation;
      matrix.compose(position.fromArray(item.position), rotation.set(x, y, z, w), scale.fromArray(item.scale));
      mesh.setMatrixAt(i, matrix);
      mesh.setColorAt(i, colour.set(item.color));
    });
    return mesh;
  };
  // The sites several atoms share, as the app draws them: each site's sphere cut into wedges about the home view's
  // direction, each wedge its part's fraction of the turn in the part's colour, the first starting at the plane through
  // that direction and the home view's up. A part of fraction 0 has no wedge.
  const wedgeMaterial = material.clone();
  wedgeMaterial.vertexColors = true;
  const sharedSites = mesh => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(mesh.positions, 3));
    geometry.setAttribute('normal', new THREE.Float32BufferAttribute(mesh.normals, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(mesh.colours, 3));
    geometry.setIndex(mesh.indices);
    return new THREE.Mesh(geometry, wedgeMaterial);
  };
  // The cylinders are the half-bonds, two per bond in the scene's order, then the cell edges.
  let meshes = new THREE.Group();
  const place = () => {
    world.remove(meshes);
    meshes = new THREE.Group();
    const subset = currentSubset();
    meshes.add(instanced(sphere, subset.spheres));
    meshes.add(sharedSites(subset.shared));
    const bonds = shown.bonds ? subset.bonds : [];
    meshes.add(instanced(cylinder, bonds));
    meshes.add(instanced(cylinder, shown.cell ? structure.browser.cell : []));
    if (shown.moments) {
      for (const arrow of subset.moments) meshes.add(arrowMesh(arrow));
    }
    triad.visible = shown.axes;
    world.add(meshes);
    drawLegend(subset.legend);
  };

  // An arrow as the core places it: a shaft and a head along its direction from its origin. The axes and the magnetic
  // moments (edi ADR-0078) are drawn alike.
  const up = new THREE.Vector3(0, 1, 0);
  const cone = new THREE.ConeGeometry(1, 1, 24);
  const arrowMesh = arrow => {
    const direction = new THREE.Vector3().fromArray(arrow.direction).normalize();
    const turn = new THREE.Quaternion().setFromUnitVectors(up, direction);
    const ink = new THREE.MeshPhongMaterial({ color: arrow.color });
    const origin = new THREE.Vector3().fromArray(arrow.origin);
    const shaft = new THREE.Mesh(cylinder, ink);
    shaft.position.copy(origin).addScaledVector(direction, arrow.shaft_length / 2);
    shaft.quaternion.copy(turn);
    shaft.scale.set(arrow.shaft_radius, arrow.shaft_length, arrow.shaft_radius);
    const head = new THREE.Mesh(cone, ink);
    head.position.copy(origin).addScaledVector(direction, arrow.shaft_length + arrow.head_length / 2);
    head.quaternion.copy(turn);
    head.scale.set(arrow.head_radius, arrow.head_length, arrow.head_radius);
    return new THREE.Group().add(shaft, head);
  };
  // The axis arrows, the letter beside each head.
  const triad = new THREE.Group();
  const overlay = [];
  for (const arrow of drawing.triad) {
    triad.add(arrowMesh(arrow));
    const letter = document.createElement('div');
    letter.className = 'axis-letter';
    letter.style.color = arrow.color;
    letter.textContent = arrow.letter;
    figure.appendChild(letter);
    overlay.push({ element: letter, at: new THREE.Vector3().fromArray(arrow.letter_anchor), show: () => shown.axes });
  }
  world.add(triad);
  // The atom labels, shown when asked for.
  for (const [labelIndex, label] of structure.labels.entries()) {
    const element = document.createElement('div');
    element.className = 'atom-label';
    element.style.color = sceneStyle('label').light;
    element.textContent = label.text;
    figure.appendChild(element);
    const at = new THREE.Vector3().fromArray(label.anchor);
    overlay.push({ element, at, show: () => shown.labels && currentSubset().labels[labelIndex] });
  }

  // The element legend, each element with the atom icon the app's legend shows, in the scheme's colour.
  const legend = document.createElement('div');
  legend.className = 'structure-legend';
  figure.appendChild(legend);
  const drawLegend = entries => {
    legend.replaceChildren();
    const [width, height, path] = ICONS.atom;
    for (const entry of entries) {
      const row = document.createElement('div');
      const mark = document.createElement('span');
      mark.className = 'atom-mark';
      mark.innerHTML = `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true"><path d="${path}"/></svg>`;
      mark.style.color = entry.color;
      row.append(mark, entry.element);
      legend.appendChild(row);
    }
    legend.style.display = entries.length ? '' : 'none';
  };

  // The view: an orthographic camera looking along a view's direction at the frame's target, its half height the
  // fitted one at the view's magnification. The lights follow the camera.
  const target = new THREE.Vector3().fromArray(scene.frame.target);
  const distance = 4 * (drawing.fitted_half_height + scene.frame.half_width + scene.frame.pad);
  // The projection button swaps it for a perspective camera at the same place, the same height in view at the target.
  const parallel = new THREE.OrthographicCamera(-1, 1, 1, -1, distance / 100, 3 * distance);
  const perspective = new THREE.PerspectiveCamera(30, 1, distance / 100, 3 * distance);
  let camera = parallel;
  world.add(new THREE.AmbientLight(0xffffff, value('light.ambient')));
  const lights = [];
  for (const name of ['key', 'fill']) {
    const light = new THREE.DirectionalLight(0xffffff, value(`light.${name}`));
    light.position.set(value(`light.${name}.right`), value(`light.${name}.up`), value(`light.${name}.toward`));
    lights.push(light, light.target);
  }
  camera.add(...lights);
  world.add(parallel, perspective);
  const controls = new OrbitControls(camera, renderer.domElement);
  let halfHeight = 1;

  const render = () => {
    renderer.render(world, camera);
    const size = renderer.getSize(new THREE.Vector2());
    for (const item of overlay) {
      const at = item.at.clone().project(camera);
      item.element.style.display = item.show() ? '' : 'none';
      item.element.style.left = `${((at.x + 1) / 2) * size.x}px`;
      item.element.style.top = `${((1 - at.y) / 2) * size.y}px`;
    }
  };
  const fit = () => {
    const width = figure.clientWidth;
    const height = figure.clientHeight;
    renderer.setSize(width, height);
    const aspect = width / height;
    parallel.left = -halfHeight * aspect;
    parallel.right = halfHeight * aspect;
    parallel.top = halfHeight;
    parallel.bottom = -halfHeight;
    parallel.updateProjectionMatrix();
    perspective.aspect = aspect;
    perspective.fov = (2 * Math.atan(halfHeight / distance) * 180) / Math.PI;
    perspective.updateProjectionMatrix();
    render();
  };
  const toggleProjection = () => {
    const next = camera === parallel ? perspective : parallel;
    next.position.copy(camera.position);
    next.quaternion.copy(camera.quaternion);
    next.up.copy(camera.up);
    next.zoom = camera.zoom;
    next.add(...lights);
    camera = next;
    controls.object = camera;
    controls.update();
    fit();
  };
  // The home view and the views along a, b and c are the core's (default_view, view_along).
  const look = chosen => {
    halfHeight = drawing.fitted_half_height / chosen.magnification;
    camera.zoom = 1;
    camera.position.copy(target).addScaledVector(new THREE.Vector3().fromArray(chosen.direction).normalize(), distance);
    camera.up.fromArray(chosen.up);
    camera.lookAt(target);
    controls.target.copy(target);
    controls.update();
    fit();
  };

  // The toolbar, as the app's Structure view (StructureToolbar.qml): the colour scheme and the atoms, then labels,
  // bonds, cell, magnetic moments and axes; then the projection, the views along a, b and c and home; then Save image.
  const toolbar = document.createElement('div');
  toolbar.className = 'viewer-toolbar';
  const toggles = [];
  const group = () => {
    const gap = document.createElement('span');
    gap.className = 'gap';
    toolbar.appendChild(gap);
  };
  const choose = (title, options, key) => {
    const select = document.createElement('select');
    select.title = title(options.find(option => option.token === shown[key]));
    select.setAttribute('aria-label', title(options[0]).split(':')[0]);
    for (const option of options) {
      const item = document.createElement('option');
      item.value = option.token;
      item.textContent = option.short ?? option.name;
      item.title = option.name;
      select.appendChild(item);
    }
    select.value = shown[key];
    select.addEventListener('change', () => {
      shown[key] = select.value;
      select.title = title(options.find(option => option.token === select.value));
      refresh();
    });
    toolbar.appendChild(select);
  };
  const toggle = (icon, title, key) => {
    const element = button(icon, title, () => {
      shown[key] = !shown[key];
      refresh();
    });
    toggles.push({ element, on: () => shown[key] });
    toolbar.appendChild(element);
  };
  const features = structure.browser.controls;
  choose(option => `Colour scheme: ${option.name}`, structure.browser.schemes, 'scheme');
  if (features.atoms) {
    choose(option => `Atoms: ${option.name}`, structure.browser.atoms, 'atoms');
    if (features.labels) toggle('tag', 'Labels', 'labels');
    if (features.bonds) toggle('link', 'Bonds', 'bonds');
  }
  toggle('vector-square', 'Cell', 'cell');
  if (features.moments) toggle('long-arrow-alt-up', 'Magnetic moments', 'moments');
  toggle('location-arrow', 'Axes', 'axes');
  group();
  const projection = button('cube', 'Parallel (orthographic) view', () => {
    toggleProjection();
    projection.title = camera === perspective ? 'Perspective view' : 'Parallel (orthographic) view';
  });
  toolbar.appendChild(projection);
  ['a', 'b', 'c'].forEach((name, axis) => {
    const element = button(name, `View along ${name}`, () => look(structure.along[axis]));
    element.classList.add('axis-button');
    element.style.color = sceneStyle(`axis.${name}`).light;
    toolbar.appendChild(element);
  });
  toolbar.appendChild(button('home', 'Reset view', () => look(view)));
  group();
  toolbar.appendChild(button('camera', 'Save image', () => {
    render();
    renderer.domElement.toBlob(blob => saveBlob(blob, `${structure.id}.png`));
  }));
  figure.appendChild(toolbar);

  const refresh = () => {
    for (const item of toggles) {
      item.element.setAttribute('aria-pressed', String(item.on()));
    }
    place();
    render();
  };
  controls.addEventListener('change', render);
  new ResizeObserver(fit).observe(figure);
  refresh();
  look(view);
}

for (const figure of document.querySelectorAll('.pattern-figure')) {
  const experiment = model.experiments?.[Number(figure.dataset.index)];
  if (experiment?.single_crystal) {
    drawSingleCrystal(figure, experiment.single_crystal);
  } else if (experiment) {
    drawPattern(figure, experiment.pattern);
  }
}
for (const figure of document.querySelectorAll('.structure-figure')) {
  const structure = model.structures?.[Number(figure.dataset.index)];
  if (structure) {
    drawStructure(figure, structure);
  }
}
const evolution = model.evolution ?? [];
if (evolution.length > 0) {
  for (const figure of document.querySelectorAll('.evolution-figure')) {
    const series = evolution[Number(figure.dataset.index)];
    if (series) drawEvolution(figure, series);
  }
}
