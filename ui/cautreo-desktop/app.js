/* Cautreo Desktop UI — behavior
   The only moving thing on screen is the body's vitals trace.
   State is one-way: this layer only renders what "the bus" reports. */

(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ───────────────────────────────────────────
     1 · Vitals trace — the living body line
     ─────────────────────────────────────────── */

  var W = 236;
  var H = 52;
  var MID = H / 2;
  var beatW = 44; // one heartbeat of path width

  // One heartbeat: flat, small P, sharp QRS, modest T, flat.
  function beatPath(x) {
    return [
      "L" + (x + 10) + "," + MID,
      "L" + (x + 15) + "," + (MID - 4),
      "L" + (x + 19) + "," + MID,
      "L" + (x + 23) + "," + (MID + 11),
      "L" + (x + 27) + "," + (MID - 17),
      "L" + (x + 31) + "," + MID,
      "L" + (x + 36) + "," + (MID - 6),
      "L" + (x + 40) + "," + MID
    ].join(" ");
  }

  // Build a continuous run of beats wider than the viewbox, for seamless crawl.
  function buildTrace(phase, broken) {
    var d = "M" + (-beatW) + "," + MID;
    for (var x = -beatW; x < W + beatW; x += beatW) {
      var shifted = x + phase;
      if (broken && shifted > W * 0.42 && shifted < W * 0.58) {
        // the gap where the body lost its signal
        d += " L" + (shifted + 34) + "," + MID;
      } else {
        d += " " + beatPath(shifted);
      }
    }
    return d;
  }

  function flatTrace() {
    return "M0," + MID + " L" + W + "," + MID;
  }

  var tracePath = document.getElementById("tracePath");
  var phase = 0;
  var running = false;

  function paintTrace(mode) {
    if (mode === "OFFLINE") {
      tracePath.setAttribute("d", flatTrace());
      return;
    }
    if (mode === "DEGRADED") {
      tracePath.setAttribute("d", buildTrace(phase, true));
      return;
    }
    tracePath.setAttribute("d", buildTrace(phase, false));
  }

  function tick() {
    if (!running) return;
    phase -= 0.55;
    if (phase <= -beatW) phase += beatW;
    paintTrace(currentLink);
    requestAnimationFrame(tick);
  }

  function startTrace() {
    if (reduceMotion) {
      paintTrace(currentLink);
      return;
    }
    if (running) return;
    running = true;
    requestAnimationFrame(tick);
  }

  /* ───────────────────────────────────────────
     2 · Link state machine — never fake a reply
     ─────────────────────────────────────────── */

  // Thanh Thân thể chỉ mang khóa lý do — đúng như contract. Giải thích đầy đủ
  // nằm ở ô nhập và ở bề mặt Hệ thống, không ních hết vào một dòng.
  var REASONS = {
    endpoint_unreachable: "không gọi được endpoint model",
    model_mismatch: "model không đúng như cấu hình",
    engine_unavailable: "cautreo.dll không nạp được",
    permission_denied: "plugin thiếu quyền"
  };

  var REASON_CYCLE = ["endpoint_unreachable", "model_mismatch", "engine_unavailable", "permission_denied"];
  var reasonIndex = 0;
  var currentReason = "";

  // Tên model do host báo qua bus. UI không tự khai tên model.
  var modelLabel = "chưa rõ model";
  var currentLink = "ONLINE";

  var bodyBar = document.getElementById("bodyBar");
  var linkChip = document.getElementById("linkChip");
  var linkName = document.getElementById("linkName");
  var linkReason = document.getElementById("linkReason");
  var composerHint = document.getElementById("composerHint");
  var composerInput = document.getElementById("composerInput");
  var sendBtn = document.getElementById("sendBtn");
  var eyeState = document.getElementById("eyeState");
  var handState = document.getElementById("handState");
  var mOnline = document.getElementById("mOnline");
  var mDegraded = document.getElementById("mDegraded");
  var modelName = document.getElementById("modelName");

  var DEFAULT_HINT = "Lệnh đi qua bus → Python → Cautreo / model. Kết quả trả về luôn mang nhãn nguồn.";
  var OFFLINE_HINT = "Đang offline theo lựa chọn của bạn. Bật lại để đi LINKING → ONLINE, không nhảy thẳng.";

  function setLink(mode, reasonKey, reasonText) {
    currentLink = mode;

    bodyBar.setAttribute("data-link", mode);
    linkChip.setAttribute("data-link", mode);

    if (mode === "DEGRADED") {
      // Ưu tiên lý do host báo qua bus. Chỉ khi không có (chế độ mẫu) mới
      // xoay vòng trong bảng lý do — và đó là dữ liệu mẫu, có ghi rõ.
      var key = reasonKey || REASON_CYCLE[reasonIndex % REASON_CYCLE.length];
      if (!reasonKey) reasonIndex++;
      currentReason = key;
      linkName.textContent = "degraded";
      // Thanh Thân thể chỉ mang khóa lý do — đúng như hợp đồng.
      linkReason.textContent = key;
      // Chip model nói đúng sự thật: tên model vẫn là tên cấu hình, nhưng nó
      // đang không kết nối. Không được để chip này đọc như "đang dùng".
      if (modelName) modelName.textContent = modelLabel + " · chưa nối";
      // Lời giải thích LẤY TỪ HOST qua `reason_text`. Bảng REASONS bên dưới chỉ
      // dùng khi không có host (bản mẫu) — UI không tự bịa lời giải thích cho
      // trạng thái của máy thật.
      var explained = reasonText || REASONS[key] || "không rõ lý do";
      composerHint.textContent =
        "Đang degraded — " + explained + ". Ô nhập vẫn nhận lệnh, nhưng chỉ lệnh không cần model được chạy. Mọi kết quả bị dán nhãn nguồn.";
      composerHint.classList.add("is-degraded");
      composerInput.disabled = false;
      composerInput.placeholder = "Lệnh không cần model vẫn chạy được…";
      sendBtn.disabled = false;
      eyeState.textContent = "chỉ mục cục bộ";
      handState.textContent = "chặn lệnh cần model";
    } else if (mode === "OFFLINE") {
      currentReason = "";
      linkName.textContent = "offline";
      linkReason.textContent = "";
      if (modelName) modelName.textContent = "model đã ngắt";
      composerHint.textContent = OFFLINE_HINT;
      composerHint.classList.remove("is-degraded");
      composerInput.disabled = true;
      composerInput.placeholder = "Đang offline — nhập lại khi bật liên kết";
      sendBtn.disabled = true;
      eyeState.textContent = "nghỉ";
      handState.textContent = "nghỉ";
    } else {
      currentReason = "";
      linkName.textContent = "online";
      linkReason.textContent = "";
      if (modelName) modelName.textContent = modelLabel;
      composerHint.textContent = DEFAULT_HINT;
      composerHint.classList.remove("is-degraded");
      composerInput.disabled = false;
      composerInput.placeholder = "Nhập chỉ thị cho ViVy…";
      sendBtn.disabled = false;
      eyeState.textContent = "đang đọc";
      handState.textContent = "đang ghi";
    }

    if (mOnline) mOnline.classList.toggle("live", mode === "ONLINE");
    if (mDegraded) mDegraded.classList.toggle("bad", mode === "DEGRADED");

    var activeSurface = document.querySelector(".surface.is-active");
    document.title = "Cautreo · " +
      (activeSurface ? activeSurface.getAttribute("data-surface") : "giao-tiep") +
      " · " + mode;

    paintTrace(mode);
  }

  // Prototype switch — stands in for what the bus will later report.
  var protoBtns = document.querySelectorAll(".proto-switch button");
  protoBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      protoBtns.forEach(function (b) { b.setAttribute("aria-pressed", "false"); });
      btn.setAttribute("aria-pressed", "true");
      setLink(btn.getAttribute("data-set"));
    });
  });

  var retryBtn = document.getElementById("retryBtn");
  if (retryBtn) {
    retryBtn.addEventListener("click", function () {
      // Recovery path per spec: DEGRADED probes again, then LINKING → ONLINE.
      linkName.textContent = "đang nối lại…";
      linkReason.textContent = "";
      paintTrace("LINKING");
      // Chỉ render state do bus báo — không tự bịa ONLINE.
      if (!bus.live) {
        setLink("DEGRADED", "endpoint_unreachable", "chưa nối bus — không tự chuyển ONLINE");
        return;
      }
      callBus("host.link-probe", {});
    });
  }

  /* ───────────────────────────────────────────
     3 · Surfaces — nav rail switches the workspace
     ─────────────────────────────────────────── */

  var railBtns = document.querySelectorAll(".rail-btn[data-surface]");
  var surfaces = document.querySelectorAll(".surface");
  var dockGroups = document.querySelectorAll(".dock-group");

  function showSurface(name) {
    railBtns.forEach(function (b) {
      if (b.getAttribute("data-surface") === name) {
        b.setAttribute("aria-current", "page");
      } else {
        b.removeAttribute("aria-current");
      }
    });

    surfaces.forEach(function (s) {
      s.classList.toggle("is-active", s.getAttribute("data-surface") === name);
    });

    dockGroups.forEach(function (g) {
      g.hidden = g.getAttribute("data-for") !== name;
    });

    document.title = "Cautreo · " + name + " · " + currentLink;
  }

  railBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      showSurface(btn.getAttribute("data-surface"));
    });
  });

  /* ───────────────────────────────────────────
     4 · Tab groups — panels "đậu" theo nhóm tab
     ─────────────────────────────────────────── */

  function wireTabs(tabSelector, scopeEl) {
    var scope = scopeEl || document;
    var tabs = scope.querySelectorAll(tabSelector);
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        var pane = tab.getAttribute("data-pane");
        var group = tab.closest(".dock-group") || tab.closest(".surface") || document;

        // Only flip within this tab strip's own group.
        var strip = tab.parentElement;
        strip.querySelectorAll("[role='tab']").forEach(function (t) {
          t.setAttribute("aria-selected", t === tab ? "true" : "false");
        });

        group.querySelectorAll("[data-pane-body]").forEach(function (body) {
          // Content panes and dock panes are separate namespaces.
          var isDockPane = body.closest(".dock");
          var isContentPane = body.closest(".content");
          if (isDockPane && tab.closest(".dock")) {
            body.hidden = body.getAttribute("data-pane-body") !== pane;
          } else if (isContentPane && tab.closest(".content-tabs")) {
            body.hidden = body.getAttribute("data-pane-body") !== pane;
          }
        });
      });
    });
  }

  wireTabs(".dock-tab");
  wireTabs(".content-tab");

  /* ───────────────────────────────────────────
     5 · Composer — receipts, not self-praise
     ─────────────────────────────────────────── */

  var stream = document.getElementById("stream");

  function clockNow() {
    var t = new Date();
    return [t.getHours(), t.getMinutes(), t.getSeconds()]
      .map(function (n) { return String(n).padStart(2, "0"); })
      .join(":");
  }

  // Luồng tư duy: mỗi đoạn một khối `<details>` TỰ ĐỘNG THU GỌN (không có
  // atribut `open`). Người dùng bấm mới mở. Đây là chữ CỦA MODEL — không cắt
  // bỏ, chỉ không bày ra trước mặt khi chưa ai hỏi.
  function buildThinking(thinking) {
    var parts = Array.isArray(thinking)
      ? thinking
      : typeof thinking === "string" && thinking.trim() ? [thinking] : [];
    if (!parts.length) return null;

    var wrap = document.createElement("div");
    wrap.className = "thinking-stack";
    parts.forEach(function (part) {
      var det = document.createElement("details");
      det.className = "thinking";

      var sum = document.createElement("summary");
      sum.className = "thinking-summary";
      sum.textContent = "Suy nghĩ của model · " + String(part).length + " ký tự";

      var pre = document.createElement("div");
      pre.className = "thinking-body";
      pre.textContent = part;

      det.appendChild(sum);
      det.appendChild(pre);
      wrap.appendChild(det);
    });
    return wrap;
  }

  function addEntry(kind, src, body, variant, thinking) {
    var article = document.createElement("article");
    article.className = "entry" + (variant ? " " + variant : "");

    var meta = document.createElement("div");
    meta.className = "entry-meta";

    var kindEl = document.createElement("span");
    kindEl.className = "entry-kind";
    kindEl.textContent = kind;

    var timeEl = document.createElement("span");
    timeEl.className = "entry-time";
    timeEl.textContent = clockNow();

    meta.appendChild(kindEl);

    // Nhãn nguồn chỉ dành cho kết quả đi qua bus. Lời của người dùng không phải "nguồn".
    if (src) {
      var srcEl = document.createElement("span");
      srcEl.className = "src";
      srcEl.setAttribute("data-src", src);
      srcEl.textContent = src;
      meta.appendChild(srcEl);
    }

    meta.appendChild(timeEl);

    var bodyEl = document.createElement("div");
    bodyEl.className = "entry-body";
    bodyEl.textContent = body;

    // Khối suy nghĩ nằm SAU câu trả lời, thu gọn sẵn.
    var thinkingEl = buildThinking(thinking);
    if (thinkingEl) bodyEl.appendChild(thinkingEl);

    article.appendChild(meta);
    article.appendChild(bodyEl);
    stream.appendChild(article);
    article.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
  }

  // Host assigns the label at the bus. The UI never invents one.
  function sendCommand(text) {
    addEntry("chỉ thị của bạn", null, text, "is-tool");

    if (currentLink === "OFFLINE") {
      return; // input is disabled; nothing to do
    }

    if (bus.live) {
      // Có bus thật: chỉ điều hướng tới method có sẵn. Không tự sinh kết quả nào.
      var routed = routeCommand(text);
      if (routed.badJson) {
        // Gọi method nhưng JSON tham số sai — nói thẳng, không biến thành câu hỏi.
        addEntry(
          "tham số sai",
          null,
          "Đọc được tên method " + routed.method + " nhưng khối JSON phía sau không hợp lệ. Không có lệnh nào được gửi đi.",
          "is-error"
        );
        return;
      }
      callBus(routed.method, routed.params);
      return;
    }

    if (currentLink === "DEGRADED") {
      // Only model-free commands run. Anything needing the model is refused,
      // with a reason — never a fabricated answer.
      var needsModel = !/đọc|tra|kiểm tra file|liệt kê|fs\.|tool\./i.test(text);
      if (needsModel) {
        addEntry(
          "từ chối chạy",
          null,
          "Lệnh này cần model để sinh kết quả, mà model đang mất. Không có câu trả lời nào được bịa ra. Lý do: " +
            currentReason +
            " — " +
            (REASONS[currentReason] || "đang degraded") +
            ".",
          "is-error"
        );
        return;
      }
      addEntry(
        "chờ bus",
        null,
        "Lệnh này không cần model nên được phép chạy. Kết quả sẽ hiện ở đây, mang nhãn nguồn do host gán — giao diện này chưa nối bus nên chưa tự sinh kết quả.",
        "is-tool"
      );
      return;
    }

    addEntry(
      "đã nhận chỉ thị",
      null,
      "Giao diện bản mẫu chưa nối IPC Bus. Khi nối thật, lời gọi đi qua bus → mặt Python → Cautreo / model, và kết quả trả về sẽ mang nhãn nguồn do host gán.",
      "is-tool"
    );
  }

  sendBtn.addEventListener("click", function () {
    var text = composerInput.value.trim();
    if (!text) return;
    composerInput.value = "";
    sendCommand(text);
  });

  composerInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  /* ───────────────────────────────────────────
     6 · Boot — default is real connection
     ───────────────────────────────────────────

     BOOTING → LINKING → ONLINE, and if step 3 fails the app
     lands in DEGRADED with the true reason. There is no
     "simulation" branch and no invented reply. */

  function boot() {
    setLink("BOOTING");
    linkName.textContent = "booting";
    linkReason.textContent = "";
    paintTrace("LINKING");

    window.setTimeout(function () {
      linkName.textContent = "linking";
      linkReason.textContent = "đang bắt tay model thật";
    }, 420);

    window.setTimeout(function () {
      // Sample boot: KHÔNG bịa ONLINE. State thật do bus/host.state quyết định.
      if (!bus.live) {
        setLink("DEGRADED", "endpoint_unreachable", "sample boot — không có bus, không tự ONLINE");
        return;
      }
      callBus("host.link-probe", {});
    }, 1100);
  }

  /* ───────────────────────────────────────────
     7 · Deep link — mỗi màn hình mở được trực tiếp
        ?surface=nhiem-vu & ?link=degraded
        #nhiem-vu · #he-thong · #skill-plugin · #degraded · #offline

     Nhận cả query lẫn hash. Query sống sót khi chụp màn hình
     headless, hash thì không — nhưng nghĩa hai đường là một.
     Deep link áp ngay lúc nạp, không đợi chuỗi boot chạy xong.
     ─────────────────────────────────────────── */

  function readDeepLink() {
    var out = { surface: null, link: null };
    var query = window.location.search.replace(/^\?/, "");
    if (query) {
      query.split("&").forEach(function (pair) {
        var kv = pair.split("=");
        var k = kv[0];
        var v = decodeURIComponent(kv[1] || "");
        if (k === "surface" && v) out.surface = v;
        if (k === "link" && v) out.link = v.toUpperCase();
      });
    }
    var raw = window.location.hash.replace(/^#/, "");
    if (raw) {
      raw.split("&").forEach(function (part) {
        var bit = part.trim();
        if (!bit) return;
        if (bit === "degraded" || bit === "offline" || bit === "online") out.link = bit.toUpperCase();
        else out.surface = bit;
      });
    }
    return out;
  }

  function applyLink(mode) {
    protoBtns.forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-set") === mode ? "true" : "false");
    });
    setLink(mode);
    if (mode === "ONLINE") startTrace();
  }

  function applyDeepLink() {
    var deep = readDeepLink();
    if (deep.surface && document.querySelector('.rail-btn[data-surface="' + deep.surface + '"]')) {
      showSurface(deep.surface);
    }
    if (deep.link) {
      applyLink(deep.link);
      return true;
    }
    return false;
  }

  window.addEventListener("hashchange", applyDeepLink);

  /* ───────────────────────────────────────────
     8 · Live bus — nối IPC Bus thật khi có host

     Có bus thì Thanh Thân thể đọc trạng thái do host báo, mọi dòng trong
     dòng suy nghĩ đều do bus phát kèm nhãn nguồn do **host** gán, và
     `proto-switch` bị ẩn đi — không cho "giả vờ" state khi đang xem máy thật.

     Không có bus thì giữ nguyên bản mẫu, có ghi rõ là bản mẫu.
     ─────────────────────────────────────────── */

  var bus = { ws: null, live: false, seq: 0, closed: false, pending: {} };
  var protoSwitch = document.getElementById("protoSwitch");
  var streamNote = document.getElementById("streamNote");

  var SAMPLE_NOTE =
    "Dòng dưới đây là dữ liệu mẫu để xem giao diện. Khi nối bus thật, mọi dòng đều do bus phát kèm nhãn nguồn — không có dòng nào do UI tự bịa.";
  var LIVE_NOTE =
    "Đang nối IPC Bus thật. Mọi dòng dưới đây đều do host phát kèm nhãn nguồn do host gán theo sổ năng lực — giao diện không tự bịa dòng nào, và không tự đặt nhãn.";

  function setBusMode(live) {
    bus.live = live;
    document.body.setAttribute("data-bus", live ? "live" : "sample");
    if (protoSwitch) protoSwitch.hidden = live;
    if (streamNote) streamNote.textContent = live ? LIVE_NOTE : SAMPLE_NOTE;
    if (live) {
      composerHint.textContent =
        "Nối bus thật rồi. Lệnh: help · đọc <path> · ghi <path> <nội dung> · hỏi <prompt> · tra <khoá> · hoặc tên method. Còn lại coi là lời nói với ViVy — hỏi thẳng model, kết quả mang nhãn nguồn do host gán.";
    }
  }

  // Bộ điều hướng. Chỉ trỏ tới method có thật, không sinh kết quả nào.
  //
  // Không khớp động từ đã biết và cũng không ra được một tên method có namespace
  // thì coi là **lời nói với ViVy** — gửi cho `vivy.runtime/ask`. Kết quả đi về
  // sẽ mang nhãn `model` do host gán, nên người dùng thấy rõ câu đã đi đâu.
  // Không có đường nào ở đây tự viết một câu trả lời.
  function routeCommand(text) {
    var t = text.trim();
    var m;
    if (/^(help|giúp|\?)$/i.exec(t)) return { method: "vivy.runtime/help", params: {} };
    if ((m = /^đọc\s+(.+)$/i.exec(t))) return { method: "tool.fs-read", params: { path: m[1].trim() } };
    if ((m = /^ghi\s+(\S+)\s+([\s\S]*)$/i.exec(t))) return { method: "tool.fs-write", params: { path: m[1], text: m[2] } };
    if ((m = /^hỏi\s+([\s\S]+)$/i.exec(t))) return { method: "vivy.runtime/ask", params: { prompt: m[1].trim() } };
    if ((m = /^tra\s+(\S+)/i.exec(t))) return { method: "vivy.runtime/recall", params: { key: m[1] } };
    // Tên method phải **có namespace** (chứa `.` hoặc `/`) — đúng như contract
    // `id = "namespace.tên"`. Nhờ vậy "hello" không bị hiểu nhầm là tên method.
    if ((m = /^([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+(?:\/[A-Za-z0-9_-]+)?|[A-Za-z0-9_-]+\/[A-Za-z0-9_-]+)(?:\s+(\{[\s\S]*\}))?$/.exec(t))) {
      var params = {};
      if (m[2]) {
        try { params = JSON.parse(m[2]); } catch (e) {
          // JSON hỏng: đây là một lời gọi method nhưng tham số sai. Báo thẳng
          // cho người dùng, không âm thầm chuyển thành câu hỏi cho model.
          return { method: m[1], params: {}, badJson: true };
        }
      }
      return { method: m[1], params: params };
    }
    return { method: "vivy.runtime/ask", params: { prompt: t } };
  }

  function callBus(method, params) {
    if (!bus.ws || bus.ws.readyState !== 1) return;
    var id = "c-" + ++bus.seq;
    bus.pending[id] = method;
    bus.ws.send(JSON.stringify({ jsonrpc: "2.0", id: id, method: method, params: params || {} }));
  }

  // ---- bản đồ thân thể ----
  // Chỉ vẽ đúng số liệu host trả về. Không suy luận, không tự đặt tên cơ quan.

  function mapPart(part) {
    var li = document.createElement("li");
    li.className = "map-part";
    var head = document.createElement("div");
    head.className = "map-part-head";
    var idEl = document.createElement("code");
    idEl.textContent = part.id;
    var meta = document.createElement("span");
    meta.className = "map-part-meta";
    meta.textContent = (part.kind || "?") + " v" + (part.version || "?") + " · " + (part.state || "?");
    head.appendChild(idEl);
    head.appendChild(meta);
    li.appendChild(head);

    var grants = document.createElement("div");
    grants.className = "map-part-grants";
    grants.textContent = "quyền: " +
      (Array.isArray(part.grants) && part.grants.length ? part.grants.join(", ") : "không xin quyền nào");
    li.appendChild(grants);

    var methods = Array.isArray(part.methods) ? part.methods : [];
    if (methods.length) {
      var ul = document.createElement("ul");
      ul.className = "map-methods";
      methods.forEach(function (m) {
        var mi = document.createElement("li");
        var c = document.createElement("code");
        c.textContent = m.name;
        mi.appendChild(c);
        if (m.needs_model) {
          var need = document.createElement("span");
          need.className = "map-need";
          need.textContent = " · cần model";
          mi.appendChild(need);
        }
        ul.appendChild(mi);
      });
      li.appendChild(ul);
    } else if (part.state !== "activated") {
      // Nói đúng lý do, không phải "chưa có method" — bus sẽ từ chối lời gọi.
      var none = document.createElement("div");
      none.className = "map-part-grants";
      none.textContent = "method: không gọi được khi chưa activated";
      li.appendChild(none);
    }
    return li;
  }

  function mapSection(title, parts, emptyNote) {
    var wrap = document.createElement("section");
    wrap.className = "map-section";
    var h = document.createElement("h4");
    h.textContent = title;
    wrap.appendChild(h);
    if (!parts || !parts.length) {
      var p = document.createElement("p");
      p.className = "plate-note";
      p.textContent = emptyNote;
      wrap.appendChild(p);
      return wrap;
    }
    var ul = document.createElement("ul");
    ul.className = "map-parts";
    parts.forEach(function (part) { ul.appendChild(mapPart(part)); });
    wrap.appendChild(ul);
    return wrap;
  }

  function renderBodyMap(map) {
    var root = document.getElementById("bodyMap");
    if (!root || !map) return;
    root.textContent = "";

    var organs = map.organs || {};
    root.appendChild(mapSection("Mắt · cơ quan nhận", organs.eye, "chưa có"));
    root.appendChild(mapSection("Tay · cơ quan làm", organs.hand, "chưa có"));
    root.appendChild(mapSection("Toàn thân", organs["both"], "chưa có"));
    root.appendChild(mapSection("Method của host", map.host_methods, "chưa có"));
    root.appendChild(mapSection(
      "Thứ đang hỏng",
      (map.broken || []).map(function (b) {
        return { id: b.id, kind: b.kind, version: b.state, state: b.state, grants: [], methods: [], error: b.error };
      }),
      "chưa có"
    ));

    var counts = map.counts || {};
    var foot = document.createElement("p");
    foot.className = "map-counts";
    foot.textContent =
      "plugin: " + (counts.plugins || 0) +
      " · method: " + (counts.methods || 0) +
      " · skill: " + (counts.skills || 0);
    root.appendChild(foot);
    root.setAttribute("data-map", "live");
  }

  function refreshBodyMap() {
    if (bus.live) callBus("host.body-map", {});
  }

  function renderResult(msg) {
    var receipt = msg.receipt;
    var result = msg.result || {};
    var body;
    var thinking = null;

    if (typeof result.answer === "string") {
      // Model trả về đã tách: `answer` là câu trả lời, `thinking` là luồng tư
      // duy. UI chỉ bày `answer` ra trước mặt; `thinking` nằm trong khối thu gọn.
      body = result.answer;
      if (Array.isArray(result.thinking)) {
        thinking = result.thinking.filter(function (t) {
          return typeof t === "string" && t.trim();
        });
        if (!thinking.length) thinking = null;
      }
      if (!body.trim()) {
        // Model chỉ sinh suy nghĩ, không ra câu trả lời cuối. Nói thẳng điều đó
        // — KHÔNG lấy `summary` ("đã hỏi model") ra giả làm câu trả lời.
        body = thinking
          ? "Model chỉ sinh phần suy nghĩ, không có câu trả lời cuối. Bấm mở rộng bên dưới để xem."
          : "Model không trả về chữ nào.";
      }
    } else {
      // Kết quả không có cấu trúc tách (tool, hoặc plugin bên thứ ba) — bày
      // nguyên khối. UI KHÔNG tự đoán chỗ nào là suy nghĩ.
      body = result.summary || result.text || JSON.stringify(result);
      if (body && typeof body === "object") body = JSON.stringify(body);
    }

    // Nhãn nguồn LẤY TỪ RECEIPT do host gán. UI không đọc nhãn trong result.
    // Response đã kèm receipt — không render thêm từ host.receipt (tránh nhân đôi).
    addEntry(receipt ? receipt.command : "kết quả", receipt ? receipt.source : null, String(body), "is-tool", thinking);
  }

  function renderError(msg) {
    var err = msg.error || {};
    var data = err.data || {};
    var reason = data.reason || "";
    var body = "Bị từ chối — " + err.message + " (" + err.code + ").";
    if (reason) body += " Lý do: " + reason + ".";
    if (data.need) body += " Thiếu quyền: " + (Array.isArray(data.need) ? data.need.join(", ") : data.need) + ".";
    if (data.method) body += " Method: " + data.method + ".";
    body += " Không có kết quả nào được sinh ra cho lệnh này.";
    // Lỗi KHÔNG có receipt — nên không có nhãn nguồn. Không dán chip nguồn cho lỗi.
    addEntry("từ chối chạy", null, body, "is-error");
  }

  function applyHostState(params) {
    var link = String(params.link || "").toUpperCase();
    if (params.model) modelLabel = params.model;
    if (link === "BOOTING" || link === "LINKING") {
      currentLink = "BOOTING";
      bodyBar.setAttribute("data-link", "BOOTING");
      linkChip.setAttribute("data-link", "BOOTING");
      linkName.textContent = link.toLowerCase();
      linkReason.textContent = params.reason || "";
      paintTrace("LINKING");
      return;
    }
    if (link === "ONLINE") startTrace();
    setLink(link, params.reason || "", params.reason_text || "");
  }

  function onBusMessage(ev) {
    var msg;
    try { msg = JSON.parse(ev.data); } catch (e) { return; }
    if (msg.method === "host.state") { applyHostState(msg.params || {}); return; }
    if (msg.method === "host.receipt") {
      var r = msg.params || {};
      // Chỉ hiển thị receipt phát broadcast, không dán nhãn do UI nghĩ ra.
      addEntry(r.organ + " · " + r.command, r.source, r.result, "is-tool");
      return;
    }
    if (msg.method === "registry.changed") {
      // Registry đổi → bản đồ dựng lại. Hỏi host để lấy bản đồ mới nhất.
      refreshBodyMap();
      return;
    }
    if (Object.prototype.hasOwnProperty.call(msg, "id")) {
      var asked = bus.pending[msg.id];
      delete bus.pending[msg.id];
      // Trả lời của `host.body-map` đổ vào bảng bản đồ, không tràn vào dòng chat.
      if (asked === "host.body-map") {
        if (!msg.error && msg.result && msg.result.map) renderBodyMap(msg.result.map);
        return;
      }
      if (msg.error) renderError(msg);
      else renderResult(msg);
    }
  }

  function onBusClose() {
    if (bus.closed) return;
    bus.closed = true;
    bus.live = false;
    bus.ws = null;
    setBusMode(false);
  }

  function startBus() {
    if (!window.location.host) return false; // mở bằng file:// thì không có bus
    var wsUrl = (window.location.protocol === "https:" ? "wss://" : "ws://") +
      window.location.host + "/bus";
    try {
      bus.ws = new WebSocket(wsUrl);
    } catch (e) {
      return false;
    }
    bus.ws.addEventListener("open", function () {
      bus.closed = false;
      setBusMode(true);
      // Vừa nối bus là hỏi ngay bản đồ — không chờ sự kiện gì.
      refreshBodyMap();
    });
    bus.ws.addEventListener("message", onBusMessage);
    bus.ws.addEventListener("close", onBusClose);
    bus.ws.addEventListener("error", onBusClose);
    return true;
  }

  // Có deep link thì vào thẳng trạng thái đó. Không có thì thử bus thật trước,
  // không có bus mới chạy chuỗi boot của bản mẫu.
  paintTrace("ONLINE");
  if (applyDeepLink()) {
    startBus();
  } else if (!startBus()) {
    boot();
  }
})();
