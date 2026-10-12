const ROLES = {
  status: ["sensor", ["washing_modes"]],
  phase: ["sensor", ["program_phases_wm", "program_phases_td"]],
  remaining: ["sensor", ["remaining_time"]],
  runningProgram: ["sensor", ["programs_wm", "programs_td"]],
  program: ["select", ["programs_wm", "programs_td"]],
  favourite: ["select", ["favourite_program"]],
  temperature: ["select", ["temperature"]],
  spin: ["select", ["spin_speed"]],
  dryLevel: ["select", ["dry_levels"]],
  start: ["switch", ["washing_machine", "washer_dryer", "tumble_dryer"]],
  pause: ["switch", ["pause"]],
  doorLock: ["binary_sensor", ["door_lock"]],
};

const STAGES = {
  wash: ["weighting", "heating", "washing", "steam", "tumbling", "refresh"],
  rinse: ["rinse"],
  spin: ["spin"],
  dry: ["drying"],
};

const TEXT = {
  en: {
    wash: "Wash", rinse: "Rinse", spin: "Spin", dry: "Dry",
    left: "min left", ends: "Ends at", idle: "Ready", program: "Program",
    favourites: "Favourites", recent: "Recent", start: "Start", stop: "Stop", pause: "Pause",
    resume: "Resume", remoteOff: "Remote start is off on the machine. Press its remote button to control it from here.",
    noDevice: "Choose a washing machine, washer-dryer or dryer from the hOn integration in the card settings.",
    temperature: "Temperature", spinSpeed: "Spin",
  },
  cs: {
    wash: "Praní", rinse: "Máchání", spin: "Ždímání", dry: "Sušení",
    left: "min zbývá", ends: "Konec v", idle: "Připraveno", program: "Program",
    favourites: "Oblíbené", recent: "Naposledy", start: "Spustit", stop: "Zastavit", pause: "Pozastavit",
    resume: "Pokračovat", remoteOff: "Dálkové ovládání je na pračce vypnuté. Zapněte ho tlačítkem na pračce.",
    noDevice: "V nastavení karty vyberte pračku, pračku se sušičkou nebo sušičku z integrace hOn.",
    temperature: "Teplota", spinSpeed: "Odstředění",
  },
};

const ICONS = {
  play: "M8 5.14v13.72a1 1 0 0 0 1.52.85l10.9-6.86a1 1 0 0 0 0-1.7L9.52 4.29A1 1 0 0 0 8 5.14Z",
  pause: "M7 5h3.5v14H7zM13.5 5H17v14h-3.5z",
  stop: "M7 7h10v10H7z",
  star: "M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z",
  history: "M13 3a9 9 0 0 0-9 9H1l3.9 3.9.1.1L9 12H6a7 7 0 1 1 2.05 4.95l-1.42 1.42A9 9 0 1 0 13 3Zm-1 5v5l4.25 2.52.77-1.28-3.52-2.09V8H12Z",
  lock: "M12 17a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm6-9h-1V6a5 5 0 0 0-10 0v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2ZM9 6a3 3 0 0 1 6 0v2H9V6Z",
  chevron: "M7 10l5 5 5-5z",
};

const svgIcon = (path, size = 20) =>
  `<svg viewBox="0 0 24 24" width="${size}" height="${size}" aria-hidden="true"><path d="${path}" fill="currentColor"/></svg>`;

const escape = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class HonWasherCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.device_id) {
      throw new Error("Set device_id to an hOn washing machine, washer-dryer or dryer.");
    }
    this._config = { layout: "full", recent: 2, show_favourites: true, ...config };
    this._recent = [];
    this._recentKey = undefined;
  }

  static getStubConfig(hass) {
    const entity = Object.values(hass.entities || {}).find(
      (e) => e.platform === "hon" && e.entity_id.startsWith("select.") && /^programs_(wm|td)$/.test(e.translation_key || ""),
    );
    return { device_id: entity ? entity.device_id : "", layout: "compact" };
  }

  getCardSize() {
    return this._config?.layout === "compact" ? 3 : 9;
  }

  set hass(hass) {
    this._hass = hass;
    this._refreshRecent();
    const signature = this._signature();
    if (signature === this._lastSignature) return;
    this._lastSignature = signature;
    this._render();
  }

  _t(key) {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").split("-")[0];
    return (TEXT[lang] || TEXT.en)[key] || TEXT.en[key];
  }

  _entities() {
    const found = {};
    const entries = Object.values(this._hass.entities || {}).filter(
      (e) => e.device_id === this._config.device_id && e.platform === "hon",
    );
    for (const [role, [domain, keys]] of Object.entries(ROLES)) {
      const entry = entries.find((e) => e.entity_id.startsWith(`${domain}.`) && keys.includes(e.translation_key));
      if (entry && this._hass.states[entry.entity_id]) found[role] = this._hass.states[entry.entity_id];
    }
    return found;
  }

  _signature() {
    if (!this._hass || !this._config) return "";
    const e = this._entities();
    return JSON.stringify([
      this._hass.locale?.language,
      this._recent,
      Object.values(e).map((s) => [s.entity_id, s.state, s.attributes.options?.length]),
    ]);
  }

  async _refreshRecent() {
    if (!this._hass?.callWS || !this._config?.recent) return;
    const key = this._entities().status?.state;
    if (key === this._recentKey) return;
    this._recentKey = key;
    try {
      const result = await this._hass.callWS({ type: "hon/recent_programs", device_id: this._config.device_id });
      this._recent = result.programs || [];
    } catch (error) {
      this._recent = [];
    }
    this._lastSignature = undefined;
    this.hass = this._hass;
  }

  _format(stateObj, value) {
    if (!stateObj) return "";
    if (this._hass.formatEntityState) return this._hass.formatEntityState(stateObj, value);
    return value ?? stateObj.state;
  }

  _usable(stateObj) {
    return stateObj && !["unavailable", "unknown"].includes(stateObj.state);
  }

  _call(domain, service, stateObj, data = {}) {
    if (!stateObj) return;
    this._hass.callService(domain, service, { entity_id: stateObj.entity_id, ...data });
  }

  _state() {
    const e = this._entities();
    const status = e.status?.state;
    const running = status === "running";
    const paused = status === "pause";
    const active = running || paused || status === "scheduled";
    const remaining = Number(e.remaining?.state);
    const hasTime = active && Number.isFinite(remaining) && remaining > 0;
    const stage = active ? Object.keys(STAGES).find((s) => STAGES[s].includes(e.phase?.state)) : undefined;
    const stages = Object.keys(STAGES).filter((s) => s !== "dry" || e.dryLevel);
    const options = e.program?.attributes.options || [];
    const favourites = e.favourite?.attributes.options || [];
    return {
      e, running, paused, active, remaining, hasTime, stage, stages, favourites,
      reached: stage ? stages.indexOf(stage) : -1,
      ends: hasTime
        ? new Date(Date.now() + remaining * 60000).toLocaleTimeString(this._hass.locale?.language, { hour: "2-digit", minute: "2-digit" })
        : "",
      subtitle: active
        ? [this._format(e.status), this._usable(e.phase) ? this._format(e.phase) : ""].filter(Boolean).join(", ")
        : this._usable(e.status) ? this._format(e.status) : this._t("idle"),
      programLabel: active && this._usable(e.runningProgram) ? this._format(e.runningProgram) : this._format(e.program),
      programs: options.filter((o) => !o.startsWith("iot_") && !favourites.includes(o)),
      recent: this._recent.filter((o) => options.includes(o)).slice(0, this._config.recent),
      controllable: this._usable(e.start),
    };
  }

  _porthole(s) {
    return `<svg viewBox="0 0 200 200" class="drum" aria-hidden="true">
      <defs>
        <clipPath id="glass"><circle cx="100" cy="100" r="72"/></clipPath>
        <linearGradient id="water" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" style="stop-color: var(--hon-water-top)"/>
          <stop offset="1" style="stop-color: var(--hon-water-bottom)"/>
        </linearGradient>
      </defs>
      <circle cx="100" cy="100" r="94" class="rim"/>
      <circle cx="100" cy="100" r="80" class="seal"/>
      <circle cx="100" cy="100" r="72" class="glass"/>
      <g clip-path="url(#glass)">
        <g class="water level-${s.stage || (s.active ? "wash" : "idle")}">
          <path class="wave back" d="M-100 0 Q-75 -8 -50 0 T0 0 T50 0 T100 0 T150 0 T200 0 T250 0 T300 0 V200 H-100 Z"/>
          <path class="wave front" d="M-100 4 Q-75 -6 -50 4 T0 4 T50 4 T100 4 T150 4 T200 4 T250 4 T300 4 V200 H-100 Z"/>
        </g>
      </g>
      <circle cx="100" cy="100" r="72" class="shine"/>
    </svg>`;
  }

  _stagesBar(s) {
    return `<ol class="stages">
      ${s.stages.map((stage, i) => `<li class="${i < s.reached ? "done" : ""} ${i === s.reached ? "now" : ""}"><span class="bar"></span><span class="label">${escape(this._t(stage))}</span></li>`).join("")}
    </ol>`;
  }

  _recentChips(s) {
    if (!s.recent.length) return "";
    const current = s.active ? s.e.runningProgram?.state : s.e.program?.state;
    return `<div class="recent" role="group" aria-label="${escape(this._t("recent"))}">
      ${s.recent.map((o) => `<button class="pick" aria-pressed="${o === current}" data-select="${escape(s.e.program.entity_id)}" data-option="${escape(o)}" ${s.active ? "disabled" : ""}>${svgIcon(ICONS.history, 16)}<span>${escape(this._format(s.e.program, o))}</span></button>`).join("")}
    </div>`;
  }

  _chips(stateObj, label, disabled) {
    const options = stateObj?.attributes.options || [];
    if (options.length < 2 || options.length > 6) return "";
    return `<div class="choice" role="radiogroup" aria-label="${escape(label)}">
      ${options.map((o) => `<button class="seg" role="radio" aria-checked="${o === stateObj.state}" data-select="${escape(stateObj.entity_id)}" data-option="${escape(o)}" ${disabled ? "disabled" : ""}>${escape(this._format(stateObj, o))}</button>`).join("")}
    </div>`;
  }

  _actions(s) {
    if (s.active) {
      return `<button class="primary" data-action="${s.paused ? "resume" : "pause"}" ${this._usable(s.e.pause) ? "" : "disabled"}>${svgIcon(s.paused ? ICONS.play : ICONS.pause)}${escape(this._t(s.paused ? "resume" : "pause"))}</button>
        <button class="secondary" data-action="stop" ${s.controllable ? "" : "disabled"}>${svgIcon(ICONS.stop)}${escape(this._t("stop"))}</button>`;
    }
    return `<button class="primary wide" data-action="start" ${s.controllable ? "" : "disabled"}>${svgIcon(ICONS.play)}${escape(this._t("start"))}</button>`;
  }

  _notice(s) {
    return s.e.start && !s.controllable ? `<p class="notice">${escape(this._t("remoteOff"))}</p>` : "";
  }

  _full(s, name) {
    const { e } = s;
    return `<ha-card class="full ${s.running ? "running" : ""}">
      <header>
        <h2>${escape(name)}</h2>
        <p class="subtitle">${escape(s.subtitle)}</p>
      </header>
      <div class="porthole" role="img" aria-label="${escape(s.subtitle)}">
        ${this._porthole(s)}
        <div class="readout">
          ${s.hasTime
            ? `<span class="minutes">${s.remaining}</span><span class="unit">${escape(this._t("left"))}</span>`
            : `<span class="unit idle">${escape(s.active ? this._format(e.status) : this._t("idle"))}</span>`}
        </div>
        ${e.doorLock?.state === "on" ? `<span class="lock" title="${escape(this._format(e.doorLock))}">${svgIcon(ICONS.lock, 16)}</span>` : ""}
      </div>
      ${s.hasTime ? `<p class="ends">${escape(this._t("ends"))} <strong>${escape(s.ends)}</strong></p>` : ""}
      ${this._stagesBar(s)}
      <label class="program ${s.active ? "locked" : ""}">
        <span class="visually-hidden">${escape(this._t("program"))}</span>
        <select data-program ${s.active || !e.program ? "disabled" : ""}>
          ${s.favourites.length ? `<optgroup label="${escape(this._t("favourites"))}">${s.favourites.map((o) => `<option value="${escape(o)}" ${o === e.program?.state ? "selected" : ""}>★ ${escape(o)}</option>`).join("")}</optgroup>` : ""}
          <optgroup label="${escape(this._t("program"))}">
            ${s.programs.map((o) => `<option value="${escape(o)}" ${o === e.program?.state ? "selected" : ""}>${escape(this._format(e.program, o))}</option>`).join("")}
          </optgroup>
        </select>
        <span class="current">${escape(s.programLabel)}</span>
        ${svgIcon(ICONS.chevron, 18)}
      </label>
      ${this._recentChips(s)}
      ${this._config.show_favourites && s.favourites.length ? `
        <div class="favourites" aria-label="${escape(this._t("favourites"))}">
          ${s.favourites.map((o) => `<button class="fav" aria-pressed="${o === e.program?.state}" data-select="${escape(e.favourite.entity_id)}" data-option="${escape(o)}" ${s.active ? "disabled" : ""}>${svgIcon(ICONS.star, 14)}${escape(o)}</button>`).join("")}
        </div>` : ""}
      ${!s.active ? `<div class="settings">${this._chips(e.temperature, this._t("temperature"))}${this._chips(e.spin, this._t("spinSpeed"))}${this._chips(e.dryLevel, this._t("dry"))}</div>` : ""}
      <div class="actions">${this._actions(s)}</div>
      ${this._notice(s)}
    </ha-card>`;
  }

  _compact(s, name) {
    const action = s.active ? (s.paused ? "resume" : "pause") : "start";
    const enabled = s.active ? this._usable(s.e.pause) : s.controllable;
    const status = this._usable(s.e.status) ? this._format(s.e.status) : this._t("idle");
    const line = s.hasTime
      ? `${this._t("ends")} ${s.ends}`
      : s.active || s.recent.length ? status : `${status}, ${s.programLabel}`;
    return `<ha-card class="compact ${s.running ? "running" : ""}">
      <div class="row">
        <div class="mini" role="img" aria-label="${escape(s.subtitle)}">
          ${this._porthole(s)}
          ${s.hasTime ? `<span class="mini-time">${s.remaining}</span>` : ""}
        </div>
        <div class="titles">
          <h2>${escape(name)}</h2>
          <p class="subtitle">${escape(line)}</p>
        </div>
        <button class="round" data-action="${action}" ${enabled ? "" : "disabled"} aria-label="${escape(this._t(action))}" title="${escape(this._t(action))}">
          ${svgIcon(action === "pause" ? ICONS.pause : ICONS.play, 24)}
        </button>
      </div>
      ${s.active ? this._stagesBar(s) : ""}
      ${this._recentChips(s)}
      ${this._notice(s)}
    </ha-card>`;
  }

  _render() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const s = this._state();
    if (!s.e.program && !s.e.status) {
      this.shadowRoot.innerHTML = `${STYLE}<ha-card><p class="empty">${escape(this._t("noDevice"))}</p></ha-card>`;
      return;
    }
    const device = this._hass.devices?.[this._config.device_id];
    const name = this._config.name || device?.name_by_user || device?.name || "";
    this.shadowRoot.innerHTML = STYLE + (this._config.layout === "compact" ? this._compact(s, name) : this._full(s, name));

    this.shadowRoot.querySelectorAll("[data-option]").forEach((el) =>
      el.addEventListener("click", () =>
        this._call("select", "select_option", this._hass.states[el.dataset.select], { option: el.dataset.option }),
      ),
    );
    this.shadowRoot.querySelector("[data-program]")?.addEventListener("change", (ev) =>
      this._call("select", "select_option", s.e.program, { option: ev.target.value }),
    );
    this.shadowRoot.querySelectorAll("[data-action]").forEach((el) =>
      el.addEventListener("click", () => {
        const action = el.dataset.action;
        if (action === "start") this._call("switch", "turn_on", s.e.start);
        if (action === "stop") this._call("switch", "turn_off", s.e.start);
        if (action === "pause") this._call("switch", "turn_on", s.e.pause);
        if (action === "resume") this._call("switch", "turn_off", s.e.pause);
      }),
    );
  }
}

const STYLE = `<style>
  :host {
    --hon-action: var(--primary-color, #0a6cff);
    --hon-on-action: var(--text-primary-color, #fff);
    --hon-ink: var(--primary-text-color, #1b1f24);
    --hon-muted: var(--secondary-text-color, #69707a);
    --hon-well: var(--secondary-background-color, #eef1f5);
    --hon-line: var(--divider-color, rgba(120, 130, 145, 0.25));
    --hon-steel: color-mix(in srgb, var(--hon-ink) 14%, var(--card-background-color, #fff));
    --hon-water-top: #7cc6ef;
    --hon-water-bottom: #2f86c8;
  }
  ha-card { padding: 20px 20px 18px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px; color: var(--hon-ink); container-type: inline-size; }
  ha-card.compact { padding: 14px 16px; gap: 12px; }
  header { text-align: center; }
  h2 { margin: 0; font-size: 1.15rem; font-weight: 600; line-height: 1.3; }
  .subtitle { margin: 2px 0 0; color: var(--hon-muted); font-size: 0.9rem; }
  .empty { margin: 0; color: var(--hon-muted); }

  .porthole { position: relative; width: min(100%, 248px); margin: 2px auto 0; aspect-ratio: 1; }
  .drum { width: 100%; height: 100%; display: block; }
  .rim { fill: var(--hon-steel); }
  .seal { fill: color-mix(in srgb, var(--hon-ink) 70%, transparent); opacity: 0.85; }
  .glass { fill: color-mix(in srgb, var(--hon-water-top) 16%, var(--card-background-color, #fff)); }
  .shine { fill: none; stroke: rgba(255, 255, 255, 0.35); stroke-width: 3; stroke-dasharray: 60 400; stroke-dashoffset: -250; }
  .water { transition: transform 1.2s ease; }
  .water.level-idle { transform: translateY(200px); }
  .water.level-wash { transform: translateY(126px); }
  .water.level-rinse { transform: translateY(136px); }
  .water.level-spin { transform: translateY(158px); }
  .water.level-dry { transform: translateY(170px); }
  .wave { fill: url(#water); }
  .wave.back { opacity: 0.45; }
  .running .wave.front { animation: slosh 3.2s linear infinite; }
  .running .wave.back { animation: slosh 5.4s linear infinite reverse; }
  .running .level-spin .wave { animation-duration: 0.9s; }
  @keyframes slosh { to { transform: translateX(-100px); } }
  .readout { position: absolute; inset: 0 0 16% 0; display: grid; place-content: center; gap: 2px; text-align: center; pointer-events: none; }
  .minutes { font-size: 3.1rem; font-weight: 600; line-height: 1; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
  .unit { color: var(--hon-ink); font-size: 0.85rem; opacity: 0.8; }
  .unit.idle { font-size: 1.05rem; font-weight: 500; opacity: 0.75; }
  .lock { position: absolute; right: 18%; top: 12%; color: var(--hon-muted); }
  .ends { margin: -4px 0 0; text-align: center; color: var(--hon-muted); font-size: 0.9rem; }
  .ends strong { color: var(--hon-ink); font-weight: 600; }

  .stages { list-style: none; margin: 0; padding: 0; display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: 6px; }
  .stages li { display: grid; gap: 6px; text-align: center; font-size: 0.8rem; color: var(--hon-muted); }
  .bar { height: 4px; border-radius: 2px; background: var(--hon-well); }
  .stages .done .bar { background: color-mix(in srgb, var(--hon-action) 45%, var(--hon-well)); }
  .stages .now .bar { background: var(--hon-action); }
  .stages .now { color: var(--hon-ink); font-weight: 600; }

  .program { position: relative; display: flex; align-items: center; gap: 8px; min-height: 48px; padding: 0 14px; border-radius: 14px; background: var(--hon-well); cursor: pointer; }
  .program select { position: absolute; inset: 0; opacity: 0; cursor: pointer; font-size: 16px; }
  .program .current { flex: 1; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .program svg { color: var(--hon-muted); flex: none; }
  .program.locked { cursor: default; }
  .program.locked svg { visibility: hidden; }
  .program:focus-within { outline: 2px solid var(--hon-action); outline-offset: 2px; }

  .recent { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: 8px; }
  .pick { display: flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 0 12px; border-radius: 12px; border: 1px solid var(--hon-line); background: none; color: var(--hon-ink); font: inherit; font-size: 0.92rem; font-weight: 500; cursor: pointer; }
  .pick span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pick svg { flex: none; color: var(--hon-muted); }
  .pick[aria-pressed="true"] { border-color: var(--hon-action); background: color-mix(in srgb, var(--hon-action) 12%, transparent); }
  .pick[aria-pressed="true"] svg { color: var(--hon-action); }

  .favourites { display: flex; gap: 8px; overflow-x: auto; padding: 2px 24px 2px 2px; margin: -4px -2px 0; scrollbar-width: none; mask-image: linear-gradient(to right, #000 calc(100% - 28px), transparent); }
  .fav { flex: none; display: inline-flex; align-items: center; gap: 6px; min-height: 36px; padding: 0 14px; border-radius: 18px; border: 1px solid var(--hon-line); background: none; color: var(--hon-ink); font: inherit; font-size: 0.88rem; cursor: pointer; }
  .fav svg { color: #e2a52b; }
  .fav[aria-pressed="true"] { background: color-mix(in srgb, var(--hon-action) 12%, transparent); border-color: var(--hon-action); }

  .settings { display: grid; gap: 8px; }
  .settings:empty { display: none; }
  .choice { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); padding: 3px; border-radius: 12px; background: var(--hon-well); }
  .seg { min-height: 36px; padding: 0 4px; border: 0; border-radius: 9px; background: none; color: var(--hon-muted); font: inherit; font-size: 0.84rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer; }
  .seg[aria-checked="true"] { background: var(--card-background-color, #fff); color: var(--hon-ink); font-weight: 600; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12); }

  .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .actions button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 52px; border-radius: 14px; font: inherit; font-size: 1rem; font-weight: 600; cursor: pointer; }
  .primary { border: 0; background: var(--hon-action); color: var(--hon-on-action); }
  .primary.wide { grid-column: 1 / -1; }
  .secondary { border: 1px solid var(--hon-line); background: var(--hon-well); color: var(--hon-ink); }

  .row { display: grid; grid-template-columns: 64px minmax(0, 1fr) auto; align-items: center; gap: 14px; }
  .mini { position: relative; width: 64px; height: 64px; }
  .mini .shine { display: none; }
  .mini-time { position: absolute; inset: 0; display: grid; place-content: center; font-size: 1.15rem; font-weight: 700; font-variant-numeric: tabular-nums; text-shadow: 0 0 6px var(--card-background-color, #fff); }
  .titles h2 { font-size: 1.05rem; }
  .titles .subtitle { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .round { width: 52px; height: 52px; border-radius: 50%; border: 0; display: grid; place-items: center; background: var(--hon-action); color: var(--hon-on-action); cursor: pointer; }
  .compact .stages li { gap: 4px; font-size: 0.74rem; }

  button:disabled { opacity: 0.45; cursor: not-allowed; }
  button:focus-visible { outline: 2px solid var(--hon-action); outline-offset: 2px; }
  .notice { margin: -2px 0 0; color: var(--hon-muted); font-size: 0.85rem; text-align: center; }
  .visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

  @container (max-width: 360px) {
    ha-card.full { padding: 16px 14px 14px; }
    .seg { font-size: 0.74rem; padding: 0 1px; }
    .stages li { font-size: 0.74rem; }
  }
  @media (prefers-reduced-motion: reduce) {
    .running .wave { animation: none !important; }
    .water { transition: none; }
  }
</style>`;

const register = () => {
  if (customElements.get("hon-washer-card")) return;
  customElements.define("hon-washer-card", HonWasherCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "hon-washer-card",
    name: "hOn washing machine",
    description: "Program, recent programs, favourites, progress and start/pause for an hOn washing machine, washer-dryer or dryer.",
    preview: true,
  });
};

// Home Assistant swaps in a scoped custom-element registry while its app loads;
// a card defined before that is invisible to the dashboard.
if (document.querySelector("home-assistant")) {
  customElements.whenDefined("home-assistant").then(register);
} else {
  register();
}
