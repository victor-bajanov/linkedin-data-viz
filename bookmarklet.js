// LinkedIn Profile → CRM Bookmarklet (readable source)
// Usage: Create a bookmark with the minified version (see bookmarklet_install.html)
// Navigate to a LinkedIn profile page, click the bookmarklet.
//
// Extraction approach (from linkedin-profile-extractor.js):
//   - Scope to first <main section> to avoid nav/notification elements
//   - Filter out video-player h2s via [class*="vjs"]
//   - Collect <p> elements with noise filtering for headline
//   - document.title as fallback for name

(function () {
  var ENDPOINT = "http://localhost:8050/api/import-contact";

  // --- Video/dialog noise strings to skip ---
  var NOISE = [
    "Play", "Pause", "Mute", "LIVE", "Video Player", "Loaded",
    "Stream Type", "Current Time", "Duration", "Fullscreen",
    "Captions", "Settings", "Playback Rate", "modal window",
    "dialog window", "Close Modal"
  ];
  function isNoise(text) {
    for (var i = 0; i < NOISE.length; i++) {
      if (text.indexOf(NOISE[i]) !== -1) return true;
    }
    return /^\d+:\d+$/.test(text) || /^\d+\.\d+%$/.test(text);
  }

  // --- Extract name: scope to first <main section>, skip video h2s ---
  var name = "";
  var headerSection = document.querySelectorAll("main section")[0];

  if (headerSection) {
    var h2s = headerSection.querySelectorAll("h2");
    for (var i = 0; i < h2s.length; i++) {
      // Skip h2s inside video player containers
      if (h2s[i].closest && h2s[i].closest('[class*="vjs"]')) continue;
      var h2Text = h2s[i].innerText.trim();
      if (h2Text && h2Text.length > 1) {
        name = h2Text;
        break;
      }
    }
  }

  // --- Fallback: extract name from document.title ("Person Name | LinkedIn") ---
  if (!name) {
    var titleParts = document.title.split("|");
    if (titleParts.length >= 2 && titleParts[titleParts.length - 1].trim() === "LinkedIn") {
      name = titleParts.slice(0, -1).join("|").trim();
    }
  }

  // --- Extract headline from <p> elements in header section ---
  var headline = "";
  var location = "";
  if (headerSection) {
    var pEls = headerSection.querySelectorAll("p");
    var texts = [];
    for (var j = 0; j < pEls.length; j++) {
      var t = pEls[j].innerText.trim();
      if (t.length > 5 && !isNoise(t)) texts.push(t);
    }
    // Headline: first <p> with length > 20 (job title / description)
    for (var k = 0; k < texts.length; k++) {
      if (texts[k].length > 20) { headline = texts[k]; break; }
    }
    // Location: shorter text with a comma, not the headline, not connections
    for (var m = 0; m < texts.length; m++) {
      if (texts[m] !== headline && texts[m].indexOf(",") !== -1 && texts[m].length < 80 &&
          texts[m].indexOf("connection") === -1 && texts[m].indexOf("mutual") === -1) {
        location = texts[m];
        break;
      }
    }
  }

  // --- Parse position and company from headline ---
  var position = "";
  var company = "";
  if (headline) {
    // Common pattern: "Title at Company"
    var atMatch = headline.match(/^(.+?)\s+(?:at|@)\s+(.+)$/i);
    if (atMatch) {
      position = atMatch[1].trim();
      company = atMatch[2].trim();
    } else {
      // Pipe-separated headline: take first segment as position
      position = headline.split("|")[0].trim();
    }
  }

  // --- Profile URL (strip query params / hash) ---
  var profileUrl = window.location.origin + window.location.pathname;
  profileUrl = profileUrl.replace(/\/+$/, "");

  // --- Bail if we couldn't get a name ---
  if (!name) {
    alert("Could not extract a name. Are you on a LinkedIn profile page?");
    return;
  }

  // --- Confirm with user ---
  var msg =
    "Import to CRM?\n\n" +
    "Name: " + name + "\n" +
    "Position: " + (position || "(not detected)") + "\n" +
    "Company: " + (company || "(not detected)") + "\n" +
    (location ? "Location: " + location + "\n" : "") +
    "URL: " + profileUrl;

  if (!confirm(msg)) return;

  // --- Open localhost endpoint in new tab (avoids CSP connect-src block) ---
  var params =
    "name=" + encodeURIComponent(name) +
    "&position=" + encodeURIComponent(position) +
    "&company=" + encodeURIComponent(company) +
    "&profile_url=" + encodeURIComponent(profileUrl);

  window.open(ENDPOINT + "?" + params, "_blank");
})();
