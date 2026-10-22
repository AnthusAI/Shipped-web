(function () {
  var CODE128_PATTERNS = (
    "11011001100 11001101100 11001100110 10010011000 10010001100 10001001100 " +
    "10011001000 10011000100 10001100100 11001001000 11001000100 11000100100 " +
    "10110011100 10011011100 10011001110 10111001100 10011101100 10011100110 " +
    "11001110010 11001011100 11001001110 11011100100 11001110100 11101101110 " +
    "11101001100 11100101100 11100100110 11101100100 11100110100 11100110010 " +
    "11011011000 11011000110 11000110110 10100011000 10001011000 10001000110 " +
    "10110001000 10001101000 10001100010 11010001000 11000101000 11000100010 " +
    "10110111000 10110001110 10001101110 10111011000 10111000110 10001110110 " +
    "11101110110 11010001110 11000101110 11011101000 11011100010 11011101110 " +
    "11101011000 11101000110 11100010110 11101101000 11101100010 11100011010 " +
    "11101111010 11001000010 11110001010 10100110000 10100001100 10010110000 " +
    "10010000110 10000101100 10000100110 10110010000 10110000100 10011010000 " +
    "10011000010 10000110100 10000110010 11000010010 11001010000 11110111010 " +
    "11000010100 10001111010 10100111100 10010111100 10010011110 10111100100 " +
    "10011110100 10011110010 11110100100 11110010100 11110010010 11011011110 " +
    "11011110110 11110110110 10101111000 10100011110 10001011110 10111101000 " +
    "10111100010 11110101000 11110100010 10111011110 10111101110 11101011110 " +
    "11110101110 11010000100 11010010000 11010011100 11000111010"
  ).split(" ");
  var START_B = 104;
  var STOP = 106;
  var HEIGHT_UNITS = 46;
  var SVG_NAMESPACE = "http://www.w3.org/2000/svg";

  function twoDigits(number) {
    return (number < 10 ? "0" : "") + number;
  }

  function localDateLabel(now) {
    return "SHP " + now.getFullYear() + "-" + twoDigits(now.getMonth() + 1) + "-" + twoDigits(now.getDate());
  }

  function modulesFor(text) {
    var symbols = [START_B];
    var weighted = START_B;
    for (var index = 0; index < text.length; index += 1) {
      var value = text.charCodeAt(index) - 32;
      symbols.push(value);
      weighted += (index + 1) * value;
    }
    symbols.push(weighted % 103, STOP);
    return symbols.map(function (symbol) { return CODE128_PATTERNS[symbol]; }).join("") + "11";
  }

  function redraw(holder, text) {
    var bars = holder.querySelector("svg");
    var caption = holder.querySelector("[data-brand-barcode-text]");
    if (!bars) { return; }
    var modules = modulesFor(text);
    while (bars.firstChild) { bars.removeChild(bars.firstChild); }
    bars.setAttribute("viewBox", "0 0 " + modules.length + " " + HEIGHT_UNITS);
    bars.setAttribute("aria-label", "Barcode for " + text + ", today's date");
    var position = 0;
    while (position < modules.length) {
      if (modules.charAt(position) !== "1") { position += 1; continue; }
      var end = position;
      while (end < modules.length && modules.charAt(end) === "1") { end += 1; }
      var bar = document.createElementNS(SVG_NAMESPACE, "rect");
      bar.setAttribute("x", position);
      bar.setAttribute("y", 0);
      bar.setAttribute("width", end - position);
      bar.setAttribute("height", HEIGHT_UNITS);
      bars.appendChild(bar);
      position = end;
    }
    if (caption) { caption.textContent = text; }
  }

  var text = localDateLabel(new Date());
  var holders = document.querySelectorAll("[data-brand-barcode]");
  for (var holderIndex = 0; holderIndex < holders.length; holderIndex += 1) {
    redraw(holders[holderIndex], text);
  }
})();
