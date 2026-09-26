/* ==========================================================================
   TraceRoot AI — Frontend application logic
   Vanilla JS. No frameworks. Talks only to the existing FastAPI backend.
   ========================================================================== */

(function () {
  "use strict";

  // --------------------------------------------------------------------
  // Config
  // --------------------------------------------------------------------

  const API_BASE = "http://localhost:8000";
  const REQUEST_TIMEOUT_MS = 8000;

  const ENDPOINTS = [
    { method: "GET", path: "/", desc: "API home / liveness message." },
    { method: "GET", path: "/health", desc: "Reports API, model and dashboard-artifact readiness." },
    { method: "POST", path: "/predict", desc: "Legacy single-anomaly prediction (8-feature request, 2-field response)." },
    { method: "POST", path: "/api/v1/predict", desc: "Hybrid prediction using the stored model plus the severity rule." },
    { method: "GET", path: "/api/v1/anomalies", desc: "Paginated, filterable list of stored anomaly results." },
    { method: "GET", path: "/api/v1/incidents", desc: "List of stored correlated incidents." },
    { method: "GET", path: "/api/v1/incidents/{incident_id}", desc: "A single stored incident by ID." },
    { method: "GET", path: "/api/v1/root-cause-analysis", desc: "Structured, deterministic root-cause analysis." },
    { method: "GET", path: "/api/v1/metrics", desc: "Summary counts derived from stored artifacts." },
  ];

  // --------------------------------------------------------------------
  // Safe DOM helpers
  // --------------------------------------------------------------------

  function safeGetElement(id) {
    try {
      return document.getElementById(id);
    } catch (err) {
      return null;
    }
  }

  function safeQuery(selector, root) {
    try {
      return (root || document).querySelector(selector);
    } catch (err) {
      return null;
    }
  }

  function safeQueryAll(selector, root) {
    try {
      return Array.prototype.slice.call((root || document).querySelectorAll(selector));
    } catch (err) {
      return [];
    }
  }

  function setText(el, text) {
    if (el) el.textContent = text;
  }

  function setHTML(el, html) {
    if (el) el.innerHTML = html;
  }

  function escapeHTML(value) {
    const str = value === null || value === undefined ? "" : String(value);
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // --------------------------------------------------------------------
  // Toasts
  // --------------------------------------------------------------------

  function showToast(message, type) {
    const container = safeGetElement("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast" + (type === "error" ? " error" : type === "success" ? " success" : "");
    toast.innerHTML =
      '<span class="toast-dot"></span><span>' + escapeHTML(message) + "</span>";

    container.appendChild(toast);

    setTimeout(function () {
      toast.classList.add("leaving");
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 250);
    }, 4200);
  }

  // --------------------------------------------------------------------
  // API client
  // --------------------------------------------------------------------

  function withTimeout(promise, ms) {
    let timeoutId;
    const timeout = new Promise(function (_, reject) {
      timeoutId = setTimeout(function () {
        reject(new Error("Request timed out"));
      }, ms);
    });
    return Promise.race([promise, timeout]).finally(function () {
      clearTimeout(timeoutId);
    });
  }

  /**
   * apiFetch — defensive wrapper around fetch().
   * Never throws. Always resolves to:
   *   { ok, status, data, error }
   */
  async function apiFetch(path, options) {
    const url = API_BASE + path;
    const opts = Object.assign(
      {
        headers: { "Content-Type": "application/json" },
      },
      options || {}
    );

    try {
      const response = await withTimeout(fetch(url, opts), REQUEST_TIMEOUT_MS);
      let data = null;
      const text = await response.text();

      if (text) {
        try {
          data = JSON.parse(text);
        } catch (parseErr) {
          data = { raw: text };
        }
      }

      return {
        ok: response.ok,
        status: response.status,
        data: data,
        error: response.ok
          ? null
          : (data && (data.detail || data.message)) || "Request failed (" + response.status + ")",
      };
    } catch (err) {
      const message =
        err && err.message === "Request timed out"
          ? "Backend request timed out"
          : "Backend unavailable";
      return { ok: false, status: 0, data: null, error: message };
    }
  }

  // --------------------------------------------------------------------
  // Status helpers
  // --------------------------------------------------------------------

  // state: "on" | "warn" | "off" | "neutral"
  function setStatusRow(el, state, label) {
    if (!el) return;
    const dot = safeQuery(".status-dot", el);
    const stateEl = safeQuery(".status-state", el);
    if (dot) {
      dot.classList.remove("on", "warn", "off");
      if (state === "on" || state === "warn" || state === "off") {
        dot.classList.add(state);
      }
    }
    if (stateEl) setText(stateEl, label);
  }

  function setPill(el, state, label) {
    if (!el) return;
    el.classList.remove("on", "warn", "off", "neutral");
    el.classList.add(state || "neutral");
    const dot = safeQuery(".status-dot", el);
    if (dot) {
      dot.classList.remove("on", "warn", "off");
      if (state === "on" || state === "warn" || state === "off") {
        dot.classList.add(state);
      }
    }
    const textNode = Array.prototype.find.call(el.childNodes, function (n) {
      return n.nodeType === Node.TEXT_NODE;
    });
    // Rebuild text content after the dot span.
    while (el.lastChild && el.lastChild !== dot) {
      el.removeChild(el.lastChild);
    }
    el.appendChild(document.createTextNode(" " + label));
  }

  // --------------------------------------------------------------------
  // Application state
  // --------------------------------------------------------------------

  const state = {
    currentPage: "overview",
    health: null,
    healthOk: false,
    metrics: null,
    eventPage: 1,
  };

  // --------------------------------------------------------------------
  // Loading screen / boot sequence
  // --------------------------------------------------------------------

  const BOOT_STAGES = [
    "INITIALIZING INCIDENT INTELLIGENCE",
    "CONNECTING TO ANALYSIS ENGINE",
    "LOADING ANOMALY DETECTOR",
    "MAPPING SERVICE DEPENDENCIES",
    "INITIALIZING ROOT-CAUSE ENGINE",
    "SYSTEM READY",
  ];

  function runBootSequence() {
    const bar = safeGetElement("loading-progress-bar");
    const pct = safeGetElement("loading-percent");
    const stageEl = safeGetElement("boot-stage");
    const screen = safeGetElement("loading-screen");
    const app = safeGetElement("app");

    const totalDurationMs = 2000;
    const stepMs = 40;
    let elapsed = 0;

    const interval = setInterval(function () {
      elapsed += stepMs;
      const progress = Math.min(100, Math.round((elapsed / totalDurationMs) * 100));

      if (bar) bar.style.width = progress + "%";
      if (pct) setText(pct, progress + "%");

      const stageIndex = Math.min(
        BOOT_STAGES.length - 1,
        Math.floor((progress / 100) * BOOT_STAGES.length)
      );
      if (stageEl) setText(stageEl, BOOT_STAGES[stageIndex]);

      if (progress >= 100) {
        clearInterval(interval);

        setTimeout(function () {
          if (screen) screen.classList.add("fade-out");
          if (app) app.classList.add("visible");

          setTimeout(function () {
            if (screen && screen.parentNode) {
              screen.parentNode.removeChild(screen);
            }
          }, 650);

          // Dashboard is visible now — kick off the real backend health check.
          checkHealth();
        }, 220);
      }
    }, stepMs);
  }

  // --------------------------------------------------------------------
  // Health check
  // --------------------------------------------------------------------

  async function checkHealth() {
    const result = await apiFetch("/health");
    state.healthOk = result.ok;
    state.health = result.data;

    applyHealthToUI(result);
    return result;
  }

  function applyHealthToUI(result) {
    const ok = result.ok;
    const data = result.data || {};

    const apiState = ok ? "on" : "off";
    const apiLabel = ok ? "ONLINE" : "OFFLINE";

    setStatusRow(safeGetElement("sb-api"), apiState, apiLabel);
    setPill(safeGetElement("tb-api"), apiState, ok ? "API ONLINE" : "API OFFLINE");

    // Model status only means something if the API itself responded.
    let modelState = "off";
    let modelLabel = "OFFLINE";
    if (ok) {
      if (data.model_loaded || data.model_loadable) {
        modelState = "on";
        modelLabel = "LOADED";
      } else if (data.model_available) {
        modelState = "warn";
        modelLabel = "NOT LOADED";
      } else {
        modelState = "off";
        modelLabel = "NOT FOUND";
      }
    }
    setStatusRow(safeGetElement("sb-model"), modelState, modelLabel);

    // Gemini is not reported anywhere by this backend's /health response.
    // Be honest about that instead of inventing a status.
    let geminiState = "neutral";
    let geminiLabel = "—";
    if (ok) {
      if (typeof data.gemini_available === "boolean") {
        geminiState = data.gemini_available ? "on" : "warn";
        geminiLabel = data.gemini_available ? "AVAILABLE" : "UNAVAILABLE";
      } else {
        geminiState = "off";
        geminiLabel = "UNAVAILABLE";
      }
    } else {
      geminiState = "off";
      geminiLabel = "UNAVAILABLE";
    }
    setStatusRow(safeGetElement("sb-gemini"), geminiState, geminiLabel);

    const overallState = ok ? (modelState === "on" ? "on" : "warn") : "off";
    setPill(safeGetElement("tb-system"), overallState, ok ? "SYSTEM " + (data.status || "OK").toUpperCase() : "SYSTEM DOWN");

    renderOverviewHealth(result, modelState, modelLabel, geminiState, geminiLabel);
    renderSystemHealth(result, modelState, modelLabel, geminiState, geminiLabel);

    if (state.currentPage === "api") {
      updateApiOverallStatus(ok);
    }

    if (!ok) {
      showToast("Backend unavailable at " + API_BASE, "error");
    }
  }

  function renderOverviewHealth(result, modelState, modelLabel, geminiState, geminiLabel) {
    const ok = result.ok;
    const data = result.data || {};

    setPill(safeGetElement("ov-api-pill"), ok ? "on" : "off", ok ? "ONLINE" : "OFFLINE");
    setText(safeGetElement("ov-api-value"), ok ? "ONLINE" : "OFFLINE");
    safeGetElement("ov-api-value") && safeGetElement("ov-api-value").classList.toggle("dim", !ok);
    setText(safeGetElement("ov-api-sub"), ok ? API_BASE : result.error || "Unreachable");

    setPill(safeGetElement("ov-model-pill"), modelState, modelLabel);
    setText(safeGetElement("ov-model-value"), modelLabel);
    setText(
      safeGetElement("ov-model-sub"),
      ok ? "Loadable: " + String(!!data.model_loadable) : "No data"
    );

    setPill(safeGetElement("ov-gemini-pill"), geminiState, geminiLabel);
    setText(safeGetElement("ov-gemini-value"), geminiLabel);
    setText(
      safeGetElement("ov-gemini-sub"),
      typeof data.gemini_available === "boolean"
        ? "Reported by backend"
        : "Not exposed by this backend"
    );

    setPill(safeGetElement("ov-sys-api"), ok ? "on" : "off", ok ? "ONLINE" : "OFFLINE");
    setPill(safeGetElement("ov-sys-model"), modelState, modelLabel);
    setPill(safeGetElement("ov-sys-gemini"), geminiState, geminiLabel);
  }

  function renderSystemHealth(result, modelState, modelLabel, geminiState, geminiLabel) {
    const ok = result.ok;
    const data = result.data || {};

    setPill(safeGetElement("sys-backend"), ok ? "on" : "off", ok ? "ONLINE" : "OFFLINE");
    setPill(safeGetElement("sys-model"), modelState, modelLabel === "LOADED" ? "LOADED" : modelLabel);
    setPill(safeGetElement("sys-gemini"), geminiState, geminiLabel);
    setPill(safeGetElement("sys-cors"), ok ? "on" : "off", ok ? "CONNECTED" : "ERROR");

    const list = safeGetElement("sys-artifacts-list");
    if (list) {
      const artifacts = data.dashboard_artifacts;
      if (ok && artifacts && Object.keys(artifacts).length) {
        list.innerHTML = Object.keys(artifacts)
          .map(function (name) {
            const info = artifacts[name] || {};
            const good = info.available && info.readable;
            return (
              '<div class="kv-row"><span class="kv-key">' +
              escapeHTML(name) +
              '</span><span class="pill ' +
              (good ? "on" : "off") +
              '"><span class="status-dot"></span> ' +
              (good ? "OK" : "ISSUE") +
              "</span></div>"
            );
          })
          .join("");
      } else {
        list.innerHTML =
          '<div class="empty-state"><span class="empty-icon">—</span>No data available.</div>';
      }
    }
  }

  // --------------------------------------------------------------------
  // Overview: metrics + incidents
  // --------------------------------------------------------------------

  async function loadOverviewData() {
    const [metricsResult, incidentsResult] = await Promise.all([
      apiFetch("/api/v1/metrics"),
      apiFetch("/api/v1/incidents"),
    ]);

    if (metricsResult.ok && metricsResult.data) {
      const m = metricsResult.data;
      const criticalCount =
        (m.logs_by_level && m.logs_by_level.CRITICAL) !== undefined
          ? m.logs_by_level.CRITICAL
          : null;
      const servicesAffected =
        m.anomalies_by_service ? Object.keys(m.anomalies_by_service).length : null;

      setText(safeGetElement("ov-sum-anomalies"), fmt(m.hybrid_anomaly_count));
      setText(safeGetElement("ov-sum-critical"), fmt(criticalCount));
      setText(safeGetElement("ov-sum-services"), fmt(servicesAffected));
      setText(safeGetElement("ov-sum-rootcause"), m.root_cause_service || "—");
    } else {
      ["ov-sum-anomalies", "ov-sum-critical", "ov-sum-services", "ov-sum-rootcause"].forEach(
        function (id) {
          setText(safeGetElement(id), "No data");
        }
      );
    }

    if (incidentsResult.ok && incidentsResult.data) {
      const total =
        typeof incidentsResult.data.total === "number"
          ? incidentsResult.data.total
          : (incidentsResult.data.items || incidentsResult.data.incidents || []).length;
      setText(safeGetElement("ov-incidents-value"), String(total));
      safeGetElement("ov-incidents-value") &&
        safeGetElement("ov-incidents-value").classList.remove("dim");
      setText(safeGetElement("ov-incidents-sub"), total === 1 ? "1 incident on record" : total + " incidents on record");
    } else {
      setText(safeGetElement("ov-incidents-value"), "—");
      setText(safeGetElement("ov-incidents-sub"), incidentsResult.error || "No data");
    }
  }

  function fmt(value) {
    return value === null || value === undefined ? "—" : String(value);
  }

  // --------------------------------------------------------------------
  // Detection page
  // --------------------------------------------------------------------

  function initDetectionPage() {
    const form = safeGetElement("detection-form");
    if (!form) return;

    form.addEventListener("submit", async function (event) {
      event.preventDefault();

      const btn = safeGetElement("run-detection-btn");
      const statusEl = safeGetElement("detection-status");
      const resultWrap = safeGetElement("detection-result-wrap");

      const payload = {
        severity: numOrZero(safeGetElement("f-severity")),
        is_error: safeGetElement("f-is-error")
        ? (safeGetElement("f-is-error").value === "true" ? 1 : 0)
        : 0,
        service_code: numOrZero(safeGetElement("f-service-code")),
        message_length: numOrZero(safeGetElement("f-message-length")),
        time_since_previous: numOrZero(safeGetElement("f-time-since-previous")),
        errors_in_last_minute: numOrZero(safeGetElement("f-errors-last-min")),
        warnings_in_last_minute: numOrZero(safeGetElement("f-warnings-last-min")),
        service_error_rate: numOrZero(safeGetElement("f-service-error-rate")),
      };

      if (btn) btn.disabled = true;
      setText(statusEl, "Running detection…");
      if (resultWrap) resultWrap.innerHTML = "";

      const result = await apiFetch("/api/v1/predict", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (btn) btn.disabled = false;

      if (!result.ok) {
        setText(statusEl, "");
        renderDetectionError(resultWrap, result.error);
        showToast(result.error || "Detection request failed", "error");
        return;
      }

      setText(statusEl, "");
      renderDetectionResult(resultWrap, result.data);
    });
  }

  function numOrZero(el) {
    if (!el) return 0;
    const value = parseFloat(el.value);
    return isNaN(value) ? 0 : value;
  }

  function renderDetectionError(wrap, message) {
    if (!wrap) return;
    wrap.innerHTML =
      '<div class="result-block"><div class="empty-state"><span class="empty-icon">—</span>' +
      escapeHTML(message || "Request failed.") +
      "</div></div>";
  }

  function renderDetectionResult(wrap, data) {
    if (!wrap) return;
    data = data || {};

    const prediction = data.prediction || "Unknown";
    const isAnomaly = String(prediction).toLowerCase().indexOf("anomaly") !== -1;

    wrap.innerHTML =
      '<div class="result-block">' +
      '<div class="result-headline"><span class="value ' +
      (isAnomaly ? "anomaly" : "normal") +
      '">' +
      escapeHTML(prediction) +
      "</span></div>" +
      '<div class="result-grid">' +
      resultItem("ML PREDICTION", data.ml_prediction) +
      resultItem("RULE PREDICTION", data.rule_prediction) +
      resultItem("SEVERITY", data.severity) +
      resultItem("MODEL OUTPUT", data.model_output) +
      "</div>" +
      (data.message
        ? '<p class="reason-text" style="margin-top:14px;">' + escapeHTML(data.message) + "</p>"
        : "") +
      (data.context_note
        ? '<p class="reason-text" style="margin-top:6px;color:var(--text-low);font-size:11.5px;">' +
          escapeHTML(data.context_note) +
          "</p>"
        : "") +
      "</div>";
  }

  function resultItem(label, value) {
    if (value === undefined) return "";
    return (
      '<div class="result-item"><div class="k">' +
      escapeHTML(label) +
      '</div><div class="v">' +
      escapeHTML(value === null ? "—" : value) +
      "</div></div>"
    );
  }

  // --------------------------------------------------------------------
  // Root cause page
  // --------------------------------------------------------------------

  function initRootCausePage() {
    const btn = safeGetElement("run-rootcause-btn");
    if (!btn) return;
    btn.addEventListener("click", runRootCauseAnalysis);
  }

  async function runRootCauseAnalysis() {
    const btn = safeGetElement("run-rootcause-btn");
    const statusEl = safeGetElement("rootcause-status");
    const content = safeGetElement("rootcause-content");

    if (btn) btn.disabled = true;
    setText(statusEl, "Running analysis…");

    // The backend does not expose POST /root-cause today — only a stored,
    // read-only GET /api/v1/root-cause-analysis. We still attempt the POST
    // first in case it's added, and fall back automatically so the page
    // never breaks against the backend that actually exists.
    let result = await apiFetch("/root-cause", { method: "POST", body: JSON.stringify({}) });

    let usedFallback = false;
    if (!result.ok) {
      usedFallback = true;
      result = await apiFetch("/api/v1/root-cause-analysis");
    }

    if (btn) btn.disabled = false;
    setText(statusEl, "");

    if (!result.ok) {
      if (content) {
        content.innerHTML =
          '<div class="panel"><div class="empty-state"><span class="empty-icon">—</span>' +
          escapeHTML(result.error || "Root-cause analysis is unavailable.") +
          "</div></div>";
      }
      showToast(result.error || "Root-cause request failed", "error");
      return;
    }

    if (usedFallback) {
      showToast("POST /root-cause is not exposed — showing stored analysis instead.", "success");
    }

    renderRootCause(content, normalizeRootCause(result.data));
  }

  function normalizeRootCause(data) {
    data = data || {};
    // GET /api/v1/root-cause-analysis wraps the analysis in { total, items, analysis }.
    const analysis = data.analysis || (Array.isArray(data.items) ? data.items[0] : null) || data;
    return {
      rootCauseService: analysis.root_cause_service || analysis.probable_root_cause || null,
      confidence: analysis.confidence || null,
      firstProblemTime: analysis.first_problem_time || null,
      firstProblemLevel: analysis.first_problem_level || null,
      firstProblemMessage: analysis.first_problem_message || null,
      reason: analysis.reason || analysis.explanation || null,
      serviceScores: analysis.service_scores || {},
      geminiExplanation: analysis.gemini_explanation || analysis.gemini || null,
      geminiAvailable:
      analysis.gemini_available !== undefined
      ? analysis.gemini_available
      : null,
    };
  }

  function renderRootCause(content, rc) {
    if (!content) return;

    if (!rc.rootCauseService) {
      content.innerHTML =
        '<div class="panel"><div class="empty-state"><span class="empty-icon">—</span>No problematic events were found in the stored analysis.</div></div>';
      return;
    }

    const services = Object.keys(rc.serviceScores || {});

    const timelineHTML = services.length
      ? services
          .slice()
          .sort(function (a, b) {
            return (
              new Date(rc.serviceScores[a].first_problem) -
              new Date(rc.serviceScores[b].first_problem)
            );
          })
          .map(function (service) {
            const s = rc.serviceScores[service];
            return (
              '<div class="timeline-item"><span class="timeline-dot"></span>' +
              '<div class="timeline-time">' +
              escapeHTML(s.first_problem || "—") +
              "</div>" +
              '<div class="timeline-body"><strong>' +
              escapeHTML(service) +
              "</strong> — " +
              fmt(s.problem_events) +
              " problem event(s)</div></div>"
            );
          })
          .join("")
      : '<div class="empty-state"><span class="empty-icon">—</span>No timeline data.</div>';

    const badgesHTML = services.length
      ? services
          .map(function (service) {
            const isRoot = service === rc.rootCauseService;
            return (
              '<span class="svc-badge' +
              (isRoot ? " root" : "") +
              '">' +
              escapeHTML(service) +
              "</span>"
            );
          })
          .join("")
      : '<span class="metric-sub">No affected services reported.</span>';

    const evidenceRowsHTML = services.length
      ? services
          .map(function (service) {
            const s = rc.serviceScores[service];
            const isRoot = service === rc.rootCauseService;
            return (
              "<tr" +
              (isRoot ? ' class="is-root"' : "") +
              "><td>" +
              escapeHTML(service) +
              "</td><td>" +
              fmt(s.severity_score) +
              "</td><td>" +
              fmt(s.warnings) +
              "</td><td>" +
              fmt(s.errors) +
              "</td><td>" +
              fmt(s.criticals) +
              "</td><td>" +
              escapeHTML(s.first_problem || "—") +
              "</td></tr>"
            );
          })
          .join("")
      : "";

    const geminiSectionHTML =
      rc.geminiExplanation
        ? '<p class="reason-text">' + escapeHTML(rc.geminiExplanation) + "</p>"
        : '<div class="empty-state"><span class="empty-icon">—</span>AI explanation unavailable. This backend does not provide a Gemini-generated narrative — the deterministic explanation above is the full evidence trail.</div>';

    content.innerHTML =
      '<div class="stack">' +
      '<div class="panel">' +
      '<div class="rc-hero">' +
      '<div><div class="section-label">ROOT CAUSE SERVICE</div><div class="rc-service">' +
      escapeHTML(rc.rootCauseService) +
      "</div></div>" +
      '<span class="pill ' +
      (rc.confidence === "High" ? "on" : rc.confidence === "Low" ? "warn" : "neutral") +
      '"><span class="status-dot"></span>' +
      escapeHTML(rc.confidence || "UNKNOWN") +
      " CONFIDENCE</span>" +
      "</div>" +
      "</div>" +
      '<div class="two-col">' +
      '<div class="panel"><div class="panel-header"><span class="panel-title">Timeline</span></div><div class="panel-body"><div class="timeline">' +
      timelineHTML +
      "</div></div></div>" +
      '<div class="panel"><div class="panel-header"><span class="panel-title">Affected Services</span></div><div class="panel-body"><div class="badge-row">' +
      badgesHTML +
      "</div></div></div>" +
      "</div>" +
      '<div class="panel"><div class="panel-header"><span class="panel-title">Evidence</span></div><div class="panel-body"><div class="log-table-wrap"><table class="evidence-table"><thead><tr><th>SERVICE</th><th>SCORE</th><th>WARN</th><th>ERR</th><th>CRIT</th><th>FIRST SEEN</th></tr></thead><tbody>' +
      evidenceRowsHTML +
      "</tbody></table></div></div></div>" +
      '<div class="panel"><div class="panel-header"><span class="panel-title">First Problem Event</span></div><div class="panel-body"><div class="result-grid">' +
      resultItem("TIME", rc.firstProblemTime) +
      resultItem("LEVEL", rc.firstProblemLevel) +
      resultItem("MESSAGE", rc.firstProblemMessage) +
      "</div></div></div>" +
      '<div class="panel"><div class="panel-header"><span class="panel-title">Reason</span></div><div class="panel-body"><p class="reason-text">' +
      escapeHTML(rc.reason || "No explanation provided.") +
      "</p></div></div>" +
      '<div class="panel"><div class="panel-header"><span class="panel-title">AI Investigation</span></div><div class="panel-body">' +
      geminiSectionHTML +
      "</div></div>" +
      "</div>";
  }

  // --------------------------------------------------------------------
  // Event analyzer page
  // --------------------------------------------------------------------

  function initEventAnalyzerPage() {
    const form = safeGetElement("event-filter-form");
    if (!form) return;

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      state.eventPage = 1;
      loadEvents();
    });
  }

  async function loadEvents() {
    const statusEl = safeGetElement("event-search-status");
    const body = safeGetElement("event-table-body");
    const pagination = safeGetElement("event-pagination");

    const search = valueOf("ea-search");
    const service = valueOf("ea-service");
    const level = valueOf("ea-level");
    const anomalyOnly = valueOf("ea-anomaly-only") === "true";

    const params = new URLSearchParams();
    params.set("page", String(state.eventPage));
    params.set("page_size", "20");
    if (search) params.set("search", search);
    if (service) params.set("service", service);
    if (level) params.set("level", level);
    if (anomalyOnly) params.set("anomaly_only", "true");

    setText(statusEl, "Searching…");

    const result = await apiFetch("/api/v1/anomalies?" + params.toString());

    setText(statusEl, "");

    if (!result.ok) {
      if (body) {
        body.innerHTML =
          '<tr><td colspan="5" style="text-align:center;color:var(--text-low);padding:24px;">' +
          escapeHTML(result.error || "Unable to load events.") +
          "</td></tr>";
      }
      if (pagination) pagination.innerHTML = "";
      showToast(result.error || "Event search failed", "error");
      return;
    }

    const data = result.data || {};
    const records = data.items || data.results || [];

    renderEventTable(body, records);
    renderEventPagination(pagination, data);
  }

  function valueOf(id) {
    const el = safeGetElement(id);
    return el ? el.value.trim() : "";
  }

  function isAnomalyRecord(record) {
    if (record.final_anomaly !== undefined) {
      return record.final_anomaly === 1 || record.final_anomaly === "1" || record.final_anomaly === true;
    }
    if (record.predicted_anomaly !== undefined) {
      return (
        record.predicted_anomaly === 1 ||
        record.predicted_anomaly === "1" ||
        record.predicted_anomaly === true
      );
    }
    if (record.anomaly !== undefined) {
      return record.anomaly === -1 || record.anomaly === "-1";
    }
    return false;
  }

  function renderEventTable(body, records) {
    if (!body) return;

    if (!records || !records.length) {
      body.innerHTML =
        '<tr><td colspan="5" style="text-align:center;color:var(--text-low);padding:24px;">No events match this search.</td></tr>';
      return;
    }

    body.innerHTML = records
      .map(function (record) {
        const anomaly = isAnomalyRecord(record);
        const level = record.level || "—";
        return (
          "<tr" +
          (anomaly ? ' class="is-anomaly"' : "") +
          "><td>" +
          escapeHTML(record.timestamp || "—") +
          "</td><td>" +
          escapeHTML(record.service || "—") +
          '</td><td><span class="level-tag ' +
          escapeHTML(level) +
          '">' +
          escapeHTML(level) +
          "</span></td><td class=\"msg-cell\">" +
          escapeHTML(record.message || "—") +
          "</td><td>" +
          (anomaly ? "YES" : "no") +
          "</td></tr>"
        );
      })
      .join("");
  }

  function renderEventPagination(pagination, data) {
    if (!pagination) return;

    const page = data.page || state.eventPage;
    const pages = data.pages || 0;
    const total = data.total !== undefined ? data.total : "—";

    pagination.innerHTML =
      '<span>Page ' +
      page +
      " of " +
      (pages || 1) +
      " · " +
      total +
      ' total</span><span class="btn-row">' +
      '<button class="btn ghost" id="event-prev-btn" type="button"' +
      (page <= 1 ? " disabled" : "") +
      ">PREV</button>" +
      '<button class="btn ghost" id="event-next-btn" type="button"' +
      (pages && page >= pages ? " disabled" : "") +
      ">NEXT</button></span>";

    const prevBtn = safeGetElement("event-prev-btn");
    const nextBtn = safeGetElement("event-next-btn");
    if (prevBtn) {
      prevBtn.addEventListener("click", function () {
        if (state.eventPage > 1) {
          state.eventPage -= 1;
          loadEvents();
        }
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        state.eventPage += 1;
        loadEvents();
      });
    }
  }

  // --------------------------------------------------------------------
  // API page
  // --------------------------------------------------------------------

  function initApiPage() {
    const list = safeGetElement("endpoint-list");
    if (list) {
      list.innerHTML = ENDPOINTS.map(function (ep, index) {
        return (
          '<div class="endpoint-row" data-index="' +
          index +
          '"><span class="method-tag ' +
          ep.method +
          '">' +
          ep.method +
          '</span><span class="endpoint-path">' +
          escapeHTML(ep.path) +
          '</span><span class="endpoint-desc">' +
          escapeHTML(ep.desc) +
          "</span></div>"
        );
      }).join("");

      safeQueryAll(".endpoint-row", list).forEach(function (row) {
        row.addEventListener("click", function () {
          row.classList.toggle("expanded");
        });
      });
    }

    const swaggerBtn = safeGetElement("open-swagger-btn");
    if (swaggerBtn) {
      swaggerBtn.addEventListener("click", function () {
        window.open("http://127.0.0.1:8000/docs", "_blank", "noopener");
      });
    }

    updateApiOverallStatus(state.healthOk);
  }

  function updateApiOverallStatus(ok) {
    setText(
      safeGetElement("api-overall-status"),
      ok ? "Backend reachable at " + API_BASE : "Backend unreachable at " + API_BASE
    );
  }

  // --------------------------------------------------------------------
  // System page
  // --------------------------------------------------------------------

  function initSystemPage() {
    const btn = safeGetElement("refresh-system-btn");
    if (!btn) return;

    btn.addEventListener("click", async function () {
      btn.disabled = true;
      setText(safeGetElement("system-status-note"), "Refreshing…");
      await checkHealth();
      setText(safeGetElement("system-status-note"), "Updated " + new Date().toLocaleTimeString());
      btn.disabled = false;
    });
  }

  // --------------------------------------------------------------------
  // Navigation
  // --------------------------------------------------------------------

  const PAGE_TITLES = {
    overview: "Overview",
    detection: "Detection",
    "root-cause": "Root Cause",
    "event-analyzer": "Event Analyzer",
    api: "API",
    system: "System",
  };

  function initNavigation() {
    const navItems = safeQueryAll(".nav-item");
    navItems.forEach(function (item) {
      item.addEventListener("click", function () {
        const targetPage = item.getAttribute("data-page");
        if (!targetPage) return;
        goToPage(targetPage);
      });
    });
  }

  function goToPage(pageName) {
    state.currentPage = pageName;

    safeQueryAll(".nav-item").forEach(function (item) {
      item.classList.toggle("active", item.getAttribute("data-page") === pageName);
    });

    safeQueryAll(".page").forEach(function (section) {
      section.classList.toggle("active", section.getAttribute("data-page") === pageName);
    });

    setText(safeGetElement("topbar-section"), PAGE_TITLES[pageName] || pageName);

    if (pageName === "overview") {
      loadOverviewData();
    } else if (pageName === "api") {
      updateApiOverallStatus(state.healthOk);
    }
  }

  // --------------------------------------------------------------------
  // Refresh button (topbar)
  // --------------------------------------------------------------------

  function initRefreshButton() {
    const btn = safeGetElement("refresh-btn");
    if (!btn) return;

    btn.addEventListener("click", async function () {
      btn.classList.add("spinning");
      await checkHealth();
      if (state.currentPage === "overview") {
        await loadOverviewData();
      }
      setTimeout(function () {
        btn.classList.remove("spinning");
      }, 700);
      showToast("Status refreshed", "success");
    });
  }

  // --------------------------------------------------------------------
  // Init
  // --------------------------------------------------------------------

  function init() {
    initNavigation();
    initRefreshButton();
    initDetectionPage();
    initRootCausePage();
    initEventAnalyzerPage();
    initApiPage();
    initSystemPage();
    runBootSequence();
    // Overview data loads once the health check (kicked off at the end of
    // the boot sequence) resolves; kick it off here too so it isn't empty
    // if the user is already on the overview page.
    setTimeout(loadOverviewData, 2400);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
