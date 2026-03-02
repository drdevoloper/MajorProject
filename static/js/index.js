// ============================
// STOCK LIST
// ============================

const stocks = [
    { symbol: "AAPL", name: "Apple Inc." },
    { symbol: "MSFT", name: "Microsoft Corporation" },
    { symbol: "TSLA", name: "Tesla Inc." },
    { symbol: "AMZN", name: "Amazon.com Inc." },
    { symbol: "GOOGL", name: "Alphabet Inc. (Google)" },
    { symbol: "META", name: "Meta Platforms Inc." },
    { symbol: "NVDA", name: "NVIDIA Corporation" },
    { symbol: "IBM", name: "IBM Corporation" },
    { symbol: "TCS.NS", name: "Tata Consultancy Services Ltd." },
    { symbol: "INFY.NS", name: "Infosys Ltd." },
    { symbol: "HDFCBANK.NS", name: "HDFC Bank Ltd." },
    { symbol: "ICICIBANK.NS", name: "ICICI Bank Ltd." },
    { symbol: "SBIN.NS", name: "State Bank of India" },
    { symbol: "LT.NS", name: "Larsen & Toubro Ltd." },
    { symbol: "WIPRO.NS", name: "Wipro Ltd." },
    { symbol: "ONGC.NS", name: "Oil & Natural Gas Corporation" }
];

const socket = io();
const select = document.getElementById("symbolSelect");

stocks.forEach(stock => {
    const opt = document.createElement("option");
    opt.value = stock.symbol;
    opt.textContent = `${stock.name} (${stock.symbol})`;
    select.appendChild(opt);
});

// ============================
// GLOBAL CHARTS
// ============================

let priceChart = null;
let sentimentChart = null;
let riskTrendChart = null;

// ============================
// REQUEST DASHBOARD
// ============================

function loadDashboard() {
    const symbol = select.value;
    socket.emit("request_dashboard", { symbol });
}

// ============================
// SOCKET RESPONSE
// ============================

socket.on("dashboard_update", function(data) {

    if (!data) return;

    const safe = (val, decimals = 2) =>
        (val !== undefined && val !== null)
            ? Number(val).toFixed(decimals)
            : "0.00";

    // ================= METRICS =================

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

    updateAlertPanel(data.risk_score);
    updateNews(data.news);
    renderCharts(data);
    loadHeatmap();
});

// ============================
// ALERT PANEL
// ============================

function updateAlertPanel(risk) {

    const alertPanel = document.querySelector(".alert-panel");
    alertPanel.classList.remove("alert-normal","alert-low","alert-high");

    if (risk < 4) {
        document.getElementById("alertText").innerText = "🟢 NORMAL RISK";
        alertPanel.classList.add("alert-normal");
    }
    else if (risk < 7) {
        document.getElementById("alertText").innerText = "🟡 LOW RISK";
        alertPanel.classList.add("alert-low");
    }
    else {
        document.getElementById("alertText").innerText = "🔴 HIGH RISK";
        alertPanel.classList.add("alert-high");
    }
}

// ============================
// NEWS
// ============================

function updateNews(news) {

    const newsList = document.getElementById("newsList");
    newsList.innerHTML = "";

    if (news && news.length > 0) {

        news.forEach(n => {
            const li = document.createElement("li");
            li.innerText = n.title;
            newsList.appendChild(li);
        });

    } else {

        const li = document.createElement("li");
        li.innerHTML =
            `<div class="no-news">📰 No recent news available</div>`;
        newsList.appendChild(li);
    }
}

// ============================
// CHART RENDERING
// ============================

function renderCharts(data) {

    // ================= PRICE =================

    if (data.ohlc && data.ohlc.length >= 6) {

        const last6 = data.ohlc.slice(-6);
        const labels = last6.map(d => d.Date);
        const close = last6.map(d => Number(d.Close));

        const ctx = document.getElementById("candleChart");

        if (!priceChart) {

            priceChart = new Chart(ctx, {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [{
                        data: close,
                        borderColor: "#2563eb",
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });

        } else {

            priceChart.data.labels = labels;
            priceChart.data.datasets[0].data = close;
            priceChart.update();
        }
    }

    // ================= SENTIMENT =================

    if (data.news && data.news.length > 0) {

        let positive = 0, neutral = 0, negative = 0;

        data.news.forEach(n => {
            if (n.sentiment > 0.6) positive++;
            else if (n.sentiment > 0.4) neutral++;
            else negative++;
        });

        const ctx = document.getElementById("sentimentChart");

        if (!sentimentChart) {

            sentimentChart = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: ["Positive","Neutral","Negative"],
                    datasets: [{
                        data: [positive, neutral, negative],
                        backgroundColor: ["#16a34a","#f59e0b","#dc2626"],
                        barThickness: 30
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });

        } else {

            sentimentChart.data.datasets[0].data =
                [positive, neutral, negative];

            sentimentChart.update();
        }
    }

    // ================= RISK TREND =================

    if (data.risk_history && data.risk_history.length > 0) {

        const values = data.risk_history.slice(-10);
        const ctx = document.getElementById("riskTrendChart");

        if (!riskTrendChart) {

            riskTrendChart = new Chart(ctx, {
                type: "line",
                data: {
                    labels: values.map((_, i) => i + 1),
                    datasets: [{
                        data: values,
                        borderColor: "#7c3aed",
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });

        } else {

            riskTrendChart.data.labels =
                values.map((_, i) => i + 1);

            riskTrendChart.data.datasets[0].data = values;

            riskTrendChart.update();
        }
    }

    updateChartThemeColors();
}

// ============================
// HEATMAP
// ============================

async function loadHeatmap() {

    const container = document.getElementById("heatmapScroll");
    if (!container) return;

    try {
        const res = await fetch("/api/heatmap");
        const data = await res.json();

        let html = "";

        data.forEach(item => {

            let color = "heat-green";
            if (item.risk_score >= 7) color = "heat-red";
            else if (item.risk_score >= 4) color = "heat-orange";

            html += `
                <div class="heat-tile ${color}">
                    ${item.symbol}<br>
                    ${item.risk_score.toFixed(2)}
                </div>
            `;
        });

        container.innerHTML = html + html;

    } catch (err) {
        console.error("Heatmap error:", err);
    }
}

// ============================
// INIT
// ============================

document.addEventListener("DOMContentLoaded", () => {

    select.addEventListener("change", loadDashboard);

    loadDashboard();
    loadHeatmap();

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