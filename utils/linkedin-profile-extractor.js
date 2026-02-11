/**
 * LinkedIn Profile DOM Extractor
 * ================================
 * Extracts all content from a LinkedIn profile page.
 *
 * Usage: paste into DevTools console on any linkedin.com/in/... page.
 *
 * Architecture notes
 * ------------------
 * LinkedIn obfuscates all CSS class names (hashed strings like _66ea7430),
 * so class-based selectors are unreliable across builds. Instead we use
 * three structural invariants:
 *
 *   1. Every profile section lives inside a <section> that contains an <h2>
 *      whose text matches a known heading (About, Experience, etc.).
 *
 *   2. Structured entries (roles, education) are rendered as <a> elements
 *      whose textContent concatenates all fields (title, company, dates…).
 *
 *   3. Flat prose sections (About, Skills, Recommendations) can be read
 *      via section.textContent minus the <h2> heading text.
 */

(() => {
  "use strict";

  // ── Helpers ────────────────────────────────────────────────────────

  /** Find a <section> whose <h2> starts with the given label. */
  function findSection(label) {
    const sections = document.querySelectorAll("main section");
    return Array.from(sections).find((s) => {
      const h2 = s.querySelector("h2");
      return h2 && h2.textContent.trim().startsWith(label);
    });
  }

  /** Return section body text (everything minus the h2). */
  function sectionBody(section) {
    if (!section) return "";
    const h2 = section.querySelector("h2");
    let text = section.textContent.replace(/\s+/g, " ").trim();
    if (h2) {
      text = text.replace(h2.textContent.replace(/\s+/g, " ").trim(), "").trim();
    }
    return text;
  }

  /** Get filtered anchor entries from a section. */
  function sectionAnchors(section, minLength = 10) {
    if (!section) return [];
    return Array.from(section.querySelectorAll("a"))
      .map((a) => {
        const text = a.textContent.replace(/\s+/g, " ").trim();
        let path = null;
        try {
          path = new URL(a.href).pathname;
        } catch (_) {}
        return { text, path };
      })
      .filter(
        (a) =>
          a.text.length > minLength &&
          !a.text.startsWith("Show all") &&
          !a.text.startsWith("Show more")
      );
  }

  /** Get aria-label values from figure/svg elements (company/school logos). */
  function sectionLogos(section) {
    if (!section) return [];
    return [
      ...new Set(
        Array.from(section.querySelectorAll("figure[aria-label], svg[aria-label]"))
          .map((el) => el.getAttribute("aria-label"))
          .filter(Boolean)
      ),
    ];
  }

  // Known video-player / dialog junk strings to exclude from the header.
  const HEADER_NOISE = [
    "Play", "Pause", "Mute", "LIVE", "Skip Backward", "Skip Forward",
    "Video Player", "Loaded", "Stream Type", "Current Time", "Duration",
    "Fullscreen", "Captions", "Settings", "Picture-in-Picture",
    "Playback Rate", "Chapters", "Descriptions", "Audio Track",
    "modal window", "dialog window", "Close Modal", "Reset", "Done",
    "captions off", "captions settings", "descriptions off", "selected",
    "Seek to live",
  ];

  function isHeaderNoise(text) {
    return (
      HEADER_NOISE.some((n) => text.includes(n)) ||
      /^\d+:\d+$/.test(text) ||
      /^\d+\.\d+%$/.test(text)
    );
  }

  // ── Section extractors ─────────────────────────────────────────────

  function extractHeader() {
    const section = document.querySelectorAll("main section")[0];
    if (!section) return null;

    // Name — first <h2> outside any video container
    const h2s = section.querySelectorAll("h2");
    const nameEl = Array.from(h2s).find(
      (h) => !h.closest('[class*="vjs"]')
    );
    const name = nameEl ? nameEl.textContent.trim() : null;

    // Collect meaningful <p> elements (exclude video/dialog text)
    const pEls = Array.from(section.querySelectorAll("p"))
      .map((p) => p.textContent.trim())
      .filter((t) => t.length > 5 && !isHeaderNoise(t));

    // Heuristic assignment based on typical ordering
    const headline = pEls.find((t) => t.length > 20) || null;
    const orgs = pEls.find((t) => t.includes("·") && t.length < 120) || null;
    const location = pEls.find(
      (t) =>
        t.includes(",") &&
        !t.includes("|") &&
        t.length < 80 &&
        t !== headline &&
        t !== orgs
    ) || null;

    // Connections
    const connections =
      pEls.find((t) => t.includes("mutual connection")) ||
      Array.from(section.querySelectorAll("a"))
        .map((a) => a.textContent.trim())
        .find((t) => t.includes("mutual connection")) ||
      null;

    // Images
    const imgs = Array.from(section.querySelectorAll("img"));
    const coverImg =
      imgs.find((i) => (i.alt || "").includes("Cover"))?.src || null;
    const profileImg =
      imgs.find(
        (i) =>
          i.alt &&
          !i.alt.includes("Cover") &&
          !i.alt.includes("logo") &&
          i.src.includes("profile")
      )?.src || null;

    return {
      name,
      headline,
      currentOrganisations: orgs,
      location,
      connections,
      profileImageUrl: profileImg,
      coverImageUrl: coverImg,
    };
  }

  function extractAbout() {
    const section = findSection("About");
    if (!section) return null;
    return { text: sectionBody(section) };
  }

  function extractFeatured() {
    const section = findSection("Featured");
    if (!section) return null;

    const items = Array.from(section.querySelectorAll("li"))
      .map((li) => {
        const text = li.textContent.replace(/\s+/g, " ").trim();
        const link = li.querySelector("a");
        let path = null;
        try {
          path = link ? new URL(link.href).pathname : null;
        } catch (_) {}
        const img = li.querySelector("img");
        return {
          text: text.substring(0, 400),
          path,
          thumbnail: img?.alt || null,
        };
      })
      .filter((item) => item.text.length > 15);

    return { count: items.length, items };
  }

  function extractExperience() {
    const section = findSection("Experience");
    if (!section) return null;

    const anchors = sectionAnchors(section, 15);
    const logos = sectionLogos(section);

    // Parse each anchor's concatenated text into structured fields
    const roles = anchors.map((a) => {
      const raw = a.text;
      // LinkedIn concatenates: Title + Company + EmploymentType + DateRange + Duration + Location
      // There is no reliable delimiter — we return raw plus the company path
      return {
        rawText: raw,
        companyPath: a.path,
      };
    });

    // Descriptions (visible text not captured by anchors)
    const bodyText = sectionBody(section);
    // Pull out quoted/expanded descriptions ("Helping Britain Prosper"...)
    const descriptionFragments = bodyText
      .split(/(?=Endorsed|Show all|… more)/)
      .filter((f) => f.length > 60)
      .map((f) => f.trim().substring(0, 500));

    return { roles, logos, descriptionFragments };
  }

  function extractEducation() {
    const section = findSection("Education");
    if (!section) return null;
    const anchors = sectionAnchors(section, 10);
    const logos = sectionLogos(section);

    const entries = anchors.map((a) => ({
      rawText: a.text,
      schoolPath: a.path,
    }));

    return { entries, logos };
  }

  function extractSkills() {
    const section = findSection("Skills");
    if (!section) return null;
    const body = sectionBody(section);

    // Parse the repeating pattern: SkillName + Endorsed... + N endorsements + Endorse
    const skills = [];
    const chunks = body.split(/(?=Endorse\b)/);
    let currentSkill = null;

    for (const chunk of chunks) {
      const trimmed = chunk.trim();
      if (trimmed === "Endorse" || trimmed === "") continue;

      if (trimmed.startsWith("Endorsed by")) {
        // This is endorsement info for the current skill
        if (currentSkill) {
          const countMatch = trimmed.match(/(\d+)\s+endorsements?/);
          if (countMatch) currentSkill.endorsements = parseInt(countMatch[1]);
        }
      } else if (!trimmed.startsWith("Show all")) {
        // New skill name: text before the first "Endorsed" keyword
        const nameEnd = trimmed.indexOf("Endorsed");
        const skillName =
          nameEnd > 0 ? trimmed.substring(0, nameEnd).trim() : trimmed;
        if (skillName.length > 1 && skillName.length < 80) {
          currentSkill = { name: skillName, endorsements: null };
          skills.push(currentSkill);
          // Check if endorsement count is in the same chunk
          const countMatch = trimmed.match(/(\d+)\s+endorsements?/);
          if (countMatch) currentSkill.endorsements = parseInt(countMatch[1]);
        }
      }
    }

    return { skills };
  }

  function extractRecommendations() {
    const section = findSection("Recommendations");
    if (!section) return null;
    const body = sectionBody(section);

    // Split off "Received" tab content (ignore "Given" for now)
    const receivedStart = body.indexOf("Received");
    const givenStart = body.indexOf("Given");
    let receivedText = body;
    if (receivedStart >= 0 && givenStart > receivedStart) {
      receivedText = body.substring(receivedStart + 8, givenStart).trim();
    } else if (receivedStart >= 0) {
      receivedText = body.substring(receivedStart + 8).trim();
    }

    // Recommendation texts are separated by names (people with "· 2nd" / "· 1st" markers)
    const recPattern = /([A-Z][a-zA-Z\s.'-]+)\s*·\s*(1st|2nd|3rd)/g;
    const recs = [];
    let match;
    const indices = [];
    while ((match = recPattern.exec(receivedText)) !== null) {
      indices.push({
        name: match[1].trim(),
        degree: match[2],
        start: match.index,
        end: match.index + match[0].length,
      });
    }

    for (let i = 0; i < indices.length; i++) {
      const textStart = indices[i].end;
      const textEnd = i + 1 < indices.length ? indices[i + 1].start : receivedText.length;
      const recText = receivedText.substring(textStart, textEnd).trim();
      recs.push({
        recommenderName: indices[i].name,
        connectionDegree: indices[i].degree,
        text: recText.substring(0, 800),
      });
    }

    return { received: recs };
  }

  function extractInterests() {
    const section = findSection("Interests");
    if (!section) return null;
    const anchors = sectionAnchors(section, 3);
    const entries = anchors.map((a) => ({
      name: a.text,
      path: a.path,
    }));
    return { entries };
  }

  function extractActivity() {
    const section = findSection("Activity");
    if (!section) return null;

    // Get follower count
    const body = sectionBody(section);
    const followerMatch = body.match(/([\d,]+)\s+followers/);
    const followers = followerMatch ? followerMatch[1] : null;

    // Get recent post snippets from list items
    const lis = Array.from(section.querySelectorAll("li"));
    const posts = lis
      .map((li) => {
        const text = li.textContent.replace(/\s+/g, " ").trim();
        if (text.length < 20) return null;
        // Extract engagement numbers
        const commentMatch = text.match(/([\d,]+)\s+comments?/);
        const repostMatch = text.match(/([\d,]+)\s+reposts?/);
        return {
          snippet: text.substring(0, 350),
          comments: commentMatch ? commentMatch[1] : null,
          reposts: repostMatch ? repostMatch[1] : null,
        };
      })
      .filter(Boolean)
      .slice(0, 6);

    return { followers, recentPosts: posts };
  }

  // ── Main ───────────────────────────────────────────────────────────

  const profile = {
    extractedAt: new Date().toISOString(),
    url: window.location.href,
    header: extractHeader(),
    about: extractAbout(),
    featured: extractFeatured(),
    activity: extractActivity(),
    experience: extractExperience(),
    education: extractEducation(),
    skills: extractSkills(),
    recommendations: extractRecommendations(),
    interests: extractInterests(),
  };

  // ── Output ─────────────────────────────────────────────────────────

  console.log("%c LinkedIn Profile Extracted", "color:#0a66c2;font-size:14px;font-weight:bold");
  console.log(JSON.stringify(profile, null, 2));

  // Also copy to clipboard if available
  if (navigator.clipboard) {
    navigator.clipboard.writeText(JSON.stringify(profile, null, 2)).then(
      () => console.log("%c Copied to clipboard.", "color:green"),
      () => console.log("%c Clipboard write failed — see console output above.", "color:orange")
    );
  }

  return profile;
})();
