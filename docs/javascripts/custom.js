window.addEventListener("load", function() {
    console.log('Customization for improved readability: setting style max-width to 999rem in .md-grid class');
    var sheet = document.styleSheets[0];
    sheet.insertRule(".md-grid { max-width:999rem; }", sheet.cssRules.length);
});