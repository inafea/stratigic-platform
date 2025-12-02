// Configuration
const CONFIG = {
    API_ENDPOINT: 'https://models.inference.ai.azure.com/chat/completions',
    MODEL: 'gpt-4.1-mini',  // GitHub Models format
    API_KEY: '', // Set via environment variable: GITHUB_TOKEN
    MAX_TOKENS: 2000
};

// Get DOM elements
const form = document.getElementById('analyzerForm');
const businessIdeaInput = document.getElementById('businessIdea');
const businessGoalsInput = document.getElementById('businessGoals');
const loadingDiv = document.getElementById('loading');
const resultsDiv = document.getElementById('results');
const resultContent = document.getElementById('resultContent');
const errorDiv = document.getElementById('error');

// Form submission handler
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const businessIdea = businessIdeaInput.value.trim();
    const businessGoals = businessGoalsInput.value.trim();

    if (!businessIdea || !businessGoals) {
        showError('يرجى ملء جميع الحقول المطلوبة');
        return;
    }

    await analyzeBusinessStrategy(businessIdea, businessGoals);
});

/**
 * Analyze business strategy using AI
 */
async function analyzeBusinessStrategy(businessIdea, businessGoals) {
    try {
        clearError();
        showLoading(true);
        resultsDiv.classList.remove('active');

        // Prepare the prompt for AI analysis
        const prompt = buildPrompt(businessIdea, businessGoals);

        // Call the AI model with configured token
        const analysis = await callAIModel(prompt);

        // Display results
        displayResults(analysis);
        showLoading(false);
        resultsDiv.classList.add('active');

    } catch (error) {
        showLoading(false);
        showError(error.message);
        console.error('Analysis error:', error);
    }
}

/**
 * Build the prompt for AI analysis
 */
function buildPrompt(businessIdea, businessGoals) {
    return `أنت استشاري استراتيجية أعمال متخصص. يرجى تحليل المعلومات التجارية التالية وتقديم تحليل استراتيجي شامل.

فكرة العمل التجارية:
${businessIdea}

أهداف العمل التجارية:
${businessGoals}

يرجى تقديم تحليل استراتيجي مفصل يتضمن:

1. **تحليل فرص السوق**
   - حجم السوق المحتمل
   - مشهد المنافسة
   - الميزة القيمية الفريدة

2. **التوصيات الاستراتيجية**
   - عوامل النجاح الرئيسية
   - المخاطر المحتملة واستراتيجيات التخفيف
   - فرص النمو

3. **خطة التنفيذ**
   - أولويات المرحلة الأولى (أول 3-6 أشهر)
   - الإنجازات الرئيسية
   - الموارد المطلوبة

4. **الاعتبارات المالية**
   - احتياجات الاستثمار المقدرة
   - نموذج الإيرادات المحتمل
   - الجدول الزمني لتحقيق نقطة التعادل

5. **الخطوات التالية**
   - الإجراءات الفورية المراد اتخاذها
   - مؤشرات النجاح المراد تتبعها

يرجى تنظيم الإجابة بأقسام واضحة وتقديم رؤى قابلة للتطبيق.`;
}

/**
 * Call the AI model using GitHub Models API
 */
async function callAIModel(prompt) {
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${CONFIG.API_KEY}`
    };

    const requestBody = {
        messages: [
            {
                role: 'user',
                content: prompt
            }
        ],
        model: CONFIG.MODEL,
        temperature: 0.7,
        max_tokens: CONFIG.MAX_TOKENS,
        top_p: 0.9
    };

    try {
        const response = await fetch(CONFIG.API_ENDPOINT, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            let errorMessage = `API Error: ${response.status}`;
            
            try {
                const errorData = await response.json();
                errorMessage = errorData.error?.message || errorData.message || errorMessage;
            } catch (e) {
                // Use default error message
            }

            throw new Error(errorMessage);
        }

        const data = await response.json();
        
        if (data.choices && data.choices.length > 0) {
            return data.choices[0].message.content;
        } else {
            throw new Error('No response from AI model');
        }

    } catch (error) {
        if (error.message.includes('401') || error.message.includes('Unauthorized')) {
            throw new Error('مفتاح API غير صحيح. يرجى التحقق من رمزك.');
        } else if (error.message.includes('429')) {
            throw new Error('تم تجاوز حد المعدل. يرجى المحاولة مرة أخرى لاحقاً.');
        } else if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
            throw new Error('خطأ في الاتصال بالشبكة. يرجى التحقق من اتصالك بالإنترنت.');
        }
        throw error;
    }
}

/**
 * Display the AI analysis results
 */
function displayResults(analysis) {
    // Convert markdown-like formatting to HTML
    const htmlContent = formatAnalysis(analysis);
    resultContent.innerHTML = htmlContent;
}

/**
 * Format the analysis text to HTML
 */
function formatAnalysis(text) {
    let html = text;

    // Replace bold headers (e.g., **Header**)
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Replace markdown headers (e.g., # Header)
    html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');

    // Replace line breaks with paragraphs
    html = html.split('\n\n').map(para => {
        // Don't wrap headers in paragraphs
        if (para.match(/^<[hH][1-3]>/)) {
            return para;
        }
        // Handle bullet points
        if (para.trim().startsWith('- ') || para.trim().startsWith('* ')) {
            const items = para.split('\n').filter(line => line.trim());
            const listHtml = items.map(item => `<li>${item.replace(/^[-*]\s/, '')}</li>`).join('');
            return `<ul>${listHtml}</ul>`;
        }
        return `<p>${para}</p>`;
    }).join('');

    // Replace numbered lists
    html = html.replace(/^\d+\.\s/gm, '<li>');

    return html;
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    if (show) {
        loadingDiv.classList.add('active');
    } else {
        loadingDiv.classList.remove('active');
    }
}

/**
 * Display error message
 */
function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.add('active');
}

/**
 * Clear error message
 */
function clearError() {
    errorDiv.textContent = '';
    errorDiv.classList.remove('active');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Business Strategy Analyzer initialized');
    console.log('Using AI Model:', CONFIG.MODEL);
    console.log('API Endpoint:', CONFIG.API_ENDPOINT);
});
