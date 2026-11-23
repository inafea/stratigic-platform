"use strict";
/*
 * Public pages: About us, Pricing, Portfolio, Contact us.
 * Loaded before app.js; uses its helpers (el, t, state, api, showAlert, showNotice) at render time.
 * Text lives in PAGE_TEXT (Arabic + English). Edit it freely: it's content, not code.
 */

const PAGE_TEXT = {
    ar: {
        nav: { home: "الرئيسية", about: "من نحن", pricing: "الأسعار", portfolio: "أعمالنا", contact: "تواصل معنا" },
        login: "تسجيل الدخول", signup: "إنشاء حساب", menu: "القائمة",

        about: {
            title: "من نحن",
            lead: "«مستشار» منصة عربية تستخدم الذكاء الاصطناعي لتحويل فكرة العمل إلى استراتيجية واضحة وقابلة للتنفيذ، بجودة تقترب من عمل المستشار الخبير، وفي دقائق بدلاً من أسابيع.",
            missionTitle: "مهمتنا",
            mission: "أن يحصل كل رائد أعمال في العالم العربي على استشارة استراتيجية مهنية بلغته وبما يناسب سوقه، مهما كانت ميزانيته.",
            howTitle: "كيف يعمل مستشار",
            steps: [
                ["صف فكرتك", "اكتب فكرتك وأهدافك، واختر القطاع ونوع الاستراتيجية إن أردت."],
                ["أجب عن أسئلة قصيرة", "يطرح مستشار أسئلة توضيحية ليفهم ميزانيتك وسوقك وفريقك."],
                ["احصل على تقريرك", "تحليل في 8 أقسام مع درجة جدوى، ثم اسأل عنه وطوّره."],
            ],
            valuesTitle: "ما الذي يميّزنا",
            values: [
                ["عربي أولاً", "مصمم للأسواق العربية: الأنظمة المحلية، وسائل الدفع، وسلوك المستهلك."],
                ["صراحة لا مجاملة", "نوضّح المخاطر ونقاط الضعف بوضوح، لأن المجاملة لا تفيد صاحب الفكرة."],
                ["عملي وقابل للتنفيذ", "أرقام تقديرية وخطة 30/60/90 يوماً ومؤشرات أداء يمكنك متابعتها."],
                ["خصوصية بياناتك", "تقاريرك خاصة بحسابك فقط، ولا يطّلع عليها أي مستخدم آخر."],
            ],
            cta: "ابدأ تحليلك الأول مجاناً",
        },

        pricing: {
            title: "الأسعار",
            lead: "ابدأ مجاناً، وانتقل إلى الباقة التي تناسب حجم عملك عندما تحتاج.",
            monthly: "شهري", yearly: "سنوي", save: (p) => `وفّر ${p}%`,
            perMonth: "/ شهرياً", perYear: "/ سنوياً", free: "مجاناً",
            popular: "الأكثر طلباً",
            reports: (n) => `${n} تقارير شهرياً`,
            chat: (n) => n == null ? "أسئلة متابعة غير محدودة" : `${n} أسئلة متابعة لكل تقرير`,
            tier: { lite: "نموذج ذكاء اصطناعي أساسي", standard: "نموذج ذكاء اصطناعي متقدم", premium: "أفضل نموذج ذكاء اصطناعي متاح" },
            templates: "قوالب القطاعات وأنواع الاستراتيجية", regenerate: "إعادة توليد أي قسم",
            noWatermark: "تصدير PDF بدون علامة مائية", watermark: "تصدير PDF بعلامة مائية",
            seats: (n) => `حتى ${n} مستخدمين`, branded: "PDF بشعار شركتك",
            startFree: "ابدأ مجاناً", current: "باقتك الحالية", soon: "قريباً",
            packsTitle: "باقات التقارير", packsLead: "لا تريد اشتراكاً؟ اشترِ تقارير حسب حاجتك، صالحة لمدة 12 شهراً وبأفضل نموذج.",
            credits: (n) => n === 1 ? "تقرير واحد" : `${n} تقارير`,
            paymentsSoon: "الدفع الإلكتروني (مدى، Apple Pay، STC Pay، البطاقات) قيد الإعداد وسيتوفر قريباً.",
        },

        portfolio: {
            title: "أعمالنا",
            lead: "نماذج توضيحية لتحليلات يُعدّها مستشار لأفكار من قطاعات مختلفة. كل تحليل حقيقي يحتوي على 8 أقسام كاملة.",
            example: "مثال توضيحي", score: "درجة الجدوى",
            items: [
                { title: "مطعم وجبات صحية للطلاب في الرياض", industry: "المطاعم والأغذية", score: 80,
                  points: ["نموذج اشتراكات شهرية ونقاط استلام قرب الجامعات", "تكلفة الطعام المستهدفة 30–33% من المبيعات", "تأجيل الفرع الثاني حتى تحقيق التعادل"] },
                { title: "منصة لإدارة ومتابعة الصيانة للشركات", industry: "البرمجيات (SaaS)", score: 72,
                  points: ["تسعير متدرج حسب عدد الأصول", "التركيز على الشركات المتوسطة أولاً", "مؤشرات: الإيراد الشهري المتكرر ونسبة الإلغاء"] },
                { title: "شركة خدمات سحابية وDevOps", industry: "الخدمات المهنية", score: 76,
                  points: ["عقود شهرية بدلاً من المشاريع المنفردة", "شراكات مع مزودي السحابة", "خطر الاعتماد على عدد قليل من العملاء"] },
                { title: "متجر إلكتروني لمنتجات العناية الطبيعية", industry: "التجارة الإلكترونية", score: 68,
                  points: ["البيع عبر متجر خاص والأسواق الإلكترونية", "نسبة LTV/CAC المستهدفة 3 أو أكثر", "خطر ارتفاع تكلفة الإعلانات"] },
            ],
            cta: "حلّل فكرتك الآن",
        },

        contact: {
            title: "تواصل معنا",
            lead: "لديك سؤال أو اقتراح أو ترغب في شراكة؟ أرسل لنا رسالة وسنعود إليك في أقرب وقت.",
            name: "الاسم", email: "البريد الإلكتروني", subject: "الموضوع (اختياري)", message: "رسالتك",
            send: "إرسال الرسالة", sent: "شكراً لك! وصلتنا رسالتك وسنرد عليك عبر البريد الإلكتروني.",
            sideTitle: "كيف يمكننا مساعدتك؟",
            side: ["أسئلة عن الباقات والأسعار", "الشراكات مع الحاضنات والجهات التعليمية", "الملاحظات والاقتراحات لتحسين مستشار"],
        },
    },

    en: {
        nav: { home: "Home", about: "About us", pricing: "Pricing", portfolio: "Portfolio", contact: "Contact us" },
        login: "Log in", signup: "Sign up", menu: "Menu",

        about: {
            title: "About us",
            lead: "Mustashar is an Arabic-first platform that uses AI to turn a business idea into a clear, actionable strategy, close to the work of an expert consultant, in minutes instead of weeks.",
            missionTitle: "Our mission",
            mission: "To give every founder in the Arab world professional strategic advice in their language and fitted to their market, whatever their budget.",
            howTitle: "How Mustashar works",
            steps: [
                ["Describe your idea", "Write your idea and goals, and optionally pick an industry and strategy type."],
                ["Answer a few questions", "Mustashar asks clarifying questions to understand your budget, market and team."],
                ["Get your report", "An 8-section analysis with a viability score; then ask about it and refine it."],
            ],
            valuesTitle: "What makes us different",
            values: [
                ["Arabic first", "Built for Arab markets: local regulations, payment methods and consumer behavior."],
                ["Honest, not flattering", "We spell out risks and weaknesses, because flattery doesn't help a founder."],
                ["Practical", "Estimated numbers, a 30/60/90-day plan and KPIs you can track."],
                ["Your data stays private", "Your reports belong to your account only; no other user can see them."],
            ],
            cta: "Start your first analysis for free",
        },

        pricing: {
            title: "Pricing",
            lead: "Start for free, and move to the plan that fits your work when you need it.",
            monthly: "Monthly", yearly: "Yearly", save: (p) => `Save ${p}%`,
            perMonth: "/ month", perYear: "/ year", free: "Free",
            popular: "Most popular",
            reports: (n) => `${n} reports per month`,
            chat: (n) => n == null ? "Unlimited follow-up questions" : `${n} follow-up questions per report`,
            tier: { lite: "Standard AI model", standard: "Advanced AI model", premium: "Best available AI model" },
            templates: "Industry and strategy-type templates", regenerate: "Regenerate any section",
            noWatermark: "PDF export without watermark", watermark: "PDF export with watermark",
            seats: (n) => `Up to ${n} users`, branded: "PDF with your company logo",
            startFree: "Start for free", current: "Your current plan", soon: "Coming soon",
            packsTitle: "Report packs", packsLead: "Don't want a subscription? Buy reports as you need them, valid for 12 months, with the best model.",
            credits: (n) => n === 1 ? "1 report" : `${n} reports`,
            paymentsSoon: "Online payment (mada, Apple Pay, STC Pay, cards) is being set up and will be available soon.",
        },

        portfolio: {
            title: "Portfolio",
            lead: "Illustrative examples of analyses Mustashar prepares for ideas in different industries. Every real analysis has 8 full sections.",
            example: "Example", score: "Viability",
            items: [
                { title: "Healthy meal subscriptions for students in Riyadh", industry: "Restaurants & food", score: 80,
                  points: ["Monthly subscriptions and pickup points near universities", "Target food cost of 30–33% of sales", "Second branch postponed until break-even"] },
                { title: "Maintenance management platform for companies", industry: "Software (SaaS)", score: 72,
                  points: ["Tiered pricing by number of assets", "Mid-sized companies first", "KPIs: monthly recurring revenue and churn"] },
                { title: "Cloud and DevOps services company", industry: "Professional services", score: 76,
                  points: ["Monthly retainers instead of one-off projects", "Partnerships with cloud providers", "Risk of depending on a few clients"] },
                { title: "Online store for natural care products", industry: "E-commerce", score: 68,
                  points: ["Own store plus online marketplaces", "Target LTV/CAC of 3 or more", "Risk of rising ad costs"] },
            ],
            cta: "Analyze your idea now",
        },

        contact: {
            title: "Contact us",
            lead: "A question, a suggestion or a partnership in mind? Send us a message and we'll get back to you soon.",
            name: "Name", email: "Email", subject: "Subject (optional)", message: "Your message",
            send: "Send message", sent: "Thank you! We received your message and will reply by email.",
            sideTitle: "How can we help?",
            side: ["Questions about plans and pricing", "Partnerships with incubators and universities", "Feedback and ideas to improve Mustashar"],
        },
    },
};

const pt = () => PAGE_TEXT[state.lang] || PAGE_TEXT.ar;

function pageHead(title, lead) {
    return el("div", { class: "page-head" }, el("h2", {}, title), lead ? el("p", { class: "lead" }, lead) : null);
}

function ctaButton(label) {
    return el("a", { class: "btn btn-primary", href: state.user ? "#/" : "#/register" }, label);
}

// ---------- About us ----------
function aboutPage() {
    const x = pt().about;
    return el("div", { class: "page" },
        pageHead(x.title, x.lead),
        el("section", { class: "panel mission" }, el("h3", {}, x.missionTitle), el("p", {}, x.mission)),
        el("h3", { class: "section-title" }, x.howTitle),
        el("div", { class: "grid grid-3" }, x.steps.map(([h, p], i) =>
            el("div", { class: "panel step-card" }, el("span", { class: "step-num" }, i + 1), el("h4", {}, h), el("p", {}, p)))),
        el("h3", { class: "section-title" }, x.valuesTitle),
        el("div", { class: "grid grid-2" }, x.values.map(([h, p]) =>
            el("div", { class: "panel value-card" }, el("h4", {}, h), el("p", {}, p)))),
        el("div", { class: "page-cta" }, ctaButton(x.cta)));
}

// ---------- Pricing ----------
const pricingState = { period: "monthly", currency: null };

function money(amount, currency) {
    if (currency === "usd") return `$${amount}`;
    return state.lang === "ar" ? `${amount} ر.س` : `SAR ${amount}`;
}

function planFeatures(p, x) {
    const f = p.features, l = p.limits;
    return [
        l.reports_per_month ? x.reports(l.reports_per_month) : null,
        x.chat(l.chat_per_report ?? null),
        x.tier[p.model_tier],
        f.templates ? x.templates : null,
        f.regenerate ? x.regenerate : null,
        f.watermark ? x.watermark : x.noWatermark,
        f.seats > 1 ? x.seats(f.seats) : null,
        f.branded_pdf ? x.branded : null,
    ].filter(Boolean);
}

function pricingPage() {
    const x = pt().pricing;
    const root = el("div", { class: "page" }, pageHead(x.title, x.lead), el("p", { class: "lead" }, "…"));
    api("/api/plans").then((catalog) => {
        root.replaceChildren(pageHead(x.title, x.lead));
        pricingState.currency ??= state.lang === "ar" ? "sar" : "usd";
        const render = () => {
            const cur = pricingState.currency, period = pricingState.period;
            const yearlySave = (p) => Math.round((1 - p.price.yearly[cur] / (p.price.monthly[cur] * 12)) * 100);
            const best = Math.max(...catalog.plans.filter((p) => p.price.monthly[cur] > 0).map(yearlySave));
            const toggle = (key, options) => el("div", { class: "seg" }, options.map(([val, label]) =>
                el("button", { class: `seg-btn${pricingState[key] === val ? " active" : ""}`, type: "button",
                    onclick: () => { pricingState[key] = val; render(); } }, label)));
            const current = state.plan?.plan;
            const cards = catalog.plans.map((p) => {
                const amount = p.price[period][cur];
                let button;
                if (state.user && current === p.key) button = el("button", { class: "btn btn-secondary", disabled: "" }, x.current);
                else if (amount === 0) button = state.user ? null : el("a", { class: "btn btn-secondary", href: "#/register" }, x.startFree);
                else button = el("button", { class: "btn btn-primary", disabled: "", title: x.paymentsSoon }, x.soon);
                return el("div", { class: `panel price-card${p.key === "pro" ? " featured" : ""}` },
                    p.key === "pro" ? el("span", { class: "badge-popular" }, x.popular) : null,
                    el("h3", {}, state.lang === "ar" ? p.name_ar : p.name_en),
                    el("div", { class: "price" },
                        el("span", { class: "amount" }, amount === 0 ? x.free : money(amount, cur)),
                        amount === 0 ? null : el("span", { class: "per" }, period === "monthly" ? x.perMonth : x.perYear)),
                    el("ul", { class: "checks" }, planFeatures(p, x).map((f) => el("li", {}, f))),
                    button);
            });
            const packs = catalog.packs.map((p) => el("div", { class: "panel pack-card" },
                el("h4", {}, x.credits(p.credits)), el("div", { class: "amount" }, money(p.price[cur], cur)),
                el("button", { class: "btn btn-secondary btn-sm", disabled: "", title: x.paymentsSoon }, x.soon)));
            root.replaceChildren(
                pageHead(x.title, x.lead),
                el("div", { class: "pricing-controls" },
                    toggle("period", [["monthly", x.monthly], ["yearly", `${x.yearly} · ${x.save(best)}`]]),
                    toggle("currency", [["sar", "SAR"], ["usd", "USD"]])),
                el("div", { class: "grid grid-4" }, cards),
                el("h3", { class: "section-title" }, x.packsTitle),
                el("p", { class: "lead center" }, x.packsLead),
                el("div", { class: "grid grid-packs" }, packs),
                el("p", { class: "field-hint center" }, x.paymentsSoon));
        };
        render();
    }).catch((err) => showAlert(err.message));
    return root;
}

// ---------- Portfolio ----------
function portfolioPage() {
    const x = pt().portfolio;
    return el("div", { class: "page" },
        pageHead(x.title, x.lead),
        el("div", { class: "grid grid-2" }, x.items.map((it) => {
            const color = it.score >= 70 ? "var(--green)" : it.score >= 45 ? "var(--amber)" : "var(--red)";
            const ring = el("div", { class: "mini-score" }, el("span", {}, it.score));
            ring.style.background = `conic-gradient(${color} ${it.score * 3.6}deg, var(--track) 0)`;
            return el("article", { class: "panel work-card" },
                el("div", { class: "work-head" },
                    el("div", {}, el("span", { class: "tag" }, it.industry), el("span", { class: "tag muted" }, x.example),
                        el("h4", {}, it.title)),
                    el("div", { class: "work-score", title: x.score }, ring)),
                el("ul", { class: "checks" }, it.points.map((p) => el("li", {}, p))));
        })),
        el("div", { class: "page-cta" }, ctaButton(x.cta)));
}

// ---------- Contact us ----------
function contactPage() {
    const x = pt().contact;
    const field = (id, label, attrs = {}, tag = "input") => el("div", {},
        el("label", { for: `c-${id}` }, label), el(tag, { id: `c-${id}`, ...attrs }));
    const form = el("form", { class: "panel contact-form" },
        field("name", x.name, { required: "", maxlength: "100", autocomplete: "name", value: state.user?.name || "" }),
        field("email", x.email, { required: "", type: "email", maxlength: "254", autocomplete: "email", value: state.user?.email || "" }),
        field("subject", x.subject, { maxlength: "150" }),
        field("message", x.message, { required: "", minlength: "10", maxlength: "4000" }, "textarea"),
        el("button", { class: "btn btn-primary", type: "submit" }, x.send));
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!form.reportValidity()) return;
        const btn = form.querySelector("button");
        btn.disabled = true;
        showAlert("");
        try {
            const body = Object.fromEntries(["name", "email", "subject", "message"].map((k) => [k, $(`c-${k}`).value]));
            await api("/api/contact", { method: "POST", body: JSON.stringify(body) });
            form.replaceChildren(el("p", { class: "lead" }, x.sent));
        } catch (err) {
            showAlert(err.message);
            btn.disabled = false;
        }
    });
    return el("div", { class: "page" },
        pageHead(x.title, x.lead),
        el("div", { class: "contact-grid" }, form,
            el("aside", { class: "panel contact-side" }, el("h3", {}, x.sideTitle),
                el("ul", { class: "checks" }, x.side.map((s) => el("li", {}, s))))));
}

const PUBLIC_PAGES = { about: aboutPage, pricing: pricingPage, portfolio: portfolioPage, contact: contactPage };
