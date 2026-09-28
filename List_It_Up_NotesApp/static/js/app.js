/* List it Up — Interactive Frontend
   Animations • Subtle Sounds • Haptics
*/

(() => {
    "use strict";

    // ---------- Audio (Web Audio API) ----------
    let audioCtx = null;

    function ensureAudio() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === "suspended") {
            audioCtx.resume();
        }
        return audioCtx;
    }

    function playTone(freq, duration = 0.08, type = "sine", gain = 0.08) {
        try {
            const ctx = ensureAudio();
            const osc = ctx.createOscillator();
            const g = ctx.createGain();
            osc.type = type;
            osc.frequency.value = freq;
            g.gain.setValueAtTime(gain, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
            osc.connect(g);
            g.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + duration);
        } catch (_) {}
    }

    function soundClick() {
        playTone(420, 0.05, "sine", 0.05);
    }

    function soundSuccess() {
        playTone(520, 0.07, "sine", 0.07);
        setTimeout(() => playTone(680, 0.1, "sine", 0.06), 70);
    }

    function soundError() {
        playTone(220, 0.12, "triangle", 0.07);
    }

    function soundProcess() {
        playTone(360, 0.06, "sine", 0.04);
    }

    // ---------- Haptics ----------
    function haptic(pattern = 12) {
        if (navigator.vibrate) {
            try {
                navigator.vibrate(pattern);
            } catch (_) {}
        }
    }

    // ---------- UI Helpers ----------
    const $ = (sel, root = document) => root.querySelector(sel);
    const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

    const statusDot = $("#statusDot");
    const pageTitle = $("#pageTitle");
    const toastEl = $("#toast");
    const sidebar = $("#sidebar");
    const menuToggle = $("#menuToggle");

    function setStatus(state) {
        statusDot.className = "status-dot";
        if (state) statusDot.classList.add(state);
    }

    function showToast(msg, type = "") {
        toastEl.textContent = msg;
        toastEl.className = "toast show" + (type ? ` ${type}` : "");
        clearTimeout(toastEl._timer);
        toastEl._timer = setTimeout(() => {
            toastEl.classList.remove("show");
        }, 2800);
    }

    function setLoading(btn, loading) {
        const text = btn.querySelector(".btn-text");
        const loader = btn.querySelector(".btn-loader");
        if (loading) {
            btn.disabled = true;
            text.hidden = true;
            loader.hidden = false;
            setStatus("busy");
            soundProcess();
            haptic(8);
        } else {
            btn.disabled = false;
            text.hidden = false;
            loader.hidden = true;
        }
    }

    // ---------- Screen Navigation ----------
    function goToScreen(name) {
        const screens = $$(".screen");
        const items = $$(".nav-item");
        const target = $(`#screen-${name}`);
        if (!target) return;

        screens.forEach(s => s.classList.remove("active"));
        items.forEach(i => i.classList.remove("active"));

        target.classList.add("active");
        const navBtn = $(`.nav-item[data-screen="${name}"]`);
        if (navBtn) navBtn.classList.add("active");

        pageTitle.textContent = target.dataset.title || "List it Up";
        soundClick();
        haptic(10);

        // close mobile sidebar
        sidebar.classList.remove("open");
    }

    // Nav clicks
    $$(".nav-item").forEach(btn => {
        btn.addEventListener("click", () => {
            goToScreen(btn.dataset.screen);
        });
    });

    // Feature cards + hero buttons
    $$("[data-goto]").forEach(el => {
        el.addEventListener("click", () => {
            goToScreen(el.dataset.goto);
        });
    });

    menuToggle.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        soundClick();
        haptic(8);
    });

    // Close sidebar on outside click (mobile)
    document.addEventListener("click", (e) => {
        if (window.innerWidth <= 860 &&
            sidebar.classList.contains("open") &&
            !sidebar.contains(e.target) &&
            e.target !== menuToggle) {
            sidebar.classList.remove("open");
        }
    });

    // ---------- API Helper ----------
    async function api(endpoint, body) {
        const res = await fetch(`/api/${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        return res.json();
    }

    function showResult(container, data, successExtra = null) {
        container.hidden = false;
        container.className = "result-card " + (data.success ? "success" : "error");

        if (data.success) {
            soundSuccess();
            haptic([20, 30, 20]);
            setStatus("success");
            setTimeout(() => setStatus(""), 1800);
        } else {
            soundError();
            haptic([40, 20, 40]);
            setStatus("error");
            setTimeout(() => setStatus(""), 1800);
        }

        if (successExtra && data.success) {
            container.innerHTML = successExtra(data);
        } else {
            container.innerHTML = `
                <div class="result-title">${data.success ? "Done" : "Something went wrong"}</div>
                <div class="result-body">${data.message || ""}</div>
            `;
        }
    }

    // Artificial delay to match original "processing" feel
    function delay(ms) {
        return new Promise(r => setTimeout(r, ms));
    }

    // ---------- Forms ----------

    // CREATE
    $("#form-create").addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = $("#btn-create");
        const result = $("#result-create");
        result.hidden = true;

        const payload = {
            userId: $("#create-userId").value,
            userName: $("#create-userName").value.trim(),
            notes: $("#create-notes").value.trim()
        };

        setLoading(btn, true);
        await delay(900); // mimic original sleep
        try {
            const data = await api("create", payload);
            showResult(result, data, (d) => `
                <div class="result-title">Note saved</div>
                <div class="result-body">${d.message}</div>
                <div class="meta">Note ID: <strong>${d.notesId}</strong> — keep this safe</div>
            `);
            if (data.success) {
                showToast("Note created · ID " + data.notesId, "success");
                $("#form-create").reset();
            } else {
                showToast(data.message, "error");
            }
        } catch {
            showResult(result, { success: false, message: "Network error. Try again." });
            showToast("Connection issue", "error");
        }
        setLoading(btn, false);
    });

    // READ
    $("#form-read").addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = $("#btn-read");
        const result = $("#result-read");
        result.hidden = true;

        setLoading(btn, true);
        await delay(1100);
        try {
            const data = await api("read", { notesId: $("#read-notesId").value });
            showResult(result, data, (d) => `
                <div class="result-title">Note #${d.notesId}</div>
                <div class="result-body">${escapeHtml(d.notes)}</div>
                <div class="meta">Created · ${d.timestamp}</div>
            `);
            if (!data.success) showToast(data.message, "error");
        } catch {
            showResult(result, { success: false, message: "Network error. Try again." });
        }
        setLoading(btn, false);
    });

    // UPDATE
    $("#form-update").addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = $("#btn-update");
        const result = $("#result-update");
        result.hidden = true;

        setLoading(btn, true);
        await delay(1400);
        try {
            const data = await api("update", {
                notesId: $("#update-notesId").value,
                notes: $("#update-notes").value.trim()
            });
            showResult(result, data);
            showToast(data.success ? "Note updated" : data.message, data.success ? "success" : "error");
            if (data.success) $("#form-update").reset();
        } catch {
            showResult(result, { success: false, message: "Network error. Try again." });
        }
        setLoading(btn, false);
    });

    // DELETE
    $("#form-delete").addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = $("#btn-delete");
        const result = $("#result-delete");
        result.hidden = true;

        setLoading(btn, true);
        await delay(1000);
        try {
            const data = await api("delete", { notesId: $("#delete-notesId").value });
            showResult(result, data);
            showToast(data.success ? "Note deleted" : data.message, data.success ? "success" : "error");
            if (data.success) $("#form-delete").reset();
        } catch {
            showResult(result, { success: false, message: "Network error. Try again." });
        }
        setLoading(btn, false);
    });

    // ALL NOTES
    $("#form-all").addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = $("#btn-all");
        const container = $("#result-all");
        container.hidden = true;
        container.innerHTML = "";

        setLoading(btn, true);
        await delay(1800); // original had longer wait
        try {
            const data = await api("all", { userName: $("#all-userName").value.trim() });
            if (data.success) {
                soundSuccess();
                haptic([15, 25, 15]);
                setStatus("success");
                setTimeout(() => setStatus(""), 1800);

                container.hidden = false;
                data.notes.forEach((n, i) => {
                    const card = document.createElement("div");
                    card.className = "note-item";
                    card.style.animationDelay = `${i * 60}ms`;
                    card.innerHTML = `
                        <div class="note-id">Note #${n.notesId}</div>
                        <div class="note-text">${escapeHtml(n.notes)}</div>
                        <div class="note-time">${n.timestamp}</div>
                    `;
                    container.appendChild(card);
                });
                showToast(`${data.notes.length} note${data.notes.length > 1 ? "s" : ""} found`, "success");
            } else {
                soundError();
                haptic([40, 20, 40]);
                setStatus("error");
                setTimeout(() => setStatus(""), 1800);
                container.hidden = false;
                container.innerHTML = `
                    <div class="result-card error">
                        <div class="result-title">Nothing here</div>
                        <div class="result-body">${data.message}</div>
                    </div>
                `;
                showToast(data.message, "error");
            }
        } catch {
            showToast("Connection issue", "error");
        }
        setLoading(btn, false);
    });

    // DELETE ALL
    $("#form-delete-all").addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = $("#btn-delete-all");
        const result = $("#result-delete-all");
        result.hidden = true;

        setLoading(btn, true);
        await delay(1600);
        try {
            const data = await api("delete-all", { userId: $("#deleteAll-userId").value });
            showResult(result, data);
            showToast(data.success ? "All notes cleared" : data.message, data.success ? "success" : "error");
            if (data.success) $("#form-delete-all").reset();
        } catch {
            showResult(result, { success: false, message: "Network error. Try again." });
        }
        setLoading(btn, false);
    });

    // ---------- Utils ----------
    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    // Unlock audio on first interaction
    document.addEventListener("pointerdown", () => ensureAudio(), { once: true });

    // Ready
    console.log("%cList it Up ready", "color:#8A9A86;font-weight:600;");
})();