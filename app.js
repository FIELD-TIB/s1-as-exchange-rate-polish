const rateValue = document.querySelector("#rate-value");
const lastUpdated = document.querySelector("#last-updated");
const pollState = document.querySelector("#poll-state");
const nextPoll = document.querySelector("#next-poll");
const sampleCount = document.querySelector("#sample-count");
const rateRows = document.querySelector("#rate-rows");
const chart = document.querySelector("#rate-chart");
const chartEmpty = document.querySelector("#chart-empty");
let currentSamples = [];

function formatLocalTime(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-KE", {
    timeZone: "Africa/Nairobi",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function renderHistory(samples) {
  currentSamples = samples;
  sampleCount.textContent = `${samples.length} sample${samples.length === 1 ? "" : "s"}`;
  if (!samples.length) {
    rateRows.innerHTML = '<tr><td colspan="3" class="empty-row">No samples saved yet. The app collects rates between 06:00 and 18:00 EAT.</td></tr>';
    chartEmpty.hidden = false;
    drawChart([]);
    return;
  }

  rateRows.replaceChildren();
  [...samples].reverse().forEach((sample) => {
    const row = document.createElement("tr");
    [
      formatLocalTime(sample.fetched_at),
      Number(sample.rate).toFixed(4),
      sample.provider_updated_at || "Not supplied",
    ].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });
    rateRows.append(row);
  });
  chartEmpty.hidden = true;
  drawChart(samples);
}

function drawChart(samples) {
  const context = chart.getContext("2d");
  const width = chart.clientWidth;
  const height = chart.clientHeight;
  const pixelRatio = window.devicePixelRatio || 1;
  chart.width = width * pixelRatio;
  chart.height = height * pixelRatio;
  context.scale(pixelRatio, pixelRatio);
  context.clearRect(0, 0, width, height);
  if (!samples.length || width < 1 || height < 1) return;

  const values = samples.map((sample) => Number(sample.rate));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || max * 0.002 || 1;
  const padding = { top: 16, right: 5, bottom: 19, left: 5 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const points = values.map((value, index) => ({
    x: padding.left + (values.length === 1 ? plotWidth / 2 : index * plotWidth / (values.length - 1)),
    y: padding.top + (max - value + spread * 0.08) / (spread * 1.16) * plotHeight,
  }));

  context.strokeStyle = "#edf1ed";
  context.lineWidth = 1;
  for (let row = 0; row < 3; row += 1) {
    const y = padding.top + (plotHeight * row) / 2;
    context.beginPath();
    context.moveTo(padding.left, y);
    context.lineTo(width - padding.right, y);
    context.stroke();
  }

  const fill = context.createLinearGradient(0, padding.top, 0, height);
  fill.addColorStop(0, "rgba(45, 148, 104, .18)");
  fill.addColorStop(1, "rgba(45, 148, 104, 0)");
  context.beginPath();
  context.moveTo(points[0].x, height - padding.bottom);
  points.forEach((point) => context.lineTo(point.x, point.y));
  context.lineTo(points[points.length - 1].x, height - padding.bottom);
  context.closePath();
  context.fillStyle = fill;
  context.fill();

  context.beginPath();
  points.forEach((point, index) => {
    if (index === 0) context.moveTo(point.x, point.y);
    else context.lineTo(point.x, point.y);
  });
  context.strokeStyle = "#2d9468";
  context.lineWidth = 2;
  context.lineJoin = "round";
  context.lineCap = "round";
  context.stroke();

  const finalPoint = points[points.length - 1];
  context.beginPath();
  context.arc(finalPoint.x, finalPoint.y, 3.5, 0, Math.PI * 2);
  context.fillStyle = "#fff";
  context.fill();
  context.strokeStyle = "#2d9468";
  context.lineWidth = 2;
  context.stroke();
}

async function refresh() {
  try {
    const [statusResponse, ratesResponse] = await Promise.all([
      fetch("/api/status", { cache: "no-store" }),
      fetch("/api/rates?limit=100", { cache: "no-store" }),
    ]);
    if (!statusResponse.ok || !ratesResponse.ok) throw new Error("The local server returned an error.");
    const status = await statusResponse.json();
    const history = await ratesResponse.json();
    const { poller, latest } = status;

    if (latest) {
      rateValue.textContent = Number(latest.rate).toFixed(4);
      lastUpdated.textContent = `Saved ${formatLocalTime(latest.fetched_at)}`;
    } else {
      rateValue.textContent = "—";
      lastUpdated.textContent = poller.last_error
        ? `Could not fetch a rate: ${poller.last_error}`
        : "Waiting for the first rate sample…";
    }

    pollState.textContent = poller.last_error
      ? "Update issue"
      : poller.in_polling_window ? "Polling active" : "Outside hours";
    if (poller.last_error) pollState.title = poller.last_error;
    nextPoll.textContent = poller.next_poll
      ? `Next check ${formatLocalTime(poller.next_poll)} · every 10 minutes`
      : "Polling window: 06:00–18:00 EAT · every 10 minutes";
    renderHistory(history.rates);
  } catch (error) {
    pollState.textContent = "Server unavailable";
    pollState.title = error.message;
    lastUpdated.textContent = "Unable to load local rate data.";
  }
}

refresh();
window.setInterval(refresh, 30_000);
window.addEventListener("resize", () => drawChart(currentSamples));
