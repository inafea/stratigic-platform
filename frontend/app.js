"use strict";

// ---------- tiny DOM helpers (text only → XSS-safe) ----------
const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
        if (k === "class") node.className = v;
        else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
        else node.setAttribute(k, v);
    }
    for (const c of children.flat()) {
        if (c == null || c === false) continue;
        node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return node;
}

const list = (items) => el("ul", {}, (items || []).map((i) => el("li", {}, i)));

function renderMarkdown(text) {
    if (window.marked && window.DOMPurify) {
        return DOMPurify.sanitize(marked.parse(text));
    }
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, "<br>");
}

// ---------- state ----------
const state = {
    idea: "",
    goals: "",
    questions: [],
    reportId: null,
    busy: false,
};
const TOTAL_SECTIONS = 8;

// ---------- UI helpers ----------
function showAlert(msg) {
    const a = $("alert");
    a.textContent = msg;
    a.hidden = !msg;
    if (msg) a.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function setLoading(on, text = "جاري التحليل...") {
    $("loading").hidden = !on;
    $("loadingText").textContent = text;
}

function show(view) {
    $("stepIdea").hidden = view !== "idea";
    $("stepQuestions").hidden = view !== "questions";
    $("report").hidden = view !== "report";
}

function setBusy(on) {
    state.busy = on;
    document.querySelectorAll("button").forEach((b) => {
        if (!b.closest(".sidebar")) b.disabled = on;
    });
}

// ---------- API ----------
async function api(path, options = {}) {
    const res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    if (!res.ok) throw new Error(await errorMessage(res));
    return res.status === 204 ? null : res.json();
}

async function errorMessage(res) {
    try {
        const body = await res.json();
        if (typeof body.detail === "string") return body.detail;
        if (Array.isArray(body.detail)) return "يرجى التحقق من المدخلات (الفكرة 10 أحرف على الأقل).";
    } catch (_) { /* ignore */ }
    return `حدث خطأ (${res.status}).`;
}

/** POST and consume a server-sent-event stream. Calls onEvent(name, data) for each event. */
async function streamSSE(path, body, onEvent) {
    const res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await errorMessage(res));

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
        let idx;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
            const block = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            let event = "message", data = "";
            for (const line of block.split("\n")) {
                if (line.startsWith("event:")) event = line.slice(6).trim();
                else if (line.startsWith("data:")) data += line.slice(5).trim();
            }
            if (data) onEvent(event, JSON.parse(data));
        }
    }
}

// ---------- section renderers ----------
const renderers = {
    summary(d) {
        const score = Math.max(0, Math.min(100, d.viability_score ?? 0));
        const color = score >= 70 ? "var(--green)" : score >= 45 ? "var(--amber)" : "var(--red)";
        const ring = el("div", { class: "score" },
            el("div", { class: "score-inner" },
                el("div", {}, el("div", { class: "score-num" }, score), el("div", { class: "score-label" }, "درجة الجدوى"))));
        ring.style.background = `conic-gradient(${color} ${score * 3.6}deg, #e4e7ec 0)`;
        return [ring, el("div", {}, el("p", { class: "verdict" }, d.verdict), el("p", {}, d.summary))];
    },
    market(d) {
        return [
            el("h4", {}, "العملاء المستهدفون"), list(d.target_customers),
            el("h4", {}, "حجم السوق"), el("p", {}, d.market_size),
            el("h4", {}, "الاتجاهات"), list(d.trends),
            el("h4", {}, "القيمة الفريدة"), el("p", {}, d.unique_value_proposition),
        ];
    },
    swot(d) {
        const box = (cls, title, items) => el("div", { class: cls }, el("h4", {}, title), list(items));
        return [el("div", { class: "swot" },
            box("s", "نقاط القوة", d.strengths), box("w", "نقاط الضعف", d.weaknesses),
            box("o", "الفرص", d.opportunities), box("t", "التهديدات", d.threats))];
    },
    competition(d) {
        return [
            el("table", {},
                el("thead", {}, el("tr", {}, el("th", {}, "المنافس"), el("th", {}, "الوصف"), el("th", {}, "ميزتنا"))),
                el("tbody", {}, (d.competitors || []).map((c) =>
                    el("tr", {}, el("td", {}, el("strong", {}, c.name)), el("td", {}, c.description), el("td", {}, c.our_advantage))))),
            el("h4", {}, "التموضع"), el("p", {}, d.positioning),
        ];
    },
    risks(d) {
        const badge = (lvl) => el("span", { class: `badge lvl-${lvl}` }, lvl);
        return [el("table", {},
            el("thead", {}, el("tr", {}, el("th", {}, "الخطر"), el("th", {}, "الاحتمال"), el("th", {}, "الأثر"), el("th", {}, "التخفيف"))),
            el("tbody", {}, (d.risks || []).map((r) =>
                el("tr", {}, el("td", {}, r.risk), el("td", {}, badge(r.likelihood)), el("td", {}, badge(r.impact)), el("td", {}, r.mitigation)))))];
    },
    roadmap(d) {
        const phase = (title, p) => el("div", { class: "phase" },
            el("h4", {}, title), el("strong", {}, "الأهداف"), list(p?.goals), el("strong", {}, "الإجراءات"), list(p?.actions));
        return [el("div", { class: "roadmap" },
            phase("أول 30 يوماً", d.days_30), phase("حتى 60 يوماً", d.days_60), phase("حتى 90 يوماً", d.days_90))];
    },
    financials(d) {
        return [
            el("h4", {}, "الاستثمار المقدر"), el("p", {}, d.estimated_investment),
            el("h4", {}, "مصادر الإيراد"), list(d.revenue_streams),
            el("h4", {}, "هيكل التكاليف"), list(d.cost_structure),
            el("h4", {}, "استراتيجية التسعير"), el("p", {}, d.pricing_strategy),
            el("h4", {}, "نقطة التعادل"), el("p", {}, d.break_even_estimate),
        ];
    },
    kpis(d) {
        return [el("table", {},
            el("thead", {}, el("tr", {}, el("th", {}, "المؤشر"), el("th", {}, "المستهدف"), el("th", {}, "لماذا"))),
            el("tbody", {}, (d.kpis || []).map((k) =>
                el("tr", {}, el("td", {}, el("strong", {}, k.name)), el("td", {}, k.target), el("td", {}, k.why)))))];
    },
};

function sectionCard({ key, title, data }) {
    const body = el("div", { class: "card-body" }, (renderers[key] || (() => el("pre", {}, JSON.stringify(data, null, 2))))(data));
    const regen = el("button", { class: "btn btn-secondary btn-sm", title: "إعادة كتابة هذا القسم", onclick: () => regenerate(key) }, "↻ إعادة توليد");
    const card = el("article", { class: `card${key === "summary" ? " summary-card" : ""}`, id: `sec-${key}` });
    if (key === "summary") {
        card.append(...body.childNodes);
        const actions = el("div", { class: "card-actions" }, regen);
        actions.style.gridColumn = "1 / -1";
        card.append(actions);
    } else {
        card.append(el("div", { class: "card-head" }, el("h3", {}, title), el("div", { class: "card-actions" }, regen)), body);
    }
    return card;
}

/** Insert or replace a section; summary always goes first. */
function putSection(section) {
    const card = sectionCard(section);
    const existing = $(`sec-${section.key}`);
    if (existing) existing.replaceWith(card);
    else if (section.key === "summary") $("sections").prepend(card);
    else $("sections").append(card);
}

// ---------- report view ----------
function openReportView(idea, createdAt) {
    $("sections").replaceChildren();
    $("chatLog").replaceChildren();
    $("reportTitle").textContent = idea.length > 90 ? idea.slice(0, 90) + "…" : idea;
    $("reportMeta").textContent = createdAt ? new Date(createdAt).toLocaleString("ar") : "";
    show("report");
}

function setProgress(n) {
    $("progress").hidden = n >= TOTAL_SECTIONS;
    $("progressBar").style.width = `${Math.round((n / TOTAL_SECTIONS) * 100)}%`;
}

async function loadReport(id) {
    if (state.busy) return;
    showAlert("");
    try {
        const r = await api(`/api/reports/${id}`);
        state.reportId = r.id;
        state.idea = r.idea;
        state.goals = r.goals;
        openReportView(r.idea, r.created_at);
        r.sections.forEach(putSection);
        setProgress(TOTAL_SECTIONS);
        r.messages.forEach((m) => addMessage(m.role, m.content));
        $("chat").hidden = r.sections.length === 0;
        if (r.status === "error") showAlert("هذا التقرير غير مكتمل بسبب خطأ أثناء التحليل.");
        markActive(id);
    } catch (e) {
        showAlert(e.message);
    }
}

// ---------- flow: idea → questions → analysis ----------
$("ideaForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    showAlert("");
    state.idea = $("idea").value.trim();
    state.goals = $("goals").value.trim();
    setBusy(true);
    setLoading(true, "جاري إعداد أسئلة توضيحية...");
    try {
        const { questions } = await api("/api/clarify", {
            method: "POST",
            body: JSON.stringify({ idea: state.idea, goals: state.goals }),
        });
        state.questions = questions;
        $("questionsList").replaceChildren(...questions.map((q, i) =>
            el("div", {}, el("label", { for: `q${i}` }, q), el("input", { id: `q${i}`, maxlength: "1000" }))));
        show("questions");
        $("q0")?.focus();
    } catch (err) {
        showAlert(err.message);
    } finally {
        setLoading(false);
        setBusy(false);
    }
});

$("backBtn").addEventListener("click", () => show("idea"));

$("questionsForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const answers = state.questions
        .map((question, i) => ({ question, answer: $(`q${i}`).value.trim() }))
        .filter((a) => a.answer);
    await runAnalysis({ idea: state.idea, goals: state.goals, answers });
});

async function runAnalysis(payload) {
    showAlert("");
    setBusy(true);
    openReportView(payload.idea, new Date().toISOString());
    $("chat").hidden = true;
    setProgress(0);
    setLoading(true, "يتم إعداد التحليل قسماً تلو الآخر...");
    let count = 0;
    try {
        await streamSSE("/api/analyze", payload, (event, data) => {
            if (event === "report") state.reportId = data.id;
            else if (event === "section") {
                putSection(data);
                setProgress(++count);
                $("loadingText").textContent = `تم إعداد: ${data.title} (${count}/${TOTAL_SECTIONS})`;
            } else if (event === "error") showAlert(data.message);
            else if (event === "done") $("chat").hidden = false;
        });
    } catch (err) {
        showAlert(err.message);
    } finally {
        setLoading(false);
        setBusy(false);
        setProgress(TOTAL_SECTIONS);
        if (count > 0) $("chat").hidden = false;
        refreshHistory();
    }
}

// ---------- regenerate a section ----------
async function regenerate(key) {
    if (!state.reportId || state.busy) return;
    const instructions = prompt("تعليمات إضافية لهذا القسم (اختياري):", "");
    if (instructions === null) return;
    const card = $(`sec-${key}`);
    card?.classList.add("busy");
    setBusy(true);
    showAlert("");
    try {
        const section = await api(`/api/reports/${state.reportId}/sections/${key}/regenerate`, {
            method: "POST",
            body: JSON.stringify({ instructions: instructions.trim() || null }),
        });
        putSection(section);
        if (key === "summary") refreshHistory();
    } catch (err) {
        card?.classList.remove("busy");
        showAlert(err.message);
    } finally {
        setBusy(false);
    }
}

// ---------- follow-up chat ----------
function addMessage(role, content) {
    const node = el("div", { class: `msg ${role}` });
    if (role === "assistant") node.innerHTML = renderMarkdown(content);
    else node.textContent = content;
    $("chatLog").append(node);
    node.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return node;
}

$("chatForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = $("chatInput").value.trim();
    if (!message || !state.reportId || state.busy) return;
    $("chatInput").value = "";
    addMessage("user", message);
    const reply = addMessage("assistant", "…");
    let text = "";
    setBusy(true);
    try {
        await streamSSE(`/api/reports/${state.reportId}/chat`, { message }, (event, data) => {
            if (event === "delta") {
                text += data.text;
                reply.innerHTML = renderMarkdown(text);
            } else if (event === "error") {
                reply.remove();
                showAlert(data.message);
            }
        });
    } catch (err) {
        reply.remove();
        showAlert(err.message);
    } finally {
        setBusy(false);
        $("chatInput").focus();
    }
});

// ---------- history sidebar ----------
function markActive(id) {
    document.querySelectorAll("#historyList li").forEach((li) => li.classList.toggle("active", li.dataset.id === String(id)));
}

async function refreshHistory() {
    try {
        const reports = await api("/api/reports");
        const items = reports.map((r) => {
            const del = el("button", { class: "h-del", title: "حذف", "aria-label": "حذف التقرير" }, "×");
            del.addEventListener("click", async (ev) => {
                ev.stopPropagation();
                if (!confirm("حذف هذا التقرير نهائياً؟")) return;
                try {
                    await api(`/api/reports/${r.id}`, { method: "DELETE" });
                    if (state.reportId === r.id) resetToNew();
                    refreshHistory();
                } catch (err) { showAlert(err.message); }
            });
            const li = el("li", { "data-id": r.id, title: r.title },
                el("span", { class: "h-title" }, r.title),
                r.score != null ? el("span", { class: "h-score" }, r.score) : null,
                del);
            li.addEventListener("click", () => loadReport(r.id));
            return li;
        });
        $("historyList").replaceChildren(...(items.length ? items : [el("li", { class: "empty" }, "لا توجد تقارير بعد")]));
        markActive(state.reportId);
    } catch (_) { /* sidebar is best-effort */ }
}

function resetToNew() {
    if (state.busy) return;
    state.reportId = null;
    $("ideaForm").reset();
    showAlert("");
    show("idea");
    markActive(null);
    $("idea").focus();
}

$("newBtn").addEventListener("click", resetToNew);
$("printBtn").addEventListener("click", () => window.print());

refreshHistory();
