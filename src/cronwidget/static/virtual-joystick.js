// VirtualJoystick — on-screen thumbstick anywidget
// Syncs x/y floats (-1..1) with spring-back-to-center
// Uses pointer events for unified mouse + touch handling

function render({ model, el }) {
  const size = model.get("size") || 200;
  const knobRatio = model.get("knob_ratio") || 0.35;
  const deadzone = model.get("deadzone") || 0.0;
  const springBack = model.get("spring_back");

  const radius = size / 2;
  const knobRadius = radius * knobRatio;
  const maxTravel = radius - knobRadius;

  const wrapper = document.createElement("div");
  wrapper.className = "vj-wrapper";
  wrapper.style.width = size + "px";
  wrapper.style.height = size + "px";

  const canvas = document.createElement("canvas");
  canvas.width = size * 2; // 2x for retina
  canvas.height = size * 2;
  canvas.style.width = size + "px";
  canvas.style.height = size + "px";
  wrapper.appendChild(canvas);

  const ctx = canvas.getContext("2d");
  const scale = 2;

  let knobX = 0;
  let knobY = 0;
  let dragging = false;
  let localUpdate = false;
  let animFrame = null;

  // Read CSS custom properties for theme-aware canvas drawing
  function getColor(prop, fallback) {
    const v = getComputedStyle(wrapper).getPropertyValue(prop).trim();
    return v || fallback;
  }

  function toNormalized(px, py) {
    let nx = maxTravel > 0 ? px / maxTravel : 0;
    let ny = maxTravel > 0 ? -py / maxTravel : 0; // flip Y: up is positive
    const mag = Math.sqrt(nx * nx + ny * ny);
    if (mag < deadzone) return { x: 0, y: 0 };
    if (deadzone > 0 && mag > 0) {
      const remapped = (mag - deadzone) / (1 - deadzone);
      const factor = remapped / mag;
      nx *= factor;
      ny *= factor;
    }
    return { x: Math.max(-1, Math.min(1, nx)), y: Math.max(-1, Math.min(1, ny)) };
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cx = radius * scale;
    const cy = radius * scale;

    // Base circle
    ctx.beginPath();
    ctx.arc(cx, cy, (radius - 2) * scale, 0, Math.PI * 2);
    ctx.fillStyle = getColor("--vj-base", "#e5e7eb");
    ctx.fill();
    ctx.strokeStyle = getColor("--vj-base-stroke", "#d1d5db");
    ctx.lineWidth = 1.5 * scale;
    ctx.stroke();

    // Deadzone ring
    if (deadzone > 0) {
      ctx.beginPath();
      ctx.arc(cx, cy, maxTravel * deadzone * scale, 0, Math.PI * 2);
      ctx.strokeStyle = getColor("--vj-deadzone", "rgba(107,114,128,0.25)");
      ctx.lineWidth = 1 * scale;
      ctx.setLineDash([4 * scale, 4 * scale]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Crosshair
    const chColor = getColor("--vj-crosshair", "rgba(107,114,128,0.2)");
    ctx.strokeStyle = chColor;
    ctx.lineWidth = 1 * scale;
    ctx.beginPath();
    ctx.moveTo(cx, cy - (radius - 12) * scale);
    ctx.lineTo(cx, cy + (radius - 12) * scale);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(cx - (radius - 12) * scale, cy);
    ctx.lineTo(cx + (radius - 12) * scale, cy);
    ctx.stroke();

    // Line from center to knob
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + knobX * scale, cy + knobY * scale);
    ctx.strokeStyle = getColor("--vj-line", "rgba(59,130,246,0.25)");
    ctx.lineWidth = 2 * scale;
    ctx.stroke();

    // Knob shadow
    ctx.beginPath();
    ctx.arc(cx + knobX * scale, cy + knobY * scale + 2 * scale, knobRadius * scale, 0, Math.PI * 2);
    ctx.fillStyle = getColor("--vj-knob-shadow", "rgba(0,0,0,0.12)");
    ctx.fill();

    // Knob gradient
    const fromColor = dragging
      ? getColor("--vj-knob-active-from", "#60a5fa")
      : getColor("--vj-knob-from", "#3b82f6");
    const toColor = dragging
      ? getColor("--vj-knob-active-to", "#3b82f6")
      : getColor("--vj-knob-to", "#2563eb");
    const gradient = ctx.createRadialGradient(
      cx + knobX * scale - knobRadius * 0.3 * scale,
      cy + knobY * scale - knobRadius * 0.3 * scale,
      0,
      cx + knobX * scale,
      cy + knobY * scale,
      knobRadius * scale
    );
    gradient.addColorStop(0, fromColor);
    gradient.addColorStop(1, toColor);
    ctx.beginPath();
    ctx.arc(cx + knobX * scale, cy + knobY * scale, knobRadius * scale, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();

    // Knob border
    const strokeColor = dragging
      ? getColor("--vj-knob-active-stroke", "#93c5fd")
      : getColor("--vj-knob-stroke", "#3b82f6");
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2 * scale;
    ctx.stroke();

    // Knob highlight
    ctx.beginPath();
    ctx.arc(
      cx + knobX * scale - knobRadius * 0.2 * scale,
      cy + knobY * scale - knobRadius * 0.2 * scale,
      knobRadius * 0.3 * scale,
      0, Math.PI * 2
    );
    ctx.fillStyle = getColor("--vj-knob-highlight", "rgba(255,255,255,0.25)");
    ctx.fill();
  }

  function syncModel() {
    const n = toNormalized(knobX, knobY);
    const rx = Math.round(n.x * 1000) / 1000;
    const ry = Math.round(n.y * 1000) / 1000;
    localUpdate = true;
    model.set("x", rx);
    model.set("y", ry);
    model.save_changes();
  }

  function getPointerPos(e) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left - radius,
      y: e.clientY - rect.top - radius,
    };
  }

  function clampToCircle(px, py) {
    const dist = Math.sqrt(px * px + py * py);
    if (dist > maxTravel) {
      const ratio = maxTravel / dist;
      return { x: px * ratio, y: py * ratio };
    }
    return { x: px, y: py };
  }

  // Pointer events — unified mouse + touch
  function onPointerDown(e) {
    e.preventDefault();
    canvas.setPointerCapture(e.pointerId);
    dragging = true;
    const pos = getPointerPos(e);
    const clamped = clampToCircle(pos.x, pos.y);
    knobX = clamped.x;
    knobY = clamped.y;
    syncModel();
    draw();
  }

  function onPointerMove(e) {
    if (!dragging) return;
    e.preventDefault();
    const pos = getPointerPos(e);
    const clamped = clampToCircle(pos.x, pos.y);
    knobX = clamped.x;
    knobY = clamped.y;
    syncModel();
    draw();
  }

  function onPointerUp(e) {
    if (!dragging) return;
    dragging = false;
    canvas.releasePointerCapture(e.pointerId);
    if (springBack) {
      animateSpringBack();
    } else {
      draw();
    }
  }

  function animateSpringBack() {
    const startX = knobX;
    const startY = knobY;
    const duration = 150;
    const startTime = performance.now();

    function step(now) {
      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / duration);
      const ease = 1 - Math.pow(1 - t, 3); // ease-out cubic
      knobX = startX * (1 - ease);
      knobY = startY * (1 - ease);
      syncModel();
      draw();
      if (t < 1) {
        animFrame = requestAnimationFrame(step);
      }
    }
    if (animFrame) cancelAnimationFrame(animFrame);
    animFrame = requestAnimationFrame(step);
  }

  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointercancel", onPointerUp);

  // Value labels
  const labelDiv = document.createElement("div");
  labelDiv.className = "vj-labels";
  const xLabel = document.createElement("span");
  const yLabel = document.createElement("span");
  xLabel.className = "vj-label";
  yLabel.className = "vj-label";
  labelDiv.appendChild(xLabel);
  labelDiv.appendChild(yLabel);
  wrapper.appendChild(labelDiv);

  function updateLabels() {
    xLabel.textContent = `X: ${(model.get("x") || 0).toFixed(3)}`;
    yLabel.textContent = `Y: ${(model.get("y") || 0).toFixed(3)}`;
  }

  // Listen for Python-side changes
  function onModelChange() {
    if (localUpdate) { localUpdate = false; return; }
    if (dragging) return;
    const nx = model.get("x") || 0;
    const ny = model.get("y") || 0;
    knobX = nx * maxTravel;
    knobY = -ny * maxTravel;
    draw();
    updateLabels();
  }

  model.on("change:x", () => { updateLabels(); onModelChange(); });
  model.on("change:y", () => { updateLabels(); onModelChange(); });

  // Initial state
  const initX = model.get("x") || 0;
  const initY = model.get("y") || 0;
  knobX = initX * maxTravel;
  knobY = -initY * maxTravel;
  draw();
  updateLabels();

  el.appendChild(wrapper);

  // Cleanup
  return () => {
    canvas.removeEventListener("pointerdown", onPointerDown);
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerup", onPointerUp);
    canvas.removeEventListener("pointercancel", onPointerUp);
    if (animFrame) cancelAnimationFrame(animFrame);
  };
}

export default { render };
