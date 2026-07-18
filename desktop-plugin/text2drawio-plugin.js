"use strict";
(() => {
  // src/api-client.ts
  var ApiError = class extends Error {
    constructor(status, payload) {
      const message = String(payload.message || `Request failed with status ${status}`);
      const details = Array.isArray(payload.details) ? payload.details.filter((item) => typeof item === "string").slice(0, 5) : [];
      super(details.length && !details.every((item) => message.includes(item)) ? `${message}
${details.join("\n")}` : message);
      this.status = status;
      this.payload = payload;
    }
  };
  var AgentApiClient = class {
    constructor(baseUrl = "http://127.0.0.1:8765", timeoutMs = 6e5) {
      this.baseUrl = baseUrl;
      this.timeoutMs = timeoutMs;
    }
    health() {
      return this.request("/health", { method: "GET" });
    }
    generate(payload) {
      return this.request("/api/v1/diagrams/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    }
    async request(path, init) {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), this.timeoutMs);
      try {
        const response = await fetch(`${this.baseUrl}${path}`, { ...init, signal: controller.signal });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new ApiError(response.status, payload);
        return payload;
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          throw new Error("Agent request timed out");
        }
        throw error;
      } finally {
        window.clearTimeout(timeout);
      }
    }
  };

  // src/drawio-adapter.ts
  var DrawioAdapter = class {
    constructor(ui) {
      this.ui = ui;
    }
    currentXml() {
      const model = this.ui.editor.graph.getModel();
      const codec = new mxCodec();
      return mxUtils.getXml(codec.encode(model));
    }
    selectedCellsJson() {
      const cells = this.ui.editor.graph.getSelectionCells();
      return JSON.stringify(
        cells.map((cell) => ({
          id: cell.id,
          value: typeof cell.value === "string" ? cell.value : "",
          style: cell.style || "",
          vertex: Boolean(cell.vertex),
          edge: Boolean(cell.edge),
          geometry: cell.geometry ? {
            x: cell.geometry.x,
            y: cell.geometry.y,
            width: cell.geometry.width,
            height: cell.geometry.height
          } : null
        }))
      );
    }
    importXml(xml, replaceSelection) {
      const document2 = mxUtils.parseXml(xml);
      const modelElement = document2.getElementsByTagName("mxGraphModel")[0];
      if (!modelElement) throw new Error("Generated file does not contain mxGraphModel");
      const codec = new mxCodec(document2);
      const importedModel = codec.decode(modelElement);
      const importedRoot = importedModel.getRoot();
      const importedLayer = importedModel.getChildAt(importedRoot, 0);
      const cells = importedModel.getChildren(importedLayer);
      if (!cells.length) throw new Error("Generated diagram contains no editable cells");
      const graph = this.ui.editor.graph;
      const model = graph.getModel();
      model.beginUpdate();
      try {
        if (replaceSelection) {
          const selection = graph.getSelectionCells();
          if (selection.length) graph.removeCells(selection);
        }
        const inserted = graph.importCells(cells, 20, 20);
        graph.setSelectionCells(inserted);
        if (inserted[0]) graph.scrollCellToVisible(inserted[0]);
        return inserted.length;
      } finally {
        model.endUpdate();
      }
    }
  };

  // src/styles.ts
  var SIDEBAR_CSS = `
.text2drawio-root { --accent:#6c5ce7; --accent-soft:#f0edff; --text:#202123; --muted:#6b7280; --line:#e5e7eb; color:var(--text); font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif; }
.text2drawio-root,.text2drawio-root * { box-sizing:border-box; }
.text2drawio-root .agent { display:flex; flex-direction:column; height:min(820px,calc(100vh - 138px)); min-height:580px; background:#fff; border:1px solid #dde1e7; border-radius:16px; overflow:hidden; box-shadow:0 8px 28px rgba(31,41,55,.06); }
.text2drawio-root .header { display:flex; align-items:center; justify-content:space-between; min-height:64px; padding:0 18px; border-bottom:1px solid #eceff3; }
.text2drawio-root .brand { font-size:18px; font-weight:720; letter-spacing:-.025em; }
.text2drawio-root .status { display:flex; align-items:center; gap:7px; color:var(--muted); font-size:11px; }
.text2drawio-root .dot { width:8px; height:8px; border-radius:50%; background:#9ca3af; }
.text2drawio-root .dot.ok { background:#45bd78; box-shadow:0 0 0 3px #e9f8ef; }
.text2drawio-root .dot.busy { background:#e7a93b; box-shadow:0 0 0 3px #fff6df; }
.text2drawio-root .dot.error { background:#e46652; box-shadow:0 0 0 3px #fff0ed; }
.text2drawio-root .messages { flex:1; min-height:190px; overflow:auto; padding:18px 16px; background:#fff; }
.text2drawio-root .empty { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:220px; padding:20px; text-align:center; }
.text2drawio-root .empty strong { font-size:19px; font-weight:700; letter-spacing:-.02em; }
.text2drawio-root .empty span { max-width:270px; margin-top:9px; color:var(--muted); font-size:12px; line-height:1.65; }
.text2drawio-root .message { max-width:94%; margin:0 0 12px; padding:11px 13px; border:1px solid var(--line); border-radius:13px; background:#fff; white-space:pre-wrap; overflow-wrap:anywhere; box-shadow:0 1px 2px rgba(31,41,55,.03); }
.text2drawio-root .message.user { margin-left:auto; background:#f1f1f1; border-color:#f1f1f1; }
.text2drawio-root .message.agent { margin-right:auto; }
.text2drawio-root .message.error { color:#8f3123; border-color:#f3b4aa; background:#fff0ed; }
.text2drawio-root .meta { margin-top:7px; padding-top:7px; color:#77808c; border-top:1px solid rgba(148,163,184,.22); font-size:10.5px; line-height:1.5; }
.text2drawio-root .composer-shell { padding:10px 12px 13px; background:#fff; border-top:1px solid #f0f1f3; }
.text2drawio-root .composer { padding:10px 10px 8px; border:1px solid #cfd4dc; border-radius:16px; background:#fff; box-shadow:0 5px 18px rgba(31,41,55,.07); transition:border-color .16s,box-shadow .16s; }
.text2drawio-root .composer:focus-within { border-color:#9f94f1; box-shadow:0 0 0 3px rgba(108,92,231,.09),0 7px 22px rgba(31,41,55,.08); }
.text2drawio-root textarea { display:block; width:100%; min-height:74px; max-height:180px; resize:vertical; padding:2px 3px 8px; color:var(--text); background:#fff; border:0; outline:0; font:400 13px/1.55 inherit; }
.text2drawio-root textarea::placeholder { color:#9299a5; }
.text2drawio-root .toolbar { display:flex; align-items:center; gap:6px; min-width:0; }
.text2drawio-root button,.text2drawio-root select { font:600 11px/1.2 inherit; }
.text2drawio-root button { cursor:pointer; }
.text2drawio-root .icon-button,.text2drawio-root .generate { display:grid; place-items:center; flex:0 0 34px; width:34px; height:34px; padding:0; border-radius:50%; }
.text2drawio-root .icon-button { color:#4b5563; border:1px solid #d8dde4; background:#fff; }
.text2drawio-root .icon-button:hover { background:#f6f7f9; }
.text2drawio-root svg { width:18px; height:18px; fill:none; stroke:currentColor; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }
.text2drawio-root select { min-width:0; height:34px; padding:0 25px 0 9px; color:#4b5563; border:1px solid #dfe3e8; border-radius:10px; background:#f7f7f8; outline:0; text-overflow:ellipsis; }
.text2drawio-root .model-select { flex:1 1 44%; }
.text2drawio-root .theme-select { flex:1 1 44%; }
.text2drawio-root select:focus { border-color:#a89eef; }
.text2drawio-root .generate { margin-left:auto; color:#fff; border:1px solid var(--accent); background:var(--accent); }
.text2drawio-root .generate:hover { background:#5d4bdd; }
.text2drawio-root button:disabled,.text2drawio-root select:disabled,.text2drawio-root textarea:disabled { cursor:default; opacity:.46; }
.text2drawio-root .file-list { display:grid; gap:6px; max-height:82px; margin-bottom:7px; overflow:auto; }
.text2drawio-root .file-list:empty { display:none; }
.text2drawio-root .file-item { display:flex; align-items:center; gap:7px; padding:6px 8px; border:1px solid #e3e6ea; border-radius:9px; background:#f7f7f8; }
.text2drawio-root .file-name { flex:1; min-width:0; overflow:hidden; color:#5d6672; font-size:10.5px; text-overflow:ellipsis; white-space:nowrap; }
.text2drawio-root .remove-file { flex:0 0 auto; width:20px; height:20px; padding:0; color:#7b8490; border:0; border-radius:50%; background:transparent; font-size:17px; line-height:18px; }
.text2drawio-root .remove-file:hover { background:#e7e8eb; }
.text2drawio-root .advanced { margin:8px 2px 0; color:#5f6874; }
.text2drawio-root .advanced summary { width:max-content; cursor:pointer; font-size:11px; font-weight:600; list-style-position:outside; }
.text2drawio-root .options { display:grid; gap:7px; padding:9px 3px 2px; }
.text2drawio-root label { display:flex; align-items:flex-start; gap:8px; color:#606a75; font-size:11px; }
.text2drawio-root input[type=checkbox] { accent-color:var(--accent); margin:2px 0 0; }
.text2drawio-root .insert { width:100%; min-height:35px; margin-top:9px; color:#fff; border:1px solid var(--accent); border-radius:10px; background:var(--accent); }
.text2drawio-root .file-limit { margin-top:7px; color:#9299a5; font-size:9.5px; text-align:center; }
@media (max-width:340px) { .text2drawio-root .toolbar { flex-wrap:wrap; } .text2drawio-root .model-select,.text2drawio-root .theme-select { flex:1 1 calc(50% - 22px); } }
`;

  // src/sidebar.ts
  var DEFAULT_SUPPORTED_EXTENSIONS = [
    ".pdf",
    ".xlsx",
    ".xlsm",
    ".xls",
    ".csv",
    ".tsv",
    ".docx",
    ".pptx",
    ".txt",
    ".md",
    ".json",
    ".xml"
  ];
  var DEFAULT_THEMES = [
    ["default", "\u9ED8\u8BA4 \xB7 \u667A\u80FD\u5747\u8861"],
    ["carbon-blue", "Carbon \u4E13\u4E1A\u84DD"],
    ["material-purple", "Material \u6E05\u65B0\u7D2B"],
    ["colorbrewer-green", "ColorBrewer \u6570\u636E\u7EFF"],
    ["tableau-orange", "Tableau \u5546\u52A1\u6A59"],
    ["accessible-contrast", "\u65E0\u969C\u788D\u9AD8\u5BF9\u6BD4"]
  ];
  var TRANSLATIONS = {
    zh: {
      connecting: "\u6B63\u5728\u8FDE\u63A5",
      emptyTitle: "\u5C06\u4F60\u7684\u60F3\u6CD5\u8F6C\u5316\u4E3A\u56FE\u793A",
      emptyBody: "\u8F93\u5165\u8981\u6C42\u6216\u6DFB\u52A0\u53C2\u8003\u6587\u4EF6\uFF0C\u751F\u6210\u53EF\u7F16\u8F91\u7684 draw.io \u77E2\u91CF\u56FE\u3002",
      promptAria: "\u7ED8\u56FE\u8981\u6C42",
      promptPlaceholder: "\u63CF\u8FF0\u4F60\u60F3\u751F\u6210\u7684\u56FE\u793A\u2026",
      addFile: "\u6DFB\u52A0 PDF\u3001Excel\u3001Word \u7B49\u53C2\u8003\u6587\u4EF6",
      selectModel: "\u9009\u62E9 DeepSeek \u6A21\u578B",
      serverDefault: "\u8DDF\u968F\u670D\u52A1\u9ED8\u8BA4",
      selectTheme: "\u9009\u62E9\u5E03\u5C40\u914D\u8272\u6A21\u677F",
      generate: "\u751F\u6210\u56FE\u793A",
      advanced: "\u9AD8\u7EA7\u9009\u9879",
      enhance: "\u81EA\u52A8\u589E\u5F3A\u4E3A\u4E13\u4E1A\u7ED8\u56FE\u89C4\u683C",
      nodeImages: "\u4E3A\u4E3B\u8981\u8282\u70B9\u751F\u6210 AI \u5C0F\u914D\u56FE",
      defaultStyle: "\u65E0\u81EA\u5B9A\u4E49\u53C2\u8003\u65F6\u4F7F\u7528\u9ED8\u8BA4\u79D1\u7814\u98CE\u683C",
      includeCanvas: "\u5305\u542B\u5F53\u524D\u753B\u5E03\u548C\u9009\u4E2D\u5BF9\u8C61\u4E0A\u4E0B\u6587",
      replaceSelection: "\u63D2\u5165\u65F6\u66FF\u6362\u5F53\u524D\u9009\u4E2D\u5BF9\u8C61",
      insert: "\u63D2\u5165\u753B\u5E03",
      localFiles: "\u53C2\u8003\u6587\u4EF6\u4EC5\u5728\u672C\u673A\u89E3\u6790",
      max: "\u6700\u591A",
      each: "\u5355\u4E2A",
      connected: "\u670D\u52A1\u5DF2\u8FDE\u63A5",
      offline: "\u79BB\u7EBF\u8349\u7A3F\u6A21\u5F0F",
      imageApi: "\u8BF7\u5728 Text2Draw.io \u7BA1\u7406\u5668\u4E2D\u914D\u7F6E\u56FE\u7247 API",
      unavailable: "\u670D\u52A1\u4E0D\u53EF\u7528",
      unavailableHelp: "\u65E0\u6CD5\u8FDE\u63A5\u672C\u5730\u670D\u52A1\u3002\u8BF7\u6253\u5F00 Text2Draw.io \u7BA1\u7406\u5668\u5E76\u70B9\u51FB\u201C\u542F\u52A8\u672C\u5730\u670D\u52A1\u201D\u3002",
      promptRequired: "\u8BF7\u5148\u8F93\u5165\u7ED8\u56FE\u8981\u6C42\u3002",
      readingFiles: "\u6B63\u5728\u8BFB\u53D6\u53C2\u8003\u6587\u4EF6",
      attachments: "\u9644\u4EF6",
      enhanced: "\u5DF2\u589E\u5F3A\u4E3A\u4E13\u4E1A\u7ED8\u56FE\u89C4\u683C",
      nodes: "\u4E2A\u8282\u70B9",
      edges: "\u6761\u8FDE\u7EBF",
      generated: "\u56FE\u793A\u5DF2\u751F\u6210",
      confirmDefault: "\u9700\u8981\u786E\u8BA4\u9ED8\u8BA4\u79D1\u7814\u98CE\u683C\u3002\u8BF7\u5728\u9AD8\u7EA7\u9009\u9879\u4E2D\u52FE\u9009\u540E\u91CD\u8BD5\u3002",
      failed: "\u751F\u6210\u5931\u8D25",
      insertedPrefix: "\u5DF2\u63D2\u5165",
      insertedSuffix: "\u4E2A\u53EF\u7F16\u8F91\u5BF9\u8C61\uFF0C\u53EF\u4F7F\u7528 draw.io \u64A4\u9500\u6216\u7EE7\u7EED\u7F16\u8F91\u3002",
      insertedCanvas: "\u5DF2\u63D2\u5165\u753B\u5E03",
      insertFailed: "\u63D2\u5165\u5931\u8D25",
      planning: "\u6B63\u5728\u89C4\u5212\u56FE\u793A",
      unsupported: "\u4E0D\u652F\u6301\u6587\u4EF6",
      exceeds: "\u8D85\u8FC7\u5355\u6587\u4EF6",
      limit: "\u9650\u5236\u3002",
      maxFiles: "\u4E00\u6B21\u6700\u591A\u9009\u62E9",
      files: "\u4E2A\u6587\u4EF6\u3002",
      remove: "\u79FB\u9664",
      cannotRead: "\u65E0\u6CD5\u8BFB\u53D6\u672C\u5730\u6587\u4EF6",
      cannotEncode: "\u65E0\u6CD5\u7F16\u7801\u672C\u5730\u6587\u4EF6"
    },
    en: {
      connecting: "Connecting",
      emptyTitle: "Turn your ideas into diagrams",
      emptyBody: "Describe what you need or attach reference files to create an editable draw.io vector diagram.",
      promptAria: "Diagram request",
      promptPlaceholder: "Describe the diagram you want to create\u2026",
      addFile: "Add PDF, Excel, Word, or other reference files",
      selectModel: "Select DeepSeek model",
      serverDefault: "Use server default",
      selectTheme: "Select layout and color theme",
      generate: "Generate diagram",
      advanced: "Advanced options",
      enhance: "Enhance into a professional diagram specification",
      nodeImages: "Generate small AI illustrations for key nodes",
      defaultStyle: "Use the default research style without custom references",
      includeCanvas: "Include the current canvas and selected objects as context",
      replaceSelection: "Replace selected objects when inserting",
      insert: "Insert into canvas",
      localFiles: "Reference files are parsed locally",
      max: "up to",
      each: "each",
      connected: "Connected",
      offline: "Offline draft mode",
      imageApi: "Configure an image API in Text2Draw.io Manager",
      unavailable: "Service unavailable",
      unavailableHelp: "Cannot connect to the local service. Open Text2Draw.io Manager and click Start Local Service.",
      promptRequired: "Enter a diagram request first.",
      readingFiles: "Reading reference files",
      attachments: "Attachments",
      enhanced: "Enhanced into a professional diagram specification",
      nodes: "nodes",
      edges: "edges",
      generated: "Diagram generated",
      confirmDefault: "Confirm the default research style under Advanced options, then try again.",
      failed: "Generation failed",
      insertedPrefix: "Inserted",
      insertedSuffix: "editable objects. You can undo or continue editing in draw.io.",
      insertedCanvas: "Inserted into canvas",
      insertFailed: "Insertion failed",
      planning: "Planning diagram",
      unsupported: "Unsupported file",
      exceeds: "exceeds the per-file",
      limit: "limit.",
      maxFiles: "You can select up to",
      files: "files at a time.",
      remove: "Remove",
      cannotRead: "Cannot read local file",
      cannotEncode: "Cannot encode local file"
    }
  };
  var ENGLISH_THEME_NAMES = {
    default: "Default \xB7 Smart Balance",
    "carbon-blue": "Carbon Professional Blue",
    "material-purple": "Material Fresh Purple",
    "colorbrewer-green": "ColorBrewer Data Green",
    "tableau-orange": "Tableau Business Orange",
    "accessible-contrast": "Accessible High Contrast"
  };
  var AgentSidebar = class {
    constructor(ui) {
      this.ui = ui;
      this.language = typeof mxLanguage !== "undefined" && mxLanguage === "en" ? "en" : "zh";
      this.api = new AgentApiClient();
      this.lastResult = null;
      this.selectedFiles = [];
      this.supportedExtensions = DEFAULT_SUPPORTED_EXTENSIONS;
      this.maxAttachmentFiles = 5;
      this.maxAttachmentBytes = 15 * 1024 * 1024;
      this.adapter = new DrawioAdapter(ui);
    }
    t(key) {
      return TRANSLATIONS[this.language][key] || TRANSLATIONS.zh[key] || key;
    }
    mount(container) {
      container.textContent = "";
      this.root = document.createElement("div");
      this.root.className = "text2drawio-root";
      this.root.innerHTML = `<style>${SIDEBAR_CSS}</style>
      <section class="agent">
        <header class="header">
          <div class="brand">Text2Draw.io</div>
          <div class="status"><i class="dot"></i><span>${this.t("connecting")}</span></div>
        </header>
        <div class="messages" aria-live="polite">
          <div class="empty">
            <strong>${this.t("emptyTitle")}</strong>
            <span>${this.t("emptyBody")}</span>
          </div>
        </div>
        <div class="composer-shell">
          <div class="composer">
            <textarea aria-label="${this.t("promptAria")}" placeholder="${this.t("promptPlaceholder")}"></textarea>
            <input class="file-input" type="file" multiple hidden accept="${DEFAULT_SUPPORTED_EXTENSIONS.join(",")}">
            <div class="file-list" aria-live="polite"></div>
            <div class="toolbar">
              <button class="icon-button file-button" type="button" title="${this.t("addFile")}" aria-label="${this.t("addFile")}">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8.5 12.5 14.8 6.2a3 3 0 0 1 4.2 4.2l-8.3 8.3a5 5 0 0 1-7.1-7.1l8.1-8.1"/></svg>
              </button>
              <select class="model-select" aria-label="${this.t("selectModel")}" title="${this.t("selectModel")}">
                <option value="">${this.t("serverDefault")}</option>
              </select>
              <select class="theme-select" aria-label="${this.t("selectTheme")}" title="${this.t("selectTheme")}">
                ${DEFAULT_THEMES.map(([id, name]) => `<option value="${id}">${this.language === "en" ? ENGLISH_THEME_NAMES[id] : name}</option>`).join("")}
              </select>
              <button class="generate" type="button" title="${this.t("generate")} (\u2318/Ctrl + Enter)" aria-label="${this.t("generate")}">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 7-7 7 7M12 5v14"/></svg>
              </button>
            </div>
          </div>
          <details class="advanced">
            <summary>${this.t("advanced")}</summary>
            <div class="options">
              <label><input class="enhance-prompt" type="checkbox" checked><span>${this.t("enhance")}</span></label>
              <label><input class="node-images" type="checkbox"><span>${this.t("nodeImages")}</span></label>
              <label><input class="default-style" type="checkbox" checked><span>${this.t("defaultStyle")}</span></label>
              <label><input class="include-canvas" type="checkbox"><span>${this.t("includeCanvas")}</span></label>
              <label><input class="replace-selection" type="checkbox"><span>${this.t("replaceSelection")}</span></label>
            </div>
          </details>
          <button class="insert" type="button" disabled>${this.t("insert")}</button>
          <div class="file-limit">${this.t("localFiles")} \xB7 ${this.t("max")} 5 \xB7 ${this.t("each")} 15MB</div>
        </div>
      </section>`;
      container.appendChild(this.root);
      this.messages = this.required(".messages");
      this.statusDot = this.required(".dot");
      this.statusText = this.required(".status span");
      this.prompt = this.required("textarea");
      this.generateButton = this.required(".generate");
      this.insertButton = this.required(".insert");
      this.defaultStyle = this.required(".default-style");
      this.includeCanvas = this.required(".include-canvas");
      this.replaceSelection = this.required(".replace-selection");
      this.enhancePrompt = this.required(".enhance-prompt");
      this.generateNodeImages = this.required(".node-images");
      this.modelSelect = this.required(".model-select");
      this.themeSelect = this.required(".theme-select");
      this.fileInput = this.required(".file-input");
      this.fileButton = this.required(".file-button");
      this.fileList = this.required(".file-list");
      this.isolateInteractiveEvents();
      this.generateButton.addEventListener("click", () => void this.generate());
      this.insertButton.addEventListener("click", () => this.insert());
      this.fileButton.addEventListener("click", () => this.fileInput.click());
      this.fileInput.addEventListener("change", () => {
        this.addSelectedFiles(Array.from(this.fileInput.files || []));
        this.fileInput.value = "";
      });
      this.prompt.addEventListener("keydown", (event) => {
        if ((event.metaKey || event.ctrlKey) && event.key === "Enter") void this.generate();
      });
      void this.connect();
    }
    isolateInteractiveEvents() {
      const eventTypes = [
        "keydown",
        "keyup",
        "keypress",
        "mousedown",
        "mouseup",
        "pointerdown",
        "pointerup",
        "click",
        "dblclick",
        "change",
        "input"
      ];
      for (const type of eventTypes) {
        this.root.addEventListener(type, (event) => {
          const target = event.target;
          if (target instanceof Element && target.closest("textarea, input, button, label, select, summary")) {
            event.stopPropagation();
          }
        });
      }
    }
    async connect() {
      try {
        const health = await this.api.health();
        this.applyServerConfig(health);
        this.setStatus("ok", health.deepseek_configured ? this.t("connected") : this.t("offline"));
        if (!health.node_image_generation_configured) {
          this.generateNodeImages.disabled = true;
          this.generateNodeImages.title = this.t("imageApi");
        }
        if (health.skill.default_confirmation_required) this.defaultStyle.checked = true;
      } catch {
        this.setStatus("error", this.t("unavailable"));
        this.addMessage("error", this.t("unavailableHelp"));
      }
    }
    applyServerConfig(health) {
      var _a;
      if (health.attachments) {
        this.supportedExtensions = health.attachments.supported_extensions;
        this.maxAttachmentFiles = health.attachments.max_files;
        this.maxAttachmentBytes = health.attachments.max_file_bytes;
        this.fileInput.accept = this.supportedExtensions.join(",");
        this.required(".file-limit").textContent = `${this.t("localFiles")} \xB7 ${this.t("max")} ${this.maxAttachmentFiles} \xB7 ${this.t("each")} ${this.formatBytes(this.maxAttachmentBytes)}`;
      }
      const modelNames = {
        "deepseek-v4-flash": "DeepSeek V4 Flash",
        "deepseek-v4-pro": "DeepSeek V4 Pro"
      };
      for (const model of health.deepseek_models || []) {
        const option = document.createElement("option");
        option.value = model;
        option.textContent = modelNames[model] || model;
        this.modelSelect.appendChild(option);
      }
      this.modelSelect.value = health.deepseek_model || "";
      if ((_a = health.style_templates) == null ? void 0 : _a.length) {
        this.themeSelect.textContent = "";
        for (const theme of health.style_templates) {
          const option = document.createElement("option");
          option.value = theme.id;
          option.textContent = this.language === "en" ? ENGLISH_THEME_NAMES[theme.id] || theme.name : theme.name;
          option.title = theme.description;
          this.themeSelect.appendChild(option);
        }
      }
    }
    async generate() {
      const text = this.prompt.value.trim();
      if (!text) return this.addMessage("error", this.t("promptRequired"));
      this.busy(true);
      try {
        if (this.selectedFiles.length) this.setStatus("busy", this.t("readingFiles"));
        const attachments = await Promise.all(this.selectedFiles.map((file) => this.encodeFile(file)));
        this.addMessage(
          "user",
          text,
          this.selectedFiles.length ? `${this.t("attachments")}: ${this.selectedFiles.map((file) => file.name).join(", ")}` : ""
        );
        this.lastResult = await this.api.generate({
          prompt: text,
          use_default_style: this.defaultStyle.checked,
          current_xml: this.includeCanvas.checked ? this.adapter.currentXml() : "",
          selected_cells: this.includeCanvas.checked ? this.adapter.selectedCellsJson() : "",
          enhance_prompt: this.enhancePrompt.checked,
          generate_node_images: this.generateNodeImages.checked,
          model: this.modelSelect.value,
          style_template: this.themeSelect.value,
          attachments
        });
        const result = this.lastResult;
        if (result.prompt_was_enhanced) {
          this.addMessage("agent", this.t("enhanced"), result.enhanced_prompt.slice(0, 900));
        }
        this.addMessage(
          "agent",
          `${result.diagram_ir.title}
${result.diagram_ir.nodes.length} ${this.t("nodes")} \xB7 ${result.diagram_ir.edges.length} ${this.t("edges")}`,
          `${this.themeLabel(result.style_template)} \xB7 ${this.modelLabel(result.model_used)}${result.warnings.length ? ` \xB7 ${result.warnings.join(" ")}` : ""}`
        );
        this.insertButton.disabled = false;
        this.setStatus("ok", this.t("generated"));
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          this.addMessage("error", this.t("confirmDefault"));
        } else {
          this.addMessage("error", error instanceof Error ? error.message : this.t("failed"));
        }
        this.setStatus("error", this.t("failed"));
      } finally {
        this.busy(false);
      }
    }
    insert() {
      if (!this.lastResult) return;
      try {
        const count = this.adapter.importXml(this.lastResult.drawio_xml, this.replaceSelection.checked);
        this.addMessage("agent", `${this.t("insertedPrefix")} ${count} ${this.t("insertedSuffix")}`);
        this.setStatus("ok", this.t("insertedCanvas"));
      } catch (error) {
        this.addMessage("error", error instanceof Error ? error.message : this.t("insertFailed"));
        this.setStatus("error", this.t("insertFailed"));
      }
    }
    busy(value) {
      this.generateButton.disabled = value;
      this.prompt.disabled = value;
      this.fileInput.disabled = value;
      this.fileButton.disabled = value;
      this.modelSelect.disabled = value;
      this.themeSelect.disabled = value;
      this.fileList.querySelectorAll("button").forEach((button) => {
        button.disabled = value;
      });
      if (value) this.setStatus("busy", this.t("planning"));
    }
    setStatus(kind, text) {
      this.statusDot.className = `dot ${kind}`;
      this.statusText.textContent = text;
    }
    addMessage(kind, text, meta = "") {
      var _a;
      (_a = this.messages.querySelector(".empty")) == null ? void 0 : _a.remove();
      const item = document.createElement("div");
      item.className = `message ${kind}`;
      const content = document.createElement("div");
      content.textContent = text;
      item.appendChild(content);
      if (meta) {
        const detail = document.createElement("div");
        detail.className = "meta";
        detail.textContent = meta;
        item.appendChild(detail);
      }
      this.messages.appendChild(item);
      this.messages.scrollTop = this.messages.scrollHeight;
    }
    required(selector) {
      const element = this.root.querySelector(selector);
      if (!element) throw new Error(`Missing sidebar element: ${selector}`);
      return element;
    }
    addSelectedFiles(files) {
      var _a;
      for (const file of files) {
        const extension = `.${((_a = file.name.split(".").pop()) == null ? void 0 : _a.toLowerCase()) || ""}`;
        if (!this.supportedExtensions.includes(extension)) {
          this.addMessage("error", `${this.t("unsupported")}: ${file.name}`);
          continue;
        }
        if (file.size > this.maxAttachmentBytes) {
          this.addMessage("error", `${file.name} ${this.t("exceeds")} ${this.formatBytes(this.maxAttachmentBytes)} ${this.t("limit")}`);
          continue;
        }
        if (this.selectedFiles.length >= this.maxAttachmentFiles) {
          this.addMessage("error", `${this.t("maxFiles")} ${this.maxAttachmentFiles} ${this.t("files")}`);
          break;
        }
        const duplicate = this.selectedFiles.some((existing) => existing.name === file.name && existing.size === file.size && existing.lastModified === file.lastModified);
        if (!duplicate) this.selectedFiles.push(file);
      }
      this.renderFileList();
    }
    renderFileList() {
      this.fileList.textContent = "";
      this.selectedFiles.forEach((file, index) => {
        const item = document.createElement("div");
        item.className = "file-item";
        const name = document.createElement("span");
        name.className = "file-name";
        name.textContent = `${file.name} \xB7 ${this.formatBytes(file.size)}`;
        name.title = file.name;
        const remove = document.createElement("button");
        remove.className = "remove-file";
        remove.type = "button";
        remove.textContent = "\xD7";
        remove.setAttribute("aria-label", `${this.t("remove")} ${file.name}`);
        remove.addEventListener("click", () => {
          this.selectedFiles.splice(index, 1);
          this.renderFileList();
        });
        item.append(name, remove);
        this.fileList.appendChild(item);
      });
    }
    encodeFile(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error(`${this.t("cannotRead")}: ${file.name}`));
        reader.onload = () => {
          const value = String(reader.result || "");
          const comma = value.indexOf(",");
          if (comma < 0) return reject(new Error(`${this.t("cannotEncode")}: ${file.name}`));
          resolve({ filename: file.name, mime_type: file.type || "application/octet-stream", data_base64: value.slice(comma + 1) });
        };
        reader.readAsDataURL(file);
      });
    }
    modelLabel(id) {
      return id === "deepseek-v4-pro" ? "DeepSeek V4 Pro" : id === "deepseek-v4-flash" ? "DeepSeek V4 Flash" : id;
    }
    themeLabel(id) {
      var _a;
      return ((_a = Array.from(this.themeSelect.options).find((option) => option.value === id)) == null ? void 0 : _a.textContent) || id;
    }
    formatBytes(bytes) {
      if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))}KB`;
      return `${Math.round(bytes / (1024 * 1024))}MB`;
    }
  };

  // src/plugin.ts
  Draw.loadPlugin((ui) => {
    const sidebar = new AgentSidebar(ui);
    ui.sidebar.addPalette("text2drawio-agent", "Text2Draw.io Agent", true, (content) => {
      sidebar.mount(content);
    }, true);
  });
})();
