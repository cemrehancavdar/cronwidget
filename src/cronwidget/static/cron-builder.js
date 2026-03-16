// CronBuilder — Tangle-style interactive cron expression
// Click on a segment group cycles mode (every / step / value / range).
// Drag/scroll on number sub-spans adjusts values within mode.
// Range "1-5" has two independent drag targets.

const FIELDS = [
  { label: "minute", min: 0, max: 59, steps: [2, 3, 5, 10, 15, 20, 30] },
  { label: "hour",   min: 0, max: 23, steps: [2, 3, 4, 6, 8, 12] },
  { label: "day",    min: 1, max: 31, steps: [2, 5, 10, 15] },
  { label: "month",  min: 1, max: 12, steps: [2, 3, 4, 6],
    names: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"] },
  { label: "weekday", min: 0, max: 6, steps: [1],
    names: ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"] },
];

function parseToken(token) {
  if (token === "*") return { mode: "every" };
  if (/^\*\/\d+$/.test(token)) return { mode: "step", step: parseInt(token.slice(2), 10) };
  if (/^\d+-\d+$/.test(token)) {
    const [a, b] = token.split("-").map(Number);
    return { mode: "range", from: a, to: b };
  }
  const nums = token.split(",").map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
  if (nums.length >= 1) return { mode: "value", val: nums[0] };
  return { mode: "every" };
}

function buildToken(parsed) {
  switch (parsed.mode) {
    case "every": return "*";
    case "step":  return `*/${parsed.step}`;
    case "value": return String(parsed.val);
    case "range": return `${parsed.from}-${parsed.to}`;
    default: return "*";
  }
}

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

function cycleMode(parsed, field) {
  switch (parsed.mode) {
    case "every": return { mode: "step", step: field.steps[0] };
    case "step":  return { mode: "value", val: field.min };
    case "value": return { mode: "range", from: field.min, to: Math.min(field.min + 5, field.max) };
    case "range": return { mode: "every" };
    default:      return { mode: "every" };
  }
}

function valueName(v, field) {
  return field.names ? (field.names[v - field.min] || String(v)) : String(v);
}

function describeModeShort(parsed, field) {
  switch (parsed.mode) {
    case "every": return "every";
    case "step":  return `every ${parsed.step}`;
    case "value": return valueName(parsed.val, field);
    case "range": return `${valueName(parsed.from, field)} to ${valueName(parsed.to, field)}`;
    default: return "";
  }
}

function describeExpression(tokens) {
  if (tokens.length !== 5) return "";
  const descs = tokens.map((t, i) => {
    const f = FIELDS[i];
    const p = parseToken(t);
    switch (p.mode) {
      case "every": return `every ${f.label}`;
      case "step":  return `every ${p.step} ${f.label}s`;
      case "value": {
        if (f.names) return f.names[p.val - f.min] || String(p.val);
        if (i === 0) return `at minute ${p.val}`;
        if (i === 1) return `at ${p.val}:00`;
        if (i === 2) return `on the ${ordinal(p.val)}`;
        return String(p.val);
      }
      case "range": {
        const a = f.names ? f.names[p.from - f.min] : p.from;
        const b = f.names ? f.names[p.to - f.min] : p.to;
        if (i === 1) return `${a}:00 to ${b}:00`;
        return `${a} through ${b}`;
      }
      default: return t;
    }
  });
  const [min, hr, dom, mon, dow] = descs;
  let s = capitalize(min);
  if (tokens[1] !== "*") s += `, ${hr}`;
  if (tokens[2] !== "*") s += `, ${dom}`;
  if (tokens[3] !== "*") s += `, ${mon}`;
  if (tokens[4] !== "*") s += `, ${dow}`;
  return s;
}

function ordinal(n) {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

function fieldMatches(value, token, min) {
  if (token === "*") return true;
  if (token.includes("/")) {
    const step = parseInt(token.split("/")[1], 10);
    return (value - min) % step === 0;
  }
  if (token.includes("-")) {
    const [a, b] = token.split("-").map(Number);
    return value >= a && value <= b;
  }
  return token.split(",").map(Number).includes(value);
}

function getNextRuns(tokens, count) {
  if (tokens.length !== 5) return [];
  const runs = [];
  const d = new Date();
  d.setSeconds(0, 0);
  d.setMinutes(d.getMinutes() + 1);
  for (let i = 0; i < 525600 && runs.length < count; i++) {
    if (
      fieldMatches(d.getMinutes(), tokens[0], 0) &&
      fieldMatches(d.getHours(), tokens[1], 0) &&
      fieldMatches(d.getDate(), tokens[2], 1) &&
      fieldMatches(d.getMonth() + 1, tokens[3], 1) &&
      fieldMatches(d.getDay(), tokens[4], 0)
    ) runs.push(new Date(d));
    d.setMinutes(d.getMinutes() + 1);
  }
  return runs;
}

function formatRun(d) {
  const days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  return `${days[d.getDay()]} ${h}:${m}`;
}

function makeTangle(text, nudgeFn) {
  const span = document.createElement("span");
  span.className = "cb-tangle";
  span.tabIndex = 0;
  span.textContent = text;

  const PX_PER_STEP = 20;
  let dragging = false;
  let wasDragged = false;
  let startX = 0;
  let cumSteps = 0;

  span.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    e.stopPropagation();
    span.setPointerCapture(e.pointerId);
    dragging = true;
    wasDragged = false;
    startX = e.clientX;
    cumSteps = 0;
    span.classList.add("is-active");
  });

  span.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    e.preventDefault();
    const delta = e.clientX - startX;
    if (Math.abs(delta) > 3) wasDragged = true;
    const newSteps = Math.round(delta / PX_PER_STEP);
    while (cumSteps < newSteps) { cumSteps++; nudgeFn(1); }
    while (cumSteps > newSteps) { cumSteps--; nudgeFn(-1); }
  });

  span.addEventListener("pointerup", (e) => {
    if (!dragging) return;
    dragging = false;
    span.releasePointerCapture(e.pointerId);
    span.classList.remove("is-active");
    if (wasDragged) e.stopPropagation();
  });

  span.addEventListener("pointercancel", () => {
    dragging = false;
    span.classList.remove("is-active");
  });

  span.addEventListener("wheel", (e) => {
    e.preventDefault();
    e.stopPropagation();
    nudgeFn(e.deltaY > 0 ? 1 : -1);
  }, { passive: false });

  span.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      nudgeFn(e.key === "ArrowRight" ? 1 : -1);
    }
  });

  span.addEventListener("click", (e) => {
    if (wasDragged) {
      e.stopPropagation();
      wasDragged = false;
    }
  });

  return span;
}

function makeStatic(text) {
  const span = document.createElement("span");
  span.className = "cb-static";
  span.textContent = text;
  return span;
}

function render({ model, el }) {
  const wrapper = document.createElement("div");
  wrapper.className = "cron-builder";

  const exprRow = document.createElement("div");
  exprRow.className = "cb-expr-row";

  let localUpdate = false;
  const columns = [];

  function getTokens() {
    return (model.get("expression") || "* * * * *").trim().split(/\s+/);
  }

  function sync(tokens) {
    const expr = tokens.join(" ");
    localUpdate = true;
    model.set("expression", expr);
    model.save_changes();
    updateInfo(tokens);
  }

  function lightUpdate(colData, fi) {
    const tokens = getTokens();
    const field = FIELDS[fi];
    const token = tokens[fi] || "*";
    const parsed = parseToken(token);
    colData.modeEl.textContent = describeModeShort(parsed, field);

    const tangles = colData.container.querySelectorAll(".cb-tangle");
    switch (parsed.mode) {
      case "every":
        if (tangles[0]) tangles[0].textContent = "*";
        break;
      case "step":
        if (tangles[0]) tangles[0].textContent = String(parsed.step);
        break;
      case "value":
        if (tangles[0]) tangles[0].textContent = String(parsed.val);
        break;
      case "range":
        if (tangles[0]) tangles[0].textContent = String(parsed.from);
        if (tangles[1]) tangles[1].textContent = String(parsed.to);
        break;
    }
  }

  function rebuildColumn(colData, fi) {
    const field = FIELDS[fi];
    const tokens = getTokens();
    const token = tokens[fi] || "*";
    const parsed = parseToken(token);
    const container = colData.container;

    container.innerHTML = "";

    switch (parsed.mode) {
      case "every": {
        container.appendChild(makeTangle("*", () => {}));
        break;
      }
      case "step": {
        container.appendChild(makeStatic("*/"));
        container.appendChild(makeTangle(String(parsed.step), (dir) => {
          const t = getTokens();
          const p = parseToken(t[fi]);
          if (p.mode !== "step") return;
          const steps = field.steps;
          const idx = steps.indexOf(p.step);
          let newStep;
          if (idx >= 0) {
            const ni = clamp(idx + dir, 0, steps.length - 1);
            newStep = steps[ni];
          } else {
            newStep = clamp(p.step + dir, 1, field.max);
          }
          t[fi] = `*/${newStep}`;
          sync(t);
          lightUpdate(colData, fi);
        }));
        break;
      }
      case "value": {
        container.appendChild(makeTangle(String(parsed.val), (dir) => {
          const t = getTokens();
          const p = parseToken(t[fi]);
          if (p.mode !== "value") return;
          const v = clamp(p.val + dir, field.min, field.max);
          t[fi] = String(v);
          sync(t);
          lightUpdate(colData, fi);
        }));
        break;
      }
      case "range": {
        container.appendChild(makeTangle(String(parsed.from), (dir) => {
          const t = getTokens();
          const p = parseToken(t[fi]);
          if (p.mode !== "range") return;
          const newFrom = clamp(p.from + dir, field.min, p.to);
          t[fi] = `${newFrom}-${p.to}`;
          sync(t);
          lightUpdate(colData, fi);
        }));
        container.appendChild(makeStatic("-"));
        container.appendChild(makeTangle(String(parsed.to), (dir) => {
          const t = getTokens();
          const p = parseToken(t[fi]);
          if (p.mode !== "range") return;
          const newTo = clamp(p.to + dir, p.from, field.max);
          t[fi] = `${p.from}-${newTo}`;
          sync(t);
          lightUpdate(colData, fi);
        }));
        break;
      }
    }

    colData.modeEl.textContent = describeModeShort(parsed, field);
  }

  for (let fi = 0; fi < 5; fi++) {
    const field = FIELDS[fi];

    const col = document.createElement("span");
    col.className = "cb-tangle-col";

    const container = document.createElement("span");
    container.className = "cb-tangle-container";

    const modeEl = document.createElement("span");
    modeEl.className = "cb-tangle-mode";

    const unitEl = document.createElement("span");
    unitEl.className = "cb-tangle-unit";
    unitEl.textContent = field.label;

    col.appendChild(container);
    col.appendChild(modeEl);
    col.appendChild(unitEl);
    exprRow.appendChild(col);

    const colData = { col, container, modeEl, unitEl, fieldIdx: fi };
    columns.push(colData);

    // Click on container cycles mode
    container.addEventListener("click", () => {
      const t = getTokens();
      const p = parseToken(t[fi]);
      const next = cycleMode(p, field);
      t[fi] = buildToken(next);
      sync(t);
      rebuildColumn(colData, fi);
    });

    container.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        const t = getTokens();
        const p = parseToken(t[fi]);
        const next = cycleMode(p, field);
        t[fi] = buildToken(next);
        sync(t);
        rebuildColumn(colData, fi);
      }
    });
  }

  wrapper.appendChild(exprRow);

  const descEl = document.createElement("div");
  descEl.className = "cb-desc";
  wrapper.appendChild(descEl);

  const nextEl = document.createElement("div");
  nextEl.className = "cb-next";
  wrapper.appendChild(nextEl);

  function updateInfo(tokens) {
    descEl.textContent = describeExpression(tokens);
    const runs = getNextRuns(tokens, 3);
    nextEl.textContent = runs.length
      ? "Next  " + runs.map(formatRun).join("  ·  ")
      : "";
  }

  columns.forEach((c, i) => rebuildColumn(c, i));
  updateInfo(getTokens());

  model.on("change:expression", () => {
    if (localUpdate) { localUpdate = false; return; }
    columns.forEach((c, i) => rebuildColumn(c, i));
    updateInfo(getTokens());
  });

  el.appendChild(wrapper);
}

export default { render };
