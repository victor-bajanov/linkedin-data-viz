// LinkedIn Profile → CRM Bookmarklet (readable source)
// Usage: Create a bookmark with the minified version (see bookmarklet_minified.txt)
// Navigate to a LinkedIn profile page, click the bookmarklet.

(function () {
  var ENDPOINT = "http://localhost:8050/api/import-contact";

  // --- Extract name ---
  var nameEl = document.querySelector("h1");
  var name = nameEl ? nameEl.innerText.trim() : "";

  // --- Extract headline (position / title line below name) ---
  var headline = "";
  var headlineEl = document.querySelector(".text-body-medium");
  if (headlineEl) {
    headline = headlineEl.innerText.trim();
  }

  // --- Parse "Title at Company" from headline ---
  var position = "";
  var company = "";
  if (headline) {
    // Common patterns: "Title at Company" or "Title @ Company"
    var atMatch = headline.match(/^(.+?)\s+(?:at|@)\s+(.+)$/i);
    if (atMatch) {
      position = atMatch[1].trim();
      company = atMatch[2].trim();
    } else {
      // If no "at", treat entire headline as position
      position = headline;
    }
  }

  // --- Try to get company from the Experience section's top entry as fallback ---
  if (!company) {
    // The top experience entry usually has the current company
    var expSection = document.getElementById("experience");
    if (expSection) {
      // Walk up to the section container, then find the first company span
      var sectionContainer = expSection.closest("section");
      if (sectionContainer) {
        var expSpans = sectionContainer.querySelectorAll(
          "span.t-14.t-normal:not(.t-black--light)"
        );
        for (var i = 0; i < expSpans.length; i++) {
          var text = expSpans[i].innerText.trim();
          // Skip durations like "1 yr 3 mos"
          if (text && !text.match(/^\d+\s+(yr|mo|day)/i)) {
            company = text;
            break;
          }
        }
      }
    }
  }

  // --- Profile URL (strip query params / hash) ---
  var profileUrl = window.location.origin + window.location.pathname;
  // Normalise trailing slash
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
    "URL: " + profileUrl;

  if (!confirm(msg)) return;

  // --- POST to local Dash app ---
  var payload = {
    name: name,
    position: position,
    company: company,
    profile_url: profileUrl,
  };

  fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then(function (r) {
      return r.json();
    })
    .then(function (d) {
      if (d.error) {
        alert("Error: " + d.error);
      } else {
        alert(
          (d.status === "created" ? "Added" : "Updated") + ": " + d.name
        );
      }
    })
    .catch(function (e) {
      alert("Failed to reach CRM app.\n\n" + e + "\n\nIs the Dash app running on localhost:8050?");
    });
})();
