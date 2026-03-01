// ============================
// SYMBOLS
// ============================
// ============================
// STOCK LIST (WITH FULL NAMES)
// ============================
const stocks = [

    // 🇺🇸 US Stocks
    { symbol: "AAPL", name: "Apple Inc." },
    { symbol: "MSFT", name: "Microsoft Corporation" },
    { symbol: "TSLA", name: "Tesla Inc." },
    { symbol: "AMZN", name: "Amazon.com Inc." },
    { symbol: "GOOGL", name: "Alphabet Inc. (Google)" },
    { symbol: "META", name: "Meta Platforms Inc." },
    { symbol: "NVDA", name: "NVIDIA Corporation" },
    { symbol: "IBM", name: "IBM Corporation" },

    // 🇮🇳 Indian NSE Stocks
    { symbol: "TCS.NS", name: "Tata Consultancy Services Ltd." },
    { symbol: "INFY.NS", name: "Infosys Ltd." },
    { symbol: "HDFCBANK.NS", name: "HDFC Bank Ltd." },
    { symbol: "ICICIBANK.NS", name: "ICICI Bank Ltd." },
    { symbol: "SBIN.NS", name: "State Bank of India" },
    { symbol: "LT.NS", name: "Larsen & Toubro Ltd." },
    { symbol: "WIPRO.NS", name: "Wipro Ltd." },
    { symbol: "ONGC.NS", name: "Oil & Natural Gas Corporation" }
];

const select = document.getElementById("symbolSelect");

stocks.forEach(stock => {
    const opt = document.createElement("option");
    opt.value = stock.symbol;  // API uses symbol
    opt.textContent = `${stock.name} (${stock.symbol})`; // Display full name
    select.appendChild(opt);
});

// ============================
// GLOBAL CHARTS
// ============================
let priceChart = null;
let sentimentChart = null;
let riskTrendChart = null;

// ============================
// HEATMAP LOADER (AUTO SCROLL)
// ============================
// ============================
// HEATMAP LOADER (FAST)
// ============================
async function loadHeatmap() {

    const container = document.getElementById("heatmapScroll");
    if (!container) return;

    // 🔥 Show instant skeleton placeholders
    container.innerHTML = stocks.map(s => `
        <div class="heat-tile heat-green">
            ${s.symbol}<br>
            ...
        </div>
    `).join("");

    try {

        const res = await fetch("/api/heatmap");
        const data = await res.json();

        let tilesHTML = "";

        data.forEach(item => {

            let colorClass = "heat-green";

            if (item.risk_score < 4)
                colorClass = "heat-green";
            else if (item.risk_score < 7)
                colorClass = "heat-orange";
            else
                colorClass = "heat-red";

            tilesHTML += `
                <div class="heat-tile ${colorClass}">
                    ${item.symbol}<br>
                    ${item.risk_score.toFixed(2)}
                </div>
            `;
        });

        container.innerHTML = tilesHTML + tilesHTML;

    } catch (err) {
        console.error("Heatmap load error:", err);
    }
}

// ============================
// MAIN DASHBOARD LOADER
// ============================
async function loadDashboard() {

    try {

        const symbol = select.value;
        const priceTitle = document.getElementById("priceTitle");

        if (priceTitle) {
            priceTitle.innerText = symbol + " - Last 6 Days Price Movement";
        }

        const res = await fetch(`/api/dashboard?symbol=${symbol}`);
        const data = await res.json();

        if (data.error) return;

        const safe = (val, decimals = 2) =>
            (val !== undefined && val !== null)
                ? Number(val).toFixed(decimals)
                : "0.00";

                

        // ============================
        // METRICS
        // ============================
        document.getElementById("lstmScore").innerText =
            safe(data.lstm_deviation * 100) + "%";

        document.getElementById("isoScore").innerText =
            safe(data.anomaly_probability);

        document.getElementById("riskScore").innerText =
            safe(data.risk_score) + "/10";

        document.getElementById("alertLSTM").innerText =
            safe(data.lstm_deviation * 100) + "%";

        document.getElementById("alertISO").innerText =
            safe(data.anomaly_probability);

        document.getElementById("alertSentiment").innerText =
            safe(data.sentiment_score);

        // ============================
        // ALERT STATUS
        // ============================
        const alertPanel = document.querySelector(".alert-panel");
        alertPanel.classList.remove("alert-normal","alert-low","alert-high");

        if (data.risk_score < 4) {
            document.getElementById("alertText").innerText = "🟢 NORMAL RISK";
            alertPanel.classList.add("alert-normal");
        }
        else if (data.risk_score < 7) {
            document.getElementById("alertText").innerText = "🟡 LOW RISK";
            alertPanel.classList.add("alert-low");
        }
        else {
            document.getElementById("alertText").innerText = "🔴 HIGH RISK";
            alertPanel.classList.add("alert-high");
        }

        // ============================
        // NEWS
        // ============================
        const newsList = document.getElementById("newsList");
        newsList.innerHTML = "";

        if (data.news && data.news.length > 0) {

            data.news.forEach(n => {
                const li = document.createElement("li");
                li.innerText = n.title + " (" + safe(n.sentiment) + ")";
                newsList.appendChild(li);
            });

        } else {

            const li = document.createElement("li");
            li.innerHTML = `
                <div class="no-news">
                    📰 No recent news available for this stock
                </div>
            `;
            newsList.appendChild(li);
        }

        // ============================
        // 6 DAY OHLC LINE GRAPH
        // ============================
        if (data.ohlc && data.ohlc.length >= 6) {

            const last6 = data.ohlc.slice(-6);

            const labels = last6.map(d => d.Date);
            const openPrices  = last6.map(d => Number(d.Open));
            const highPrices  = last6.map(d => Number(d.High));
            const lowPrices   = last6.map(d => Number(d.Low));
            const closePrices = last6.map(d => Number(d.Close));

            const ctx = document.getElementById("candleChart");

            if (priceChart) {
                priceChart.destroy();
                priceChart = null;
            }

            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: "Open",
                            data: openPrices,
                            borderColor: "#2563eb",
                            tension: 0.3
                        },
                        {
                            label: "High",
                            data: highPrices,
                            borderColor: "#16a34a",
                            tension: 0.3
                        },
                        {
                            label: "Low",
                            data: lowPrices,
                            borderColor: "#dc2626",
                            tension: 0.3
                        },
                        {
                            label: "Close",
                            data: closePrices,
                            borderColor: "#f97316",
                            tension: 0.3,
                            borderWidth: 3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });

            // ============================
            // VOLATILITY CALCULATION
            // ============================
            const highs = last6.map(d => d.High);
            const lows = last6.map(d => d.Low);

            const volatility =
                ((Math.max(...highs) - Math.min(...lows)) /
                 Math.min(...lows)) * 100;

            const volBox = document.getElementById("volatilityIndicator");
            if (volBox) {
                volBox.innerText =
                    "Volatility (6D Range): " + volatility.toFixed(2) + "%";
            }
        }

        // ============================
        // SENTIMENT CHART
        // ============================
        
        // ============================
// SENTIMENT DISTRIBUTION GRAPH WITH %
// ============================

if (data.news && data.news.length > 0) {

    const ctx = document.getElementById("sentimentChart");

    if (sentimentChart) {
        sentimentChart.destroy();
        sentimentChart = null;
    }

    let positive = 0;
    let neutral = 0;
    let negative = 0;

    data.news.forEach(n => {
        const score = n.sentiment || 0;

        if (score > 0.6) positive++;
        else if (score > 0.4) neutral++;
        else negative++;
    });

    const total = positive + neutral + negative;

    const positivePct = ((positive / total) * 100).toFixed(1);
    const neutralPct  = ((neutral / total) * 100).toFixed(1);
    const negativePct = ((negative / total) * 100).toFixed(1);

    sentimentChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ["Positive", "Neutral", "Negative"],
            datasets: [{
                data: [positive, neutral, negative],
                backgroundColor: [
                    "#16a34a",
                    "#f59e0b",
                    "#dc2626"
                ],
                barThickness: 35,
                categoryPercentage: 0.5,
                barPercentage: 0.6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const percentages = [
                                positivePct,
                                neutralPct,
                                negativePct
                            ];
                            return percentages[context.dataIndex] + "%";
                        }
                    }
                }
            }
        }
    });

}

        // ============================
        // RISK TREND
        // ============================
        if (data.risk_history && data.risk_history.length > 0) {

    const ctx = document.getElementById("riskTrendChart");

    if (riskTrendChart) {
        riskTrendChart.destroy();
        riskTrendChart = null;
    }

    // Take only last 10 values
    const values = data.risk_history.slice(-10);

    riskTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array.from({ length: values.length }, (_, i) => i + 1),
            datasets: [{
                label: "Risk Trend",
                data: values,
                borderColor: "#2563eb",
                backgroundColor: "rgba(37,99,235,0.1)",
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
    min: 0,
    max: 5,
    ticks: {
        stepSize: 1   
    },
    title: {
        display: true,
        text: "Risk Score (0 – 10)"
    }
},
                x: {
                    title: {
                        display: true,
                        text: "Last 10 Risk Evaluations"
                    }
                }
            }
        }
    });
}

        // ============================
        // LOAD HEATMAP LAST
        // ============================
        await loadHeatmap();

        updateChartThemeColors();

    } catch (err) {
        console.error("Dashboard Error:", err);
    }
}


// ============================
// EVENTS
// ============================
document.addEventListener("DOMContentLoaded", () => {

    select.addEventListener("change", loadDashboard);

    Promise.all([
        loadDashboard(),
        loadHeatmap()
    ]);  // Force first render

    updateChartThemeColors();

    // Refresh every 10 minutes
    setInterval(() => {
        loadDashboard();
        loadHeatmap();
    }, 600000);

});

// ================= DARK THEME SCRIPT =================

document.addEventListener("DOMContentLoaded", () => {

    const toggle = document.getElementById("themeToggle");

    if (!toggle) return;

    const savedTheme = localStorage.getItem("theme");

    // Auto detect system dark mode
    if (savedTheme === "dark" ||
       (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.body.classList.add("dark-theme");
        toggle.checked = true;
    }

    toggle.addEventListener("change", () => {

        if (toggle.checked) {
            document.body.classList.add("dark-theme");
            localStorage.setItem("theme", "dark");
        } else {
            document.body.classList.remove("dark-theme");
            localStorage.setItem("theme", "light");
        }

        updateChartThemeColors();
    });

});

// Auto update chart axis colors
function updateChartThemeColors() {

    const isDark = document.body.classList.contains("dark-theme");

    const axisColor = isDark ? "#e5e7eb" : "#111827";
    const gridColor = isDark 
        ? "rgba(255,255,255,0.15)"   // 🔥 visible soft grid in dark
        : "rgba(0,0,0,0.08)";        // subtle grid in light

    const applyTheme = (chart) => {
        if (!chart) return;

        if (chart.options.scales) {

            if (chart.options.scales.x) {
                chart.options.scales.x.ticks = { color: axisColor };
                chart.options.scales.x.grid = {
                    color: gridColor,
                    borderColor: gridColor
                };
            }

            if (chart.options.scales.y) {
                chart.options.scales.y.ticks = { color: axisColor };
                chart.options.scales.y.grid = {
                    color: gridColor,
                    borderColor: gridColor
                };
            }
        }

        chart.update();
    };

    applyTheme(priceChart);
    applyTheme(sentimentChart);
    applyTheme(riskTrendChart);
}

/* ================= PANEL REVEAL SCRIPT ================= */

const reveals = document.querySelectorAll(".reveal");

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add("active");
        }
    });
}, {
    threshold: 0.15
});

reveals.forEach(el => observer.observe(el));