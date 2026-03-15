// ======================================================
// STOCK LIST
// ======================================================

const stocks = [
    { symbol: "AAPL", name: "Apple Inc." },
    { symbol: "MSFT", name: "Microsoft Corporation" },
    { symbol: "TSLA", name: "Tesla Inc." },
    { symbol: "AMZN", name: "Amazon.com Inc." },
    { symbol: "GOOGL", name: "Alphabet Inc." },
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


// ======================================================
// GLOBAL VARIABLES
// ======================================================

let socket;
let select;

let priceChart = null;
let sentimentChart = null;
let riskTrendChart = null;


// ======================================================
// REVEAL ANIMATION ACTIVATION
// ======================================================

function activateReveal(){

    const elements = document.querySelectorAll(".reveal");

    elements.forEach(el=>{
        el.classList.add("active");
    });

}


// ======================================================
// DOM READY
// ======================================================

document.addEventListener("DOMContentLoaded", () => {

    console.log("STEP 0: DOM Loaded");

    activateReveal();
    initializeTheme();

    socket = io({
        transports: ["websocket","polling"]
    });

    select = document.getElementById("symbolSelect");

    console.log("STEP 1: Dropdown element:", select);

    initializeDropdown();
    socketEvents();

    loadDashboard();
    loadHeatmap();

    setInterval(loadDashboard,300000);

});


// ======================================================
// DROPDOWN INITIALIZATION
// ======================================================

function initializeDropdown(){

    console.log("STEP 2: Initializing dropdown");

    if(!select){
        console.log("ERROR: Dropdown not found");
        return;
    }

    select.innerHTML="";

    stocks.forEach(stock=>{

        const option=document.createElement("option");

        option.value=stock.symbol;
        option.textContent=`${stock.name} (${stock.symbol})`;

        select.appendChild(option);

    });

    select.value="AAPL";

    select.addEventListener("change",loadDashboard);

}


// ======================================================
// SOCKET EVENTS
// ======================================================

function socketEvents(){

    if(!socket){
        console.log("ERROR: Socket not initialized");
        return;
    }

    socket.on("connect",()=>{

        console.log("STEP 3: Connected to server:",socket.id);

        loadDashboard();

    });

    socket.on("dashboard_update",(data)=>{

        console.log("STEP 4: Dashboard update received");

        if(!data){
            console.log("ERROR: Dashboard data empty");
            return;
        }

        updateMetrics(data);
        updateAlertPanel(data.risk_score);
        updateNews(data.news);
        updateRiskDrivers(data.risk_drivers);

        renderCharts(data);

        updateHeatmapTile(data.symbol,data.risk_score);

    });

    socket.on("heatmap_update",(data)=>{

        console.log("STEP 7: Heatmap update received");

        if(!data) return;

        Object.keys(data).forEach(symbol=>{
            updateHeatmapTile(symbol,data[symbol]);
        });

    });

}


// ======================================================
// DASHBOARD REQUEST
// ======================================================

function loadDashboard(){

    if(!socket || !select) return;

    const symbol=select.value || "AAPL";

    console.log("Symbol requested:",symbol);

    socket.emit("request_dashboard",{symbol});

}


// ======================================================
// SAFE VALUE FORMATTER
// ======================================================

function safe(val,decimals=2){

    if(val===undefined || val===null || isNaN(val)) return "0.00";

    return Number(val).toFixed(decimals);

}


// ======================================================
// UPDATE METRICS
// ======================================================

function updateMetrics(data){

    const lstm=document.getElementById("lstmScore");
    const iso=document.getElementById("isoScore");
    const risk=document.getElementById("riskScore");

    if(lstm) lstm.innerText=safe(data.lstm_deviation*100)+"%";
    if(iso) iso.innerText=safe(data.anomaly_probability);
    if(risk) risk.innerText=safe(data.risk_score)+"/10";

    const alertLSTM=document.getElementById("alertLSTM");
    const alertISO=document.getElementById("alertISO");
    const alertSentiment=document.getElementById("alertSentiment");
    const volatility=document.getElementById("volatilityValue");

    if(alertLSTM) alertLSTM.innerText=safe(data.lstm_deviation*100)+"%";
    if(alertISO) alertISO.innerText=safe(data.anomaly_probability);
    if(alertSentiment) alertSentiment.innerText=safe(data.sentiment_score);
    if(volatility) volatility.innerText=safe(data.volatility)+"%";

}


// ======================================================
// ALERT PANEL
// ======================================================

function updateAlertPanel(risk){

    const panel=document.querySelector(".alert-panel");
    const alertText=document.getElementById("alertText");

    if(!panel) return;

    panel.classList.remove("alert-normal","alert-low","alert-high");

    if(risk < 4){
        if(alertText) alertText.innerText="🟢 NORMAL RISK";
        panel.classList.add("alert-normal");
    }
    else if(risk < 7){
        if(alertText) alertText.innerText="🟡 LOW RISK";
        panel.classList.add("alert-low");
    }
    else{
        if(alertText) alertText.innerText="🔴 HIGH RISK";
        panel.classList.add("alert-high");
    }

}


// ======================================================
// NEWS PANEL
// ======================================================

function updateNews(news){

    const list=document.getElementById("newsList");
    if(!list) return;

    list.innerHTML="";

    if(news && news.length>0){

        news.forEach(n=>{
            const li=document.createElement("li");
            li.innerText=n.title;
            list.appendChild(li);
        });

    }else{

        const li=document.createElement("li");
        li.innerHTML=`<div class="no-news">📰 No recent news available</div>`;
        list.appendChild(li);

    }

}

// ======================================================
// RISK DRIVERS
// ======================================================

function updateRiskDrivers(drivers){

if(!drivers) return;

const anomaly = drivers["Anomaly"] || 0;
const volatility = drivers["Volatility"] || 0;
const lstm = drivers["LSTM Dev"] || 0;
const sentiment = drivers["Sentiment"] || 0;

document.getElementById("driverAnomaly").innerText = anomaly.toFixed(2)+"%";
document.getElementById("driverVolatility").innerText = volatility.toFixed(2)+"%";
document.getElementById("driverLSTM").innerText = lstm.toFixed(2)+"%";
document.getElementById("driverSentiment").innerText = sentiment.toFixed(2)+"%";

document.getElementById("barAnomaly").style.width = anomaly+"%";
document.getElementById("barVolatility").style.width = volatility+"%";
document.getElementById("barLSTM").style.width = lstm+"%";
document.getElementById("barSentiment").style.width = sentiment+"%";

}


// ======================================================
// CHARTS
// ======================================================

function renderCharts(data){

    if(!data) return;

    // ================= PRICE CHART =================

    if(data.ohlc){

        const last=data.ohlc.slice(-10);

        const labels=last.map(d=>d.Date);
        const open=last.map(d=>Number(d.Open));
        const high=last.map(d=>Number(d.High));
        const low=last.map(d=>Number(d.Low));
        const close=last.map(d=>Number(d.Close));

        const canvas=document.getElementById("candleChart");

        if(canvas){

            const ctx=canvas.getContext("2d");

            if(!priceChart){

                priceChart=new Chart(ctx,{
                    type:"line",
                    data:{
                        labels:labels,
                        datasets:[
                            {label:"Open",data:open,borderColor:"#f59e0b"},
                            {label:"High",data:high,borderColor:"#16a34a"},
                            {label:"Low",data:low,borderColor:"#dc2626"},
                            {label:"Close",data:close,borderColor:"#2563eb"}
                        ]
                    },
                    options:{responsive:true,maintainAspectRatio:false}
                });

            }else{

                priceChart.data.labels=labels;
                priceChart.data.datasets[0].data=open;
                priceChart.data.datasets[1].data=high;
                priceChart.data.datasets[2].data=low;
                priceChart.data.datasets[3].data=close;
                priceChart.update();

            }

        }

    }

    // ================= SENTIMENT CHART =================


const sentimentCanvas = document.getElementById("sentimentChart");

if(sentimentCanvas){

    const pos = data.sentiment_distribution?.positive || 0;
    const neu = data.sentiment_distribution?.neutral || 0;
    const neg = data.sentiment_distribution?.negative || 0;

    const ctx = sentimentCanvas.getContext("2d");

    if(!sentimentChart){

        sentimentChart = new Chart(ctx,{
            type:"bar",
            data:{
                labels:["Positive","Neutral","Negative"],
                datasets:[{
                    label:"Sentiment %",
                    data:[pos, neu, neg],
                    backgroundColor:[
                        "#16a34a",
                        "#f59e0b",
                        "#dc2626"
                    ],
                    borderRadius:6,
                    barThickness:80
                }]
            },
            options:{
                responsive:true,
                maintainAspectRatio:false,

                interaction:{
                    mode:"index",
                    intersect:false
                },

                plugins:{
                    tooltip:{
                        enabled:true
                    }
                },

                scales:{
                    y:{
                        beginAtZero:true,
                        max:100
                    }
                }
            }
        });

    }else{

        sentimentChart.data.datasets[0].data=[pos,neu,neg];
        sentimentChart.update();

    }
}

    // ================= RISK TREND =================

    const riskCanvas=document.getElementById("riskTrendChart");

    if(riskCanvas){

        const ctx=riskCanvas.getContext("2d");

        const riskValues=data.risk_history || [data.risk_score];

        const labels=riskValues.map((_,i)=>`T-${riskValues.length-i}`);

        if(!riskTrendChart){

            riskTrendChart=new Chart(ctx,{
                type:"line",
                data:{
                    labels:labels,
                    datasets:[{
                        label:"Risk Score",
                        data:riskValues,
                        borderColor:"#4e10d4",
                        tension:0.3
                    }]
                },
                options:{
                    scales:{
                        y:{beginAtZero:true,max:10}
                    }
                }
            });

        }else{

            riskTrendChart.data.labels=labels;
            riskTrendChart.data.datasets[0].data=riskValues;
            riskTrendChart.update();

        }

    }

}


// ======================================================
// HEATMAP LOAD
// ======================================================

async function loadHeatmap(){

    const container=document.getElementById("heatmapScroll");
    if(!container) return;

    const res=await fetch("/api/heatmap");
    const data=await res.json();

    let html="";

    data.forEach(item=>{

        let color="heat-green";
        if(item.risk_score>=7) color="heat-red";
        else if(item.risk_score>=4) color="heat-orange";

        html+=`
        <div class="heat-tile ${color}" data-symbol="${item.symbol}">
        ${item.symbol}<br>
        ${item.risk_score.toFixed(2)}
        </div>
        `;

    });

    container.innerHTML=html+html;

}


// ======================================================
// HEATMAP UPDATE
// ======================================================

function updateHeatmapTile(symbol,risk){

    const tiles=document.querySelectorAll(".heat-tile");

    tiles.forEach(tile=>{

        if(tile.dataset.symbol===symbol){

            tile.innerHTML=`${symbol}<br>${risk.toFixed(2)}`;

            tile.classList.remove("heat-green","heat-orange","heat-red");

            if(risk>=7) tile.classList.add("heat-red");
            else if(risk>=4) tile.classList.add("heat-orange");
            else tile.classList.add("heat-green");

        }

    });

}


// ======================================================
// DARK THEME TOGGLE
// ======================================================

function initializeTheme(){

    const toggle = document.getElementById("themeToggle");

    if(!toggle) return;

    const savedTheme = localStorage.getItem("theme");

    if(savedTheme === "dark"){
        document.body.classList.add("dark-theme");
        toggle.checked = true;
    }

    toggle.addEventListener("change", ()=>{

        document.body.classList.toggle("dark-theme");

        if(document.body.classList.contains("dark-theme")){
            localStorage.setItem("theme","dark");
        }else{
            localStorage.setItem("theme","light");
        }

    });

}