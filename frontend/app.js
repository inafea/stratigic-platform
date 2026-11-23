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

// ---------- translations ----------
const I18N = {
    ar: {
        pageTitle: "مستشار — محلل الاستراتيجية التجارية",
        appName: "مستشار",
        subtitle: "مستشارك الذكي لتحليل أفكار الأعمال وبناء الاستراتيجية",
        newAnalysis: "+ تحليل جديد",
        history: "التقارير السابقة",
        noReports: "لا توجد تقارير بعد",
        del: "حذف",
        delReport: "حذف التقرير",
        confirmDelete: "حذف هذا التقرير نهائياً؟",
        toggleTheme: "تبديل الوضع الليلي",
        step1: "1. الفكرة", step2: "2. أسئلة توضيحية", step3: "3. التحليل",
        ideaLabel: "فكرتك التجارية",
        ideaPh: "صف فكرتك: ما المنتج أو الخدمة؟ من العملاء؟ ما المشكلة التي تحلها؟ وفي أي سوق/مدينة؟",
        goalsLabel: "أهدافك",
        goalsPh: "مثال: تحقيق الربحية خلال سنة، الوصول إلى 1000 عميل، التوسع إلى مدينة ثانية...",
        industryLabel: "القطاع",
        strategyLabel: "نوع الاستراتيجية",
        auto: "تحديد تلقائي",
        next: "التالي ←",
        back: "→ رجوع",
        questionsHint: "أجب عن الأسئلة التالية لتحصل على تحليل أدق (يمكنك ترك أي سؤال فارغاً).",
        startAnalysis: "ابدأ التحليل",
        analyzing: "جاري التحليل...",
        preparingQuestions: "جاري إعداد أسئلة توضيحية...",
        buildingReport: "يتم إعداد التحليل قسماً تلو الآخر...",
        sectionDone: (title, n, total) => `تم إعداد: ${title} (${n}/${total})`,
        exportPdf: "⬇ تصدير PDF",
        chatTitle: "اسأل مستشار عن التقرير",
        chatPh: "مثال: ماذا لو بدأت بميزانية أقل؟ اشرح استراتيجية التسعير أكثر...",
        send: "إرسال",
        regenerate: "↻ إعادة توليد",
        regenerateTitle: "إعادة كتابة هذا القسم",
        regeneratePrompt: "تعليمات إضافية لهذا القسم (اختياري):",
        incomplete: "هذا التقرير غير مكتمل بسبب خطأ أثناء التحليل.",
        invalidInput: "يرجى التحقق من المدخلات (الفكرة 10 أحرف على الأقل).",
        httpError: (s) => `حدث خطأ (${s}).`,
        // report labels
        sec_summary: "الملخص التنفيذي", sec_market: "تحليل السوق", sec_swot: "تحليل SWOT",
        sec_competition: "المنافسون", sec_risks: "المخاطر", sec_roadmap: "خارطة الطريق",
        sec_financials: "التوقعات المالية", sec_kpis: "مؤشرات الأداء",
        viability: "درجة الجدوى",
        targetCustomers: "العملاء المستهدفون", marketSize: "حجم السوق", trends: "الاتجاهات", uvp: "القيمة الفريدة",
        strengths: "نقاط القوة", weaknesses: "نقاط الضعف", opportunities: "الفرص", threats: "التهديدات",
        competitor: "المنافس", description: "الوصف", ourAdvantage: "ميزتنا", positioning: "التموضع",
        risk: "الخطر", likelihood: "الاحتمال", impact: "الأثر", mitigation: "التخفيف",
        lvl_low: "منخفض", lvl_medium: "متوسط", lvl_high: "مرتفع",
        goals: "الأهداف", actions: "الإجراءات",
        days30: "أول 30 يوماً", days60: "حتى 60 يوماً", days90: "حتى 90 يوماً",
        investment: "الاستثمار المقدر", revenueStreams: "مصادر الإيراد", costStructure: "هيكل التكاليف",
        pricing: "استراتيجية التسعير", breakEven: "نقطة التعادل",
        kpi: "المؤشر", target: "المستهدف", why: "لماذا",
        // templates
        ind_restaurant: "المطاعم والأغذية", ind_ecommerce: "التجارة الإلكترونية", ind_saas: "البرمجيات والتطبيقات (SaaS)",
        ind_retail: "تجارة التجزئة", ind_real_estate: "العقارات", ind_education: "التعليم والتدريب",
        ind_healthcare: "الصحة واللياقة", ind_services: "الخدمات المهنية والاستشارية",
        str_new_business: "إطلاق مشروع جديد", str_expansion: "توسع مشروع قائم", str_market_entry: "دخول سوق جديد",
        str_product_launch: "إطلاق منتج جديد", str_turnaround: "إنقاذ مشروع متعثر", str_funding: "التحضير للتمويل",
    },
    en: {
        pageTitle: "Mustashar — Business Strategy Analyzer",
        appName: "Mustashar",
        subtitle: "Your AI consultant for analyzing business ideas and building a strategy",
        newAnalysis: "+ New analysis",
        history: "Previous reports",
        noReports: "No reports yet",
        del: "Delete",
        delReport: "Delete report",
        confirmDelete: "Delete this report permanently?",
        toggleTheme: "Toggle dark mode",
        step1: "1. Idea", step2: "2. Clarifying questions", step3: "3. Analysis",
        ideaLabel: "Your business idea",
        ideaPh: "Describe your idea: what is the product or service? Who are the customers? What problem does it solve? Which market/city?",
        goalsLabel: "Your goals",
        goalsPh: "e.g. become profitable within a year, reach 1,000 customers, expand to a second city...",
        industryLabel: "Industry",
        strategyLabel: "Strategy type",
        auto: "Detect automatically",
        next: "Next →",
        back: "← Back",
        questionsHint: "Answer these questions for a more accurate analysis (you can leave any of them blank).",
        startAnalysis: "Start analysis",
        analyzing: "Analyzing...",
        preparingQuestions: "Preparing clarifying questions...",
        buildingReport: "Building the analysis section by section...",
        sectionDone: (title, n, total) => `Done: ${title} (${n}/${total})`,
        exportPdf: "⬇ Export PDF",
        chatTitle: "Ask Mustashar about this report",
        chatPh: "e.g. What if I start with a smaller budget? Explain the pricing strategy in more detail...",
        send: "Send",
        regenerate: "↻ Regenerate",
        regenerateTitle: "Rewrite this section",
        regeneratePrompt: "Extra instructions for this section (optional):",
        incomplete: "This report is incomplete because of an error during analysis.",
        invalidInput: "Please check your input (the idea needs at least 10 characters).",
        httpError: (s) => `Something went wrong (${s}).`,
        sec_summary: "Executive summary", sec_market: "Market analysis", sec_swot: "SWOT analysis",
        sec_competition: "Competitors", sec_risks: "Risks", sec_roadmap: "Roadmap",
        sec_financials: "Financial outlook", sec_kpis: "KPIs",
        viability: "Viability",
        targetCustomers: "Target customers", marketSize: "Market size", trends: "Trends", uvp: "Unique value",
        strengths: "Strengths", weaknesses: "Weaknesses", opportunities: "Opportunities", threats: "Threats",
        competitor: "Competitor", description: "Description", ourAdvantage: "Our advantage", positioning: "Positioning",
        risk: "Risk", likelihood: "Likelihood", impact: "Impact", mitigation: "Mitigation",
        lvl_low: "Low", lvl_medium: "Medium", lvl_high: "High",
        goals: "Goals", actions: "Actions",
        days30: "First 30 days", days60: "By day 60", days90: "By day 90",
        investment: "Estimated investment", revenueStreams: "Revenue streams", costStructure: "Cost structure",
        pricing: "Pricing strategy", breakEven: "Break-even",
        kpi: "KPI", target: "Target", why: "Why",
        ind_restaurant: "Restaurants & food", ind_ecommerce: "E-commerce", ind_saas: "Software & apps (SaaS)",
        ind_retail: "Retail", ind_real_estate: "Real estate", ind_education: "Education & training",
        ind_healthcare: "Health & fitness", ind_services: "Professional services",
        str_new_business: "Launch a new business", str_expansion: "Expand an existing business",
        str_market_entry: "Enter a new market", str_product_launch: "Launch a new product",
        str_turnaround: "Turn around a struggling business", str_funding: "Prepare for funding",
    },
};

/** Translate in the UI language (or `lang` if given). */
function t(key, lang = state.lang) {
    return I18N[lang]?.[key] ?? I18N.ar[key] ?? key;
}

// Risk levels are always stored in Arabic by the model; map them for CSS and labels.
const LEVELS = { "منخفض": "low", "متوسط": "medium", "مرتفع": "high" };

// ---------- state ----------
const state = {
    lang: localStorage.getItem("lang") === "en" ? "en" : "ar",
    idea: "",
    goals: "",
    industry: "auto",
    strategy: "auto",
    questions: [],
    reportId: null,
    reportLang: "ar",
    sections: {},  // key -> data for the open report (re-rendered on language change)
    templates: null,
    busy: false,
};
const TOTAL_SECTIONS = 8;
const SECTION_ORDER = ["summary", "market", "swot", "competition", "risks", "roadmap", "financials", "kpis"];

// ---------- UI helpers ----------
function showAlert(msg) {
    const a = $("alert");
    a.textContent = msg;
    a.hidden = !msg;
    if (msg) a.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function setLoading(on, text = t("analyzing")) {
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
        if (!b.closest(".sidebar") && !b.closest(".header-tools")) b.disabled = on;
    });
}

// ---------- language & theme ----------
function applyLanguage() {
    const lang = state.lang;
    const root = document.documentElement;
    root.lang = lang;
    root.dir = lang === "en" ? "ltr" : "rtl";
    document.title = t("pageTitle");
    document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((n) => { n.placeholder = t(n.dataset.i18nPlaceholder); });
    document.querySelectorAll("[data-i18n-title]").forEach((n) => { n.title = t(n.dataset.i18nTitle); });
    document.querySelectorAll("[data-i18n-aria]").forEach((n) => n.setAttribute("aria-label", t(n.dataset.i18nAria)));
    const other = lang === "en" ? "ar" : "en";
    $("langBtn").textContent = other === "en" ? "English" : "العربية";
    $("langBtn").lang = other;
    fillTemplates();
    rerenderSections();  // button labels follow the UI language
    refreshHistory();
}

function toggleLanguage() {
    state.lang = state.lang === "en" ? "ar" : "en";
    localStorage.setItem("lang", state.lang);
    applyLanguage();
}

function applyTheme() {
    const dark = document.documentElement.dataset.theme === "dark";
    $("themeBtn").textContent = dark ? "☀️" : "🌙";
}

function toggleTheme() {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("theme", next);
    applyTheme();
}

// ---------- API ----------
async function api(path, options = {}) {
    const res = await fetch(path, {
        headers: { "Content-Type": "application/json", "X-Lang": state.lang },
        ...options,
    });
    if (!res.ok) throw new Error(await errorMessage(res));
    return res.status === 204 ? null : res.json();
}

async function errorMessage(res) {
    try {
        const body = await res.json();
        if (typeof body.detail === "string") return body.detail;
        if (Array.isArray(body.detail)) return t("invalidInput");
    } catch (_) { /* ignore */ }
    return t("httpError")(res.status);
}

/** POST and consume a server-sent-event stream. Calls onEvent(name, data) for each event. */
async function streamSSE(path, body, onEvent) {
    const res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Lang": state.lang },
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

// ---------- section renderers (labels in the report's own language) ----------
const renderers = {
    summary(d, r) {
        const score = Math.max(0, Math.min(100, d.viability_score ?? 0));
        const color = score >= 70 ? "var(--green)" : score >= 45 ? "var(--amber)" : "var(--red)";
        const ring = el("div", { class: "score" },
            el("div", { class: "score-inner" },
                el("div", {}, el("div", { class: "score-num" }, score), el("div", { class: "score-label" }, r("viability")))));
        ring.style.background = `conic-gradient(${color} ${score * 3.6}deg, var(--track) 0)`;
        return [ring, el("div", {}, el("p", { class: "verdict" }, d.verdict), el("p", {}, d.summary))];
    },
    market(d, r) {
        return [
            el("h4", {}, r("targetCustomers")), list(d.target_customers),
            el("h4", {}, r("marketSize")), el("p", {}, d.market_size),
            el("h4", {}, r("trends")), list(d.trends),
            el("h4", {}, r("uvp")), el("p", {}, d.unique_value_proposition),
        ];
    },
    swot(d, r) {
        const box = (cls, title, items) => el("div", { class: cls }, el("h4", {}, title), list(items));
        return [el("div", { class: "swot" },
            box("s", r("strengths"), d.strengths), box("w", r("weaknesses"), d.weaknesses),
            box("o", r("opportunities"), d.opportunities), box("t", r("threats"), d.threats))];
    },
    competition(d, r) {
        return [
            el("table", {},
                el("thead", {}, el("tr", {}, el("th", {}, r("competitor")), el("th", {}, r("description")), el("th", {}, r("ourAdvantage")))),
                el("tbody", {}, (d.competitors || []).map((c) =>
                    el("tr", {}, el("td", {}, el("strong", {}, c.name)), el("td", {}, c.description), el("td", {}, c.our_advantage))))),
            el("h4", {}, r("positioning")), el("p", {}, d.positioning),
        ];
    },
    risks(d, r) {
        const badge = (lvl) => {
            const k = LEVELS[lvl];
            return el("span", { class: `badge lvl-${k || "unknown"}` }, k ? r(`lvl_${k}`) : lvl);
        };
        return [el("table", {},
            el("thead", {}, el("tr", {}, el("th", {}, r("risk")), el("th", {}, r("likelihood")), el("th", {}, r("impact")), el("th", {}, r("mitigation")))),
            el("tbody", {}, (d.risks || []).map((x) =>
                el("tr", {}, el("td", {}, x.risk), el("td", {}, badge(x.likelihood)), el("td", {}, badge(x.impact)), el("td", {}, x.mitigation)))))];
    },
    roadmap(d, r) {
        const phase = (title, p) => el("div", { class: "phase" },
            el("h4", {}, title), el("strong", {}, r("goals")), list(p?.goals), el("strong", {}, r("actions")), list(p?.actions));
        return [el("div", { class: "roadmap" },
            phase(r("days30"), d.days_30), phase(r("days60"), d.days_60), phase(r("days90"), d.days_90))];
    },
    financials(d, r) {
        return [
            el("h4", {}, r("investment")), el("p", {}, d.estimated_investment),
            el("h4", {}, r("revenueStreams")), list(d.revenue_streams),
            el("h4", {}, r("costStructure")), list(d.cost_structure),
            el("h4", {}, r("pricing")), el("p", {}, d.pricing_strategy),
            el("h4", {}, r("breakEven")), el("p", {}, d.break_even_estimate),
        ];
    },
    kpis(d, r) {
        return [el("table", {},
            el("thead", {}, el("tr", {}, el("th", {}, r("kpi")), el("th", {}, r("target")), el("th", {}, r("why")))),
            el("tbody", {}, (d.kpis || []).map((k) =>
                el("tr", {}, el("td", {}, el("strong", {}, k.name)), el("td", {}, k.target), el("td", {}, k.why)))))];
    },
};

function sectionCard(key, data) {
    const r = (k) => t(k, state.reportLang);
    const render = renderers[key] || (() => el("pre", {}, JSON.stringify(data, null, 2)));
    const body = el("div", { class: "card-body" }, render(data, r));
    const regen = el("button", { class: "btn btn-secondary btn-sm no-print", title: t("regenerateTitle"), onclick: () => regenerate(key) }, t("regenerate"));
    const card = el("article", { class: `card${key === "summary" ? " summary-card" : ""}`, id: `sec-${key}` });
    if (key === "summary") {
        card.append(...body.childNodes);
        const actions = el("div", { class: "card-actions" }, regen);
        actions.style.gridColumn = "1 / -1";
        card.append(actions);
    } else {
        card.append(el("div", { class: "card-head" }, el("h3", {}, r(`sec_${key}`)), el("div", { class: "card-actions" }, regen)), body);
    }
    return card;
}

/** Insert or replace a section, keeping the fixed section order (summary first). */
function putSection({ key, data }) {
    state.sections[key] = data;
    const card = sectionCard(key, data);
    const existing = $(`sec-${key}`);
    if (existing) return existing.replaceWith(card);
    const after = SECTION_ORDER.slice(SECTION_ORDER.indexOf(key) + 1).map((k) => $(`sec-${k}`)).find(Boolean);
    $("sections").insertBefore(card, after || null);
}

function rerenderSections() {
    for (const [key, data] of Object.entries(state.sections)) putSection({ key, data });
}

// ---------- report view ----------
function openReportView(idea, createdAt, lang) {
    state.sections = {};
    state.reportLang = lang;
    $("sections").replaceChildren();
    $("chatLog").replaceChildren();
    // the report body follows its own language, whatever the UI language is
    for (const id of ["reportTitle", "sections", "chatLog"]) {
        $(id).lang = lang;
        $(id).dir = lang === "en" ? "ltr" : "rtl";
    }
    $("reportTitle").textContent = idea.length > 90 ? idea.slice(0, 90) + "…" : idea;
    $("reportMeta").textContent = createdAt ? new Date(createdAt).toLocaleString(state.lang) : "";
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
        state.industry = r.industry;
        state.strategy = r.strategy;
        openReportView(r.idea, r.created_at, r.language || "ar");
        r.sections.forEach(putSection);
        setProgress(TOTAL_SECTIONS);
        r.messages.forEach((m) => addMessage(m.role, m.content));
        $("chat").hidden = r.sections.length === 0;
        if (r.status === "error") showAlert(t("incomplete"));
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
    state.industry = $("industry").value;
    state.strategy = $("strategy").value;
    state.questionsLang = state.lang;
    setBusy(true);
    setLoading(true, t("preparingQuestions"));
    try {
        const { questions } = await api("/api/clarify", {
            method: "POST",
            body: JSON.stringify(ideaPayload()),
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
    // the report uses the language the questions were asked in
    await runAnalysis({ ...ideaPayload(state.questionsLang), answers });
});

async function runAnalysis(payload) {
    showAlert("");
    setBusy(true);
    openReportView(payload.idea, new Date().toISOString(), payload.language);
    $("chat").hidden = true;
    setProgress(0);
    setLoading(true, t("buildingReport"));
    let count = 0;
    try {
        await streamSSE("/api/analyze", payload, (event, data) => {
            if (event === "report") state.reportId = data.id;
            else if (event === "section") {
                putSection(data);
                setProgress(++count);
                $("loadingText").textContent = t("sectionDone")(t(`sec_${data.key}`), count, TOTAL_SECTIONS);
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
    const instructions = prompt(t("regeneratePrompt"), "");
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
            const del = el("button", { class: "h-del", title: t("del"), "aria-label": t("delReport") }, "×");
            del.addEventListener("click", async (ev) => {
                ev.stopPropagation();
                if (!confirm(t("confirmDelete"))) return;
                try {
                    await api(`/api/reports/${r.id}`, { method: "DELETE" });
                    if (state.reportId === r.id) resetToNew();
                    refreshHistory();
                } catch (err) { showAlert(err.message); }
            });
            const li = el("li", { "data-id": r.id, title: r.title },
                el("span", { class: "h-title", dir: "auto" }, r.title),
                r.score != null ? el("span", { class: "h-score" }, r.score) : null,
                del);
            li.addEventListener("click", () => loadReport(r.id));
            return li;
        });
        $("historyList").replaceChildren(...(items.length ? items : [el("li", { class: "empty" }, t("noReports"))]));
        markActive(state.reportId);
    } catch (_) { /* sidebar is best-effort */ }
}

function resetToNew() {
    if (state.busy) return;
    state.reportId = null;
    state.sections = {};
    $("ideaForm").reset();
    showAlert("");
    show("idea");
    markActive(null);
    $("idea").focus();
}

function ideaPayload(language = state.lang) {
    return { idea: state.idea, goals: state.goals, industry: state.industry, strategy: state.strategy, language };
}

// ---------- templates (industry / strategy dropdowns) ----------
async function loadTemplates() {
    try {
        state.templates = await api("/api/templates");
    } catch {
        state.templates = { industries: [], strategies: [] };  // keep "auto" only; analysis still works
    }
    fillTemplates();
}

function fillTemplates() {
    if (!state.templates) return;
    const fill = (id, items, prefix) => {
        const select = $(id);
        const current = select.value;
        select.replaceChildren(el("option", { value: "auto" }, t("auto")),
            ...items.map((i) => el("option", { value: i.key }, I18N[state.lang][prefix + i.key] ?? i.label)));
        select.value = current || "auto";
    };
    fill("industry", state.templates.industries, "ind_");
    fill("strategy", state.templates.strategies, "str_");
}

// ---------- start ----------
$("newBtn").addEventListener("click", resetToNew);
$("printBtn").addEventListener("click", () => window.print());
$("langBtn").addEventListener("click", toggleLanguage);
$("themeBtn").addEventListener("click", toggleTheme);

applyTheme();
applyLanguage();
loadTemplates();
