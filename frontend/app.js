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
        // accounts
        logout: "تسجيل الخروج",
        loginTitle: "تسجيل الدخول", loginLead: "مرحباً بعودتك إلى مستشار.",
        registerTitle: "إنشاء حساب", registerLead: "أنشئ حساباً مجانياً لتحليل أفكارك وحفظ تقاريرك.",
        email: "البريد الإلكتروني", password: "كلمة المرور", name: "الاسم",
        passwordHint: "8 أحرف على الأقل.", newPassword: "كلمة المرور الجديدة", confirmPassword: "تأكيد كلمة المرور",
        loginBtn: "دخول", registerBtn: "إنشاء الحساب", or: "أو",
        google: "المتابعة باستخدام Google", googleError: "تعذر تسجيل الدخول عبر Google. يرجى المحاولة مرة أخرى.",
        noAccount: "ليس لديك حساب؟ أنشئ حساباً", haveAccount: "لديك حساب؟ سجّل الدخول",
        forgotLink: "نسيت كلمة المرور؟", backToLogin: "العودة لتسجيل الدخول",
        forgotTitle: "نسيت كلمة المرور", forgotLead: "أدخل بريدك وسنرسل إليك رابطاً لإعادة تعيين كلمة المرور.",
        sendLink: "إرسال الرابط", forgotSent: "إذا كان البريد مسجلاً لدينا، فقد أرسلنا إليه رابط إعادة التعيين. تحقق من بريدك.",
        resetTitle: "تعيين كلمة مرور جديدة", resetBtn: "حفظ كلمة المرور", passwordsDiffer: "كلمتا المرور غير متطابقتين.",
        resetDone: "تم تغيير كلمة المرور وتسجيل دخولك.", missingToken: "الرابط غير مكتمل. يرجى فتحه من البريد مرة أخرى.",
        verifyTitle: "تأكيد البريد الإلكتروني", verifying: "جاري تأكيد بريدك...", verified: "تم تأكيد بريدك الإلكتروني. شكراً!",
        continue: "متابعة",
        verifyBanner: "يرجى تأكيد بريدك الإلكتروني عبر الرابط الذي أرسلناه إليك.", resend: "إعادة إرسال الرابط",
        resent: "أرسلنا رابط تأكيد جديداً إلى بريدك.",
        welcomeTitle: (n) => n ? `أهلاً ${n}!` : "أهلاً بك!",
        welcomeLead: "حسابك جاهز. ابدأ بتحليل فكرتك الأولى، وسنساعدك قريباً في اختيار الباقة الأنسب لك.",
        startFirst: "ابدأ التحليل الأول",
        heroTitle: "حوّل فكرتك إلى استراتيجية واضحة",
        heroLead: "مستشار يحلل فكرتك التجارية كما يفعل مستشار خبير، في دقائق.",
        heroPoints: [
            "تحليل كامل في 8 أقسام: السوق والمنافسون والمخاطر والتوقعات المالية وخارطة الطريق",
            "قوالب متخصصة حسب القطاع ونوع الاستراتيجية",
            "اسأل عن تقريرك وجرّب سيناريوهات «ماذا لو»",
        ],
        // plan limits
        templatesLocked: "🔒 القوالب المتخصصة متاحة في الباقات المدفوعة.",
        regenLocked: "إعادة توليد الأقسام غير متاحة في باقتك الحالية. قم بالترقية لاستخدامها.",
        watermarkText: "مستشار — الباقة المجانية",
        chatLeft: (left, limit) => `تبقّى لك ${left} من ${limit} أسئلة متابعة لهذا التقرير.`,
        // accounts
        logout: "تسجيل الخروج",
        loginTitle: "تسجيل الدخول", loginLead: "مرحباً بعودتك إلى مستشار.",
        registerTitle: "إنشاء حساب", registerLead: "أنشئ حساباً مجانياً لتحليل أفكارك وحفظ تقاريرك.",
        email: "البريد الإلكتروني", password: "كلمة المرور", name: "الاسم",
        passwordHint: "8 أحرف على الأقل.", newPassword: "كلمة المرور الجديدة", confirmPassword: "تأكيد كلمة المرور",
        loginBtn: "دخول", registerBtn: "إنشاء الحساب", or: "أو",
        google: "المتابعة باستخدام Google", googleError: "تعذر تسجيل الدخول عبر Google. يرجى المحاولة مرة أخرى.",
        noAccount: "ليس لديك حساب؟ أنشئ حساباً", haveAccount: "لديك حساب؟ سجّل الدخول",
        forgotLink: "نسيت كلمة المرور؟", backToLogin: "العودة لتسجيل الدخول",
        forgotTitle: "نسيت كلمة المرور", forgotLead: "أدخل بريدك وسنرسل إليك رابطاً لإعادة تعيين كلمة المرور.",
        sendLink: "إرسال الرابط", forgotSent: "إذا كان البريد مسجلاً لدينا، فقد أرسلنا إليه رابط إعادة التعيين. تحقق من بريدك.",
        resetTitle: "تعيين كلمة مرور جديدة", resetBtn: "حفظ كلمة المرور", passwordsDiffer: "كلمتا المرور غير متطابقتين.",
        resetDone: "تم تغيير كلمة المرور وتسجيل دخولك.", missingToken: "الرابط غير مكتمل. يرجى فتحه من البريد مرة أخرى.",
        verifyTitle: "تأكيد البريد الإلكتروني", verifying: "جاري تأكيد بريدك...", verified: "تم تأكيد بريدك الإلكتروني. شكراً!",
        continue: "متابعة",
        verifyBanner: "يرجى تأكيد بريدك الإلكتروني عبر الرابط الذي أرسلناه إليك.", resend: "إعادة إرسال الرابط",
        resent: "أرسلنا رابط تأكيد جديداً إلى بريدك.",
        welcomeTitle: (n) => n ? `أهلاً ${n}!` : "أهلاً بك!",
        welcomeLead: "حسابك جاهز. ابدأ بتحليل فكرتك الأولى، وسنساعدك قريباً في اختيار الباقة الأنسب لك.",
        startFirst: "ابدأ التحليل الأول",
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
        logout: "Log out",
        loginTitle: "Log in", loginLead: "Welcome back to Mustashar.",
        registerTitle: "Create an account", registerLead: "Create a free account to analyze your ideas and keep your reports.",
        email: "Email", password: "Password", name: "Name",
        passwordHint: "At least 8 characters.", newPassword: "New password", confirmPassword: "Confirm password",
        loginBtn: "Log in", registerBtn: "Create account", or: "or",
        google: "Continue with Google", googleError: "Google sign-in didn't work. Please try again.",
        noAccount: "No account? Create one", haveAccount: "Already have an account? Log in",
        forgotLink: "Forgot your password?", backToLogin: "Back to log in",
        forgotTitle: "Forgot password", forgotLead: "Enter your email and we'll send you a link to reset your password.",
        sendLink: "Send link", forgotSent: "If this email is registered, we've sent it a reset link. Check your inbox.",
        resetTitle: "Set a new password", resetBtn: "Save password", passwordsDiffer: "The passwords don't match.",
        resetDone: "Your password was changed and you're logged in.", missingToken: "This link is incomplete. Please open it from the email again.",
        verifyTitle: "Confirm your email", verifying: "Confirming your email...", verified: "Your email is confirmed. Thank you!",
        continue: "Continue",
        verifyBanner: "Please confirm your email using the link we sent you.", resend: "Resend link",
        resent: "We sent a new confirmation link to your email.",
        welcomeTitle: (n) => n ? `Welcome, ${n}!` : "Welcome!",
        welcomeLead: "Your account is ready. Start with your first analysis; soon we'll also help you pick the plan that fits you best.",
        startFirst: "Start your first analysis",
        heroTitle: "Turn your idea into a clear strategy",
        heroLead: "Mustashar analyzes your business idea the way an expert consultant would, in minutes.",
        heroPoints: [
            "A full analysis in 8 sections: market, competitors, risks, financial outlook and roadmap",
            "Specialized templates by industry and strategy type",
            "Ask about your report and explore \"what if\" scenarios",
        ],
        templatesLocked: "🔒 Specialized templates are part of the paid plans.",
        regenLocked: "Regenerating sections isn't included in your current plan. Upgrade to use it.",
        watermarkText: "Mustashar — Free plan",
        chatLeft: (left, limit) => `${left} of ${limit} follow-up questions left for this report.`,
        logout: "Log out",
        loginTitle: "Log in", loginLead: "Welcome back to Mustashar.",
        registerTitle: "Create an account", registerLead: "Create a free account to analyze your ideas and keep your reports.",
        email: "Email", password: "Password", name: "Name",
        passwordHint: "At least 8 characters.", newPassword: "New password", confirmPassword: "Confirm password",
        loginBtn: "Log in", registerBtn: "Create account", or: "or",
        google: "Continue with Google", googleError: "Google sign-in didn't work. Please try again.",
        noAccount: "No account? Create one", haveAccount: "Already have an account? Log in",
        forgotLink: "Forgot your password?", backToLogin: "Back to log in",
        forgotTitle: "Forgot password", forgotLead: "Enter your email and we'll send you a link to reset your password.",
        sendLink: "Send link", forgotSent: "If this email is registered, we've sent it a reset link. Check your inbox.",
        resetTitle: "Set a new password", resetBtn: "Save password", passwordsDiffer: "The passwords don't match.",
        resetDone: "Your password was changed and you're logged in.", missingToken: "This link is incomplete. Please open it from the email again.",
        verifyTitle: "Confirm your email", verifying: "Confirming your email...", verified: "Your email is confirmed. Thank you!",
        continue: "Continue",
        verifyBanner: "Please confirm your email using the link we sent you.", resend: "Resend link",
        resent: "We sent a new confirmation link to your email.",
        welcomeTitle: (n) => n ? `Welcome, ${n}!` : "Welcome!",
        welcomeLead: "Your account is ready. Start with your first analysis; soon we'll also help you pick the plan that fits you best.",
        startFirst: "Start your first analysis",
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
    user: null,   // logged-in user from /api/me, or null
    plan: null,   // /api/me/plan: usage and what's unlocked
    reportFeatures: null,          // what the open report allows
    chat: { used: 0, limit: null }, // follow-up questions on the open report
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
    renderChatQuota();
    renderNav();
    if (!$("authView").hidden) route();  // rebuild the open account screen in the new language
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
/** Value of the CSRF cookie, echoed in a header on every request (double-submit protection). */
function csrfToken() {
    const m = document.cookie.match(/(?:^|;\s*)mustashar_csrf=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
}

function apiHeaders() {
    return { "Content-Type": "application/json", "X-Lang": state.lang, "X-CSRF-Token": csrfToken() };
}

async function api(path, options = {}) {
    const res = await fetch(path, {
        headers: apiHeaders(),
        ...options,
    });
    if (!res.ok) {
        const msg = await errorMessage(res);
        if (res.status === 401 && !path.startsWith("/api/auth/") && path !== "/api/me") onLoggedOut();
        throw new Error(msg);
    }
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
        headers: apiHeaders(),
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
    const locked = state.reportFeatures && !state.reportFeatures.regenerate;
    const regen = locked
        ? el("button", { class: "btn btn-secondary btn-sm no-print locked", title: t("regenLocked"), onclick: () => showAlert(t("regenLocked")) }, "🔒 " + t("regenerate"))
        : el("button", { class: "btn btn-secondary btn-sm no-print", title: t("regenerateTitle"), onclick: () => regenerate(key) }, t("regenerate"));
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
    if (parseHash().path) go("");  // leave an account screen (e.g. welcome)
    showAlert("");
    try {
        const r = await api(`/api/reports/${id}`);
        state.reportId = r.id;
        state.idea = r.idea;
        state.goals = r.goals;
        state.industry = r.industry;
        state.strategy = r.strategy;
        openReportView(r.idea, r.created_at, r.language || "ar");
        applyReportTerms(r);
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
    applyReportTerms({ features: state.plan?.next_report_features, chat: { used: 0, limit: null } });
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
        loadPlan();
        if (state.reportId) api(`/api/reports/${state.reportId}`).then(applyReportTerms).catch(() => {});
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
    let failed = false;
    const reply = addMessage("assistant", "…");
    let text = "";
    setBusy(true);
    try {
        await streamSSE(`/api/reports/${state.reportId}/chat`, { message }, (event, data) => {
            if (event === "delta") {
                text += data.text;
                reply.innerHTML = renderMarkdown(text);
            } else if (event === "error") {
                failed = true;
                reply.remove();
                showAlert(data.message);
            }
        });
        if (!failed) { state.chat.used++; renderChatQuota(); }
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
    if (!state.user) return;
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

// ---------- accounts: session, screens and routing ----------
const GOOGLE_ICON = '<svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3l5.7-5.7C34 6 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3l5.7-5.7C34 6 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>';

const AUTH_ROUTES = new Set(["login", "register", "forgot", "reset", "verify"]);
const PAGE_ROUTES = new Set(Object.keys(PUBLIC_PAGES));  // about, pricing, portfolio, contact (pages.js)
const PUBLIC_ROUTES = new Set([...AUTH_ROUTES, ...PAGE_ROUTES]);

function parseHash() {
    const raw = location.hash.replace(/^#\/?/, "");
    const [path, query = ""] = raw.split("?");
    return { path: path || "", params: new URLSearchParams(query) };
}

function go(path) {
    if (location.hash === `#/${path}`) route();
    else location.hash = `#/${path}`;
}

function showNotice(msg) {
    $("notice").textContent = msg;
    $("notice").hidden = !msg;
}

async function loadMe() {
    try {
        state.user = await api("/api/me");
    } catch {
        state.user = null;
    }
    renderUserChrome();
    await loadPlan();
}

function renderUserChrome() {
    const u = state.user;
    $("userMenu").hidden = !u;
    renderNav();
    $("sidebar").hidden = !u;
    document.querySelector(".layout").classList.toggle("no-sidebar", !u);
    $("verifyBanner").hidden = !u || u.email_verified;
    if (u) {
        $("userName").textContent = u.name || u.email;
        $("userName").title = u.email;
    }
}

function onLoggedIn(user, next = "") {
    state.user = user;
    renderUserChrome();
    loadPlan();
    resetToNew();
    refreshHistory();
    go(next);
}

function onLoggedOut() {
    state.user = null;
    state.plan = null;
    state.reportId = null;
    state.sections = {};
    $("historyList").replaceChildren();
    renderUserChrome();
    go("login");
}

/** Build an account card: title, lead text, extra body, optional Google button, form, links below. */
function authCard({ title, lead, fields = [], submit, onSubmit, google = false, links = [], body = [] }) {
    const inputs = fields.map((f) => el("div", {},
        el("label", { for: `f-${f.id}` }, t(f.label)),
        el("input", {
            id: `f-${f.id}`, type: f.type || "text", autocomplete: f.auto || "off", maxlength: f.max || "254",
            ...(f.required !== false ? { required: "" } : {}), ...(f.min ? { minlength: String(f.min) } : {}),
        }),
        f.hint ? el("p", { class: "field-hint" }, t(f.hint)) : null));
    const form = submit ? el("form", { novalidate: "" }, inputs, el("button", { class: "btn btn-primary", type: "submit" }, t(submit))) : null;
    form?.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!form.reportValidity()) return;
        showAlert("");
        const btn = form.querySelector("button[type=submit]");
        btn.disabled = true;
        try {
            const values = Object.fromEntries(fields.map((f) => [f.id, $(`f-${f.id}`).value]));
            await onSubmit(values);
        } catch (err) {
            showAlert(err.message);
        } finally {
            btn.disabled = false;
        }
    });
    let googleBtn = null;
    if (google) {
        const a = el("a", { class: "btn btn-google", href: `/api/auth/google/start?lang=${state.lang}` });
        a.innerHTML = GOOGLE_ICON;  // static, trusted markup
        a.append(t("google"));
        googleBtn = [a, el("div", { class: "divider" }, t("or"))];
    }
    return el("div", { class: "panel auth" },
        el("h2", {}, title), lead ? el("p", { class: "lead" }, lead) : null,
        body, googleBtn, form,
        links.length ? el("div", { class: "links" }, links.map(([label, path]) => el("a", { href: `#/${path}` }, t(label)))) : null);
}

const screens = {
    login(params) {
        const card = authCard({
            title: t("loginTitle"), lead: t("loginLead"), google: true,
            fields: [{ id: "email", label: "email", type: "email", auto: "email" },
                     { id: "password", label: "password", type: "password", auto: "current-password", max: "128" }],
            submit: "loginBtn",
            onSubmit: async (v) => onLoggedIn(await api("/api/auth/login", { method: "POST", body: JSON.stringify(v) })),
            links: [["forgotLink", "forgot"], ["noAccount", "register"]],
        });
        if (params.get("error") === "google") setTimeout(() => showAlert(t("googleError")));
        return card;
    },
    register() {
        return authCard({
            title: t("registerTitle"), lead: t("registerLead"), google: true,
            fields: [{ id: "name", label: "name", auto: "name", max: "100", required: false },
                     { id: "email", label: "email", type: "email", auto: "email" },
                     { id: "password", label: "password", type: "password", auto: "new-password", min: 8, max: "128", hint: "passwordHint" }],
            submit: "registerBtn",
            onSubmit: async (v) => onLoggedIn(await api("/api/auth/register", {
                method: "POST", body: JSON.stringify({ ...v, language: state.lang }) }), "welcome"),
            links: [["haveAccount", "login"]],
        });
    },
    forgot() {
        return authCard({
            title: t("forgotTitle"), lead: t("forgotLead"),
            fields: [{ id: "email", label: "email", type: "email", auto: "email" }],
            submit: "sendLink",
            onSubmit: async (v) => {
                await api("/api/auth/password/forgot", { method: "POST", body: JSON.stringify(v) });
                showNotice(t("forgotSent"));
            },
            links: [["backToLogin", "login"]],
        });
    },
    reset(params) {
        const token = params.get("token");
        if (!token) return authCard({ title: t("resetTitle"), lead: t("missingToken"), links: [["forgotLink", "forgot"]] });
        return authCard({
            title: t("resetTitle"),
            fields: [{ id: "password", label: "newPassword", type: "password", auto: "new-password", min: 8, max: "128", hint: "passwordHint" },
                     { id: "confirm", label: "confirmPassword", type: "password", auto: "new-password", min: 8, max: "128" }],
            submit: "resetBtn",
            onSubmit: async (v) => {
                if (v.password !== v.confirm) throw new Error(t("passwordsDiffer"));
                const user = await api("/api/auth/password/reset", {
                    method: "POST", body: JSON.stringify({ token, password: v.password }) });
                onLoggedIn(user);
                showNotice(t("resetDone"));
            },
        });
    },
    verify(params) {
        const token = params.get("token");
        const status = el("p", { class: "lead" }, token ? t("verifying") : t("missingToken"));
        const card = authCard({ title: t("verifyTitle"), body: [status] });
        if (token) {
            api("/api/auth/verify", { method: "POST", body: JSON.stringify({ token }) })
                .then((user) => {
                    status.textContent = t("verified");
                    if (state.user && state.user.id === user.id) { state.user = user; renderUserChrome(); }
                    card.append(el("a", { class: "btn btn-primary", href: state.user ? "#/" : "#/login" }, t("continue")));
                })
                .catch((err) => { status.textContent = err.message; });
        }
        return card;
    },
    welcome() {
        return authCard({
            title: t("welcomeTitle")(state.user?.name), lead: t("welcomeLead"),
            body: [el("img", { src: "logo.svg", alt: "", class: "welcome-icon" }),
                   el("a", { class: "btn btn-primary", href: "#/" }, t("startFirst"))],
        });
    },
};

// ---------- top navigation ----------
const NAV_ITEMS = ["", "about", "pricing", "portfolio", "contact"];

function renderNav() {
    const x = PAGE_TEXT[state.lang] || PAGE_TEXT.ar;
    const current = parseHash().path;
    const names = { "": "home", about: "about", pricing: "pricing", portfolio: "portfolio", contact: "contact" };
    $("mainNav").replaceChildren(...NAV_ITEMS.map((p) => el("a", {
        href: `#/${p}`, class: current === p || (p === "" && !PUBLIC_ROUTES.has(current) && current !== "welcome") ? "active" : "",
    }, x.nav[names[p]])));
    $("guestMenu").replaceChildren(...(state.user ? [] : [
        el("a", { class: "btn btn-secondary btn-sm", href: "#/login" }, x.login),
        el("a", { class: "btn btn-primary btn-sm", href: "#/register" }, x.signup),
    ]));
    $("guestMenu").hidden = !!state.user;
    $("menuBtn").setAttribute("aria-label", x.menu);
}

function closeMenu() {
    document.body.classList.remove("menu-open");
    $("menuBtn").setAttribute("aria-expanded", "false");
}

$("menuBtn").addEventListener("click", () => {
    const open = document.body.classList.toggle("menu-open");
    $("menuBtn").setAttribute("aria-expanded", String(open));
});

/** Brand panel shown next to the login / sign-up forms. */
function heroPanel() {
    return el("aside", { class: "hero" },
        el("img", { src: "logo.svg", alt: "", class: "hero-logo" }),
        el("p", { class: "hero-name" }, t("appName")),
        el("h2", {}, t("heroTitle")),
        el("p", {}, t("heroLead")),
        el("ul", {}, t("heroPoints").map((x) => el("li", {}, x))));
}

/** Show the screen for the current #/path. Logged-out users only see the public screens. */
function route() {
    const { path, params } = parseHash();
    showAlert("");
    if (!state.user && !PUBLIC_ROUTES.has(path)) return go("login");
    if (state.user && (path === "login" || path === "register")) return go("");
    const screen = screens[path] || PUBLIC_PAGES[path];
    const authMode = AUTH_ROUTES.has(path);
    renderNav();
    closeMenu();
    document.body.classList.toggle("auth-mode", authMode);
    $("authView").hidden = !screen;
    $("appView").hidden = !!screen;
    if (screen) {
        showNotice("");
        const card = screen(params);
        $("authView").replaceChildren(authMode ? el("div", { class: "auth-shell" }, heroPanel(), card) : card);
        if (authMode) $("authView").querySelector("input")?.focus();
        window.scrollTo({ top: 0 });
    }
}

$("logoutBtn").addEventListener("click", async () => {
    try { await api("/api/auth/logout", { method: "POST" }); } catch { /* logged out anyway */ }
    onLoggedOut();
});

$("resendBtn").addEventListener("click", async () => {
    try {
        await api("/api/auth/verify/resend", { method: "POST" });
        showNotice(t("resent"));
    } catch (err) { showAlert(err.message); }
});

window.addEventListener("hashchange", route);

// ---------- plan limits in the UI (the server enforces them too) ----------
async function loadPlan() {
    if (!state.user) { state.plan = null; return; }
    try {
        state.plan = await api("/api/me/plan");
    } catch {
        state.plan = null;
    }
    applyPlanLocks();
}

function applyPlanLocks() {
    const templatesOk = state.plan?.next_report_features?.templates ?? true;
    for (const id of ["industry", "strategy"]) {
        $(id).disabled = !templatesOk;
        if (!templatesOk) $(id).value = "auto";
    }
    $("templatesLock").hidden = templatesOk;
}

/** Features and chat usage of the open report (from GET /api/reports/{id}). */
function applyReportTerms(r) {
    state.reportFeatures = r.features || null;
    state.chat = { ...(r.chat || { used: 0, limit: null }) };
    $("watermark").hidden = !state.reportFeatures?.watermark;
    rerenderSections();
    renderChatQuota();
}

function renderChatQuota() {
    const { used, limit } = state.chat;
    const q = $("chatQuota");
    q.hidden = limit == null;
    if (limit == null) return;
    const left = Math.max(0, limit - used);
    q.textContent = t("chatLeft")(left, limit);
    q.classList.toggle("lock-hint", left === 0);
}

// ---------- start ----------
$("newBtn").addEventListener("click", () => { if (parseHash().path) go(""); resetToNew(); });
$("printBtn").addEventListener("click", () => window.print());
$("langBtn").addEventListener("click", toggleLanguage);
$("themeBtn").addEventListener("click", toggleTheme);

applyTheme();
applyLanguage();
loadTemplates();
loadMe().then(() => { route(); refreshHistory(); });
