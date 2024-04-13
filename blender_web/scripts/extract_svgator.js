// 1. Read the content of every <style> in document and join them in an string.
let styleContent = "";
Array.from(document.getElementsByTagName('style')).forEach(style => {
    styleContent += style.innerHTML;
});

// 2. Get the first SVG tag under a div with classes "preview-iframe chess-pattern".
let svgElement = document.querySelector('.preview-iframe.chess-pattern svg');

// 3. Create a SVG file, embed the styles from point 1 and download it automatically.
if (svgElement) {
    // Remove script tags
    Array.from(svgElement.getElementsByTagName('script')).forEach(script => {
        script.remove();
    });

    // Remove empty style tags
    Array.from(svgElement.getElementsByTagName('style')).forEach(style => {
        if (!style.innerHTML.trim()) {
            style.remove();
        }
    });

    // Embed the styles from point 1
    let styleTag = document.createElement('style');
    styleTag.innerHTML = styleContent;
    svgElement.prepend(styleTag);

    let svgData = svgElement.outerHTML;
    let blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    let url = URL.createObjectURL(blob);

    // create a hidden anchor tag to initiate the download
    let downloadLink = document.createElement("a");
    downloadLink.href = url;
    downloadLink.download = "svg_file.svg";
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
} else {
    console.log('SVG element not found.');
}
