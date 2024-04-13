// Importar js-beautify desde un CDN
// ONE TIME ONLY!!!
//var script = document.createElement('script');
//script.src = 'https://cdn.jsdelivr.net/npm/js-beautify@1.13.5/js/lib/beautify.js';
//document.head.appendChild(script);

/*
// Create the floating box and position text elements
const floatingBox = document.createElement('div');
floatingBox.id = 'floatingBox';
floatingBox.style.position = 'fixed';
floatingBox.style.bottom = '10px';
floatingBox.style.left = '10px';
floatingBox.style.padding = '10px';
floatingBox.style.backgroundColor = '#f0f0f0';
floatingBox.style.border = '1px solid #ccc';
floatingBox.style.borderRadius = '5px';
floatingBox.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.1)';

const positionText = document.createElement('p');
positionText.id = 'positionText';
positionText.textContent = 'Mouse position: (0, 0)';
floatingBox.appendChild(positionText);
document.body.appendChild(floatingBox);

// Update the position text based on mouse movement
document.addEventListener('mousemove', (event) => {
  const x = event.clientX;
  const y = event.clientY;
  positionText.textContent = `Mouse position: (${x}, ${y})`;
});
*/

// Generate a random string of characters
function generateRandomString(length) {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let randomString = '';
    for (let i = 0; i < length; i++) {
        randomString += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return randomString;
}

// Example usage
const session_uuid = generateRandomString(8);


// Define a function to introduce a delay using setTimeout
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


/* GET Timeline bounds. */
const timelineContainer = document.querySelector('div.timeline-container');
const timelineContainerSvg = document.querySelector('div.timeline-container svg');
const timelineRect = timelineContainer.querySelector('rect[pointer-events="all"]')

const gElement = timelineContainerSvg.querySelector('g');
const boundingRect = gElement.getBoundingClientRect();
const position = {
  x: boundingRect.left + window.scrollX,
  y: boundingRect.bottom + window.scrollY
};

const timelineContainerRect = timelineContainer.getBoundingClientRect();
const bottomLeftPosition = {
  x: timelineContainerRect.left + window.scrollX,
  y: timelineContainerRect.bottom + window.scrollY
};

const timelineHeight = timelineContainerRect.height;

const timelineWidth = position.x - bottomLeftPosition.x;

/* GET Timeline KeyFrame data */
const timelineKeys = document.querySelectorAll('div.timeline-key[data-type="key"]:not(svg div.timeline-key[data-type="key"])');
const keyTimes = [];

const keyAttributes = {};
timelineKeys.forEach(key => {
    const dataKeyTime = key.getAttribute('data-keytime');
    if (!keyTimes.includes(dataKeyTime)) {
        keyTimes.push(dataKeyTime);
    }
    const dataFor = key.getAttribute('data-for');
    if (!keyAttributes[dataKeyTime]) {
        keyAttributes[dataKeyTime] = {};
    }
    if (!keyAttributes[dataKeyTime][dataFor]) {
        keyAttributes[dataKeyTime][dataFor] = [];
    }
    keyAttributes[dataKeyTime][dataFor].push([
        key.getAttribute('data-propertygroup'),
        key.getAttribute('data-propertyname')
    ]);
});


/* Simulate Timeline navigation and retrieve SVGs elements */
const typesToFind = ['g', 'path', 'line', 'rect', 'circle'];

function findElementsByType(element, types, result = {}) {
    if (types.includes(element.tagName)) {
      result[element.getAttribute('id')] = element;
    }
    const children = element.children;
    for (let i = 0; i < children.length; i++) {
      findElementsByType(children[i], types, result);
    }
    return result;
}

const svgHolder = document.createElement('div');
svgHolder.style.display = 'none';
document.body.appendChild(svgHolder);

const svgElement = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
svgHolder.appendChild(svgElement);

const totTime = Math.max(...keyTimes);
const keyCount = keyTimes.length;

let svgItemCSSCode = "";
const svgItemCSSKeyframesCode = {};

let elementCount = 1;

const mapElementIds = {};

async function processWithDelay() {
    for (let k = 0; k < keyCount; k++) {
        const keyTime = keyTimes[k];
        const calculatedWidth = Math.round(keyTime / totTime * timelineWidth);
        const percentage = keyTime / totTime * 100;
        // Simular un clic en el punto calculado
        let simulatedClickX = bottomLeftPosition.x + calculatedWidth + 10;
        if (k == (keyCount - 1)) {
            simulatedClickX += 10;
        }
        const simulatedClickY = Math.round(bottomLeftPosition.y - timelineHeight * 0.5); // Puedes ajustar la posición Y según tus necesidades
        // console.log(calculatedWidth, simulatedClickX, simulatedClickY);
        const event = new MouseEvent('click', {
            clientX: simulatedClickX,
            clientY: simulatedClickY,
            bubbles: true,
            cancelable: true
        });

        // const clickedElement = document.elementFromPoint(simulatedClickX, simulatedClickY);
        // if (clickedElement) {
        //     clickedElement.dispatchEvent(event);
        // }
        timelineRect.dispatchEvent(event);
        await delay(1000);

        const elementsWrapper = document.getElementById('elements-wrapper');
        const childElements = elementsWrapper.querySelectorAll('g, path, line, circle, rect'); // Replace with the desired tag names

        // const elementsMap = findElementsByType(elementsWrapper, typesToFind);
        for (let i = 0; i < childElements.length; i++) {
            const element = childElements[i];
            let elementId = element.getAttribute('id');
            if (!elementId) {
                continue;
            }

            if (k == 0 && !mapElementIds[elementId]) {
                const copiedElement = element.cloneNode(true);
                copiedElement.id = `${session_uuid}_${elementCount}_to`;
                if (copiedElement.tagName.toLowerCase() == 'g') {
                    mapElementIds[elementId] = copiedElement.id;
                    copiedElement.querySelectorAll('path, line, circle, rect').forEach(item => {
                        if (item.hasAttribute('id')) {
                            mapElementIds[item.getAttribute('id')] = copiedElement.id;
                            item.removeAttribute('id');
                        }
                    })
                }
                else {
                    mapElementIds[elementId] = newGroupElement.id;
                }
                svgElement.appendChild(copiedElement);
                elementCount += 1;
            }

            /* Method were a super group is created for every element. */
            /*if (k == 0 && !mapElementIds[elementId]) {
                const copiedElement = element.cloneNode(true);
                const newGroupElement = document.createElement('g');
                newGroupElement.id = `${session_uuid}_${elementCount}_to`;
                if (copiedElement.tagName.toLowerCase() == 'g') {
                    copiedElement.id = `${session_uuid}_${elementCount}_ts`;
                    mapElementIds[elementId] = copiedElement.id;
                    copiedElement.querySelectorAll('path, line, circle, rect').forEach(item => {
                        if (item.hasAttribute('id')) {
                            mapElementIds[item.getAttribute('id')] = newGroupElement.id;
                            item.removeAttribute('id');
                        }
                    })
                }
                else {
                    mapElementIds[elementId] = newGroupElement.id;
                    copiedElement.removeAttribute('id');
                }
                newGroupElement.appendChild(copiedElement);
                svgElement.appendChild(newGroupElement);
                elementCount += 1;
            }*/

            elementId = mapElementIds[elementId];
            const elementAnimId = `${elementId}__${elementId.slice(-2)}`;

            // Init data if not exist.
            if (!svgItemCSSKeyframesCode[elementId]) {
                svgItemCSSCode += `
                button:hover #${elementId} {
                    animation: ${elementAnimId} ${totTime}ms linear 1 normal forwards;
                }`;
                svgItemCSSKeyframesCode[elementId] = {
                    'elementAnimId': elementAnimId,
                    'keyframes': []
                }
            }

            if (!keyAttributes[keyTime][elementId]) {
                //console.log("nope!", elementId, keyAttributes[keyTime]);
                continue;
            }

            const attributes = [];
            const svgItemProperties = keyAttributes[keyTime][elementId];
            // console.log(svgItemProperties);
            let transformWasAdded = false;
            for (let j = 0; j < svgItemProperties.length; j++) {
                const propData = svgItemProperties[j];
                //console.log(keyTime, elementId, propData)
                const prop_group = propData[0];
                const prop_name = propData[1];
                let attributeKey;

                if (prop_group == 'transform') {
                    if (transformWasAdded) {
                        continue;
                    }
                    attributeKey = prop_group;
                    transformWasAdded = true;
                }
                else {
                    continue;
                    attributeKey = prop_name;
                }

                const attributeValue = element.getAttribute(attributeKey);
                //console.log(attributeKey, attributeValue);
                attributes.push(`${attributeKey}: ${attributeValue};\n`);
            }
            //console.log(attributes)
            svgItemCSSKeyframesCode[elementId]['keyframes'].push(`
            ${percentage}% {
                ${attributes.join('\n')}
            }`);
            //console.log(elementId, svgItemCSSKeyframesCode[elementId]['keyframes']);
        }
    }

    /* Set Styles. */
    for (const elementId in svgItemCSSKeyframesCode) {
        if (!svgItemCSSKeyframesCode.hasOwnProperty(elementId)) {
            continue;
        }
        const data = svgItemCSSKeyframesCode[elementId];
        let keyframes = data['keyframes'];
        svgItemCSSCode += `
        @keyframes ${data['elementAnimId']} {
            ${keyframes.join('\n')}
        }
        `;
    }
}

await processWithDelay();

// Crear un nuevo elemento style
const styleElement = document.createElement('style');
// Formatear el contenido del elemento style
styleElement.textContent = svgItemCSSCode; // js_beautify(svgItemCSSCode);

// Append the new style element to the SVG clone
svgElement.prepend(styleElement);
svgElement.setAttribute('viewBox', '0 0 600 600');
svgElement.setAttribute('shape-rendering', 'geometricPrecision');
svgElement.setAttribute('text-rendering', 'geometricPrecision');

// Serialize the modified SVG content to a string
const serializer = new XMLSerializer();
let svgString = serializer.serializeToString(svgElement);

// Wrap the style content with CDATA section
// const wrappedSvgString = svgString.replace('<style>', '<style>/*<![CDATA[*/').replace('</style>', '/*]]>*/</style>');

// Remove 'xmlns' attribute from child elements
// svgString = svgString.replace(/ xmlns="http:\/\/www.w3.org\/2000\/svg"/g, '');
svgString = svgString.replace(/ xmlns="http:\/\/www.w3.org\/1999\/xhtml"/g, '');

// Create a new SVG blob with embedded style
const svgBlob = new Blob([svgString], { type: 'image/svg+xml' });

// Create a data URL for the SVG blob
const svgUrl = URL.createObjectURL(svgBlob);

// Create a link element to trigger the download
const downloadLink = document.createElement('a');
downloadLink.href = svgUrl;
downloadLink.download = 'embedded.svg'; // Set the default file name

// Append the link to the document and trigger the download
document.body.appendChild(downloadLink);
downloadLink.click();

// Clean up by removing the link and revoking the URL
document.body.removeChild(downloadLink);
URL.revokeObjectURL(svgUrl);

document.body.removeChild(svgHolder);
