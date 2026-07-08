// dashboard.js
// Mengambil data dari /api/dashboard-data setiap POLL_INTERVAL_MS
// lalu memperbarui kartu, grafik, tabel klasifikasi, dan notifikasi.

const POLL_INTERVAL_MS = 5000;

let lineChart = null;
let donutChart = null;

// Configure global Chart.js font
if (typeof Chart !== 'undefined') {
  Chart.defaults.font.family = "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
  Chart.defaults.color = "#64748b";
}

function badgeClassFromStatus(status) {
  if (status === "Penuh") return "badge-penuh";
  if (status === "Sedang") return "badge-sedang";
  return "badge-aman";
}

function jenisTagClass(jenis) {
  const j = (jenis || "").toLowerCase();
  if (j === "organik") return "jenis-organik";
  if (j === "anorganik") return "jenis-anorganik";
  return "jenis-residu";
}

function updateCards(kapasitas) {
  const map = [
    ["organik", "val-organik", "status-organik", "bar-organik", "pct-organik", "rt-organik", "rt-status-organik"],
    ["anorganik", "val-anorganik", "status-anorganik", "bar-anorganik", "pct-anorganik", "rt-anorganik", "rt-status-anorganik"],
    ["residu", "val-residu", "status-residu", "bar-residu", "pct-residu", "rt-residu", "rt-status-residu"],
  ];

  map.forEach(([key, valId, statusId, barId, pctId, rtValId, rtStatusId]) => {
    const data = kapasitas[key];
    document.getElementById(valId).textContent = data.persen + "%";
    document.getElementById(rtValId).textContent = data.persen + "%";
    document.getElementById(pctId).textContent = data.persen + "%";

    // Text status class modification
    const statusEl = document.getElementById(statusId);
    statusEl.textContent = data.status;
    statusEl.className = "status-label " + (key === "organik" ? "text-green" : key === "anorganik" ? "text-blue" : "text-gray");

    // Realtime badge status
    const rtStatusEl = document.getElementById(rtStatusId);
    rtStatusEl.textContent = data.status;
    rtStatusEl.className = "badge-status " + badgeClassFromStatus(data.status);

    document.getElementById(barId).style.width = data.persen + "%";
  });

  // Update Rata-rata
  document.getElementById("val-rata2").textContent = kapasitas.rata2.persen + "%";
  document.getElementById("status-rata2").textContent = kapasitas.rata2.status;
  document.getElementById("val-rata2-donut").textContent = kapasitas.rata2.persen + "%";

  updateDonut(kapasitas.rata2.persen);
  updateAlert(kapasitas);
}

function updateAlert(kapasitas) {
  const box = document.getElementById("alert-box");
  const text = document.getElementById("alert-text");
  const penuh = Object.entries(kapasitas).find(
    ([key, val]) => key !== "rata2" && (val.status === "Penuh" || val.status === "Sedang")
  );
  if (penuh && penuh[1].persen >= 70) {
    box.style.display = "block";
    const nama = penuh[0].charAt(0).toUpperCase() + penuh[0].slice(1);
    text.textContent = `Kapasitas sampah ${nama.toLowerCase()} hampir penuh! Segera lakukan pengangkutan.`;
  } else {
    box.style.display = "none";
  }
}

function updateDonut(persen) {
  const ctx = document.getElementById("donutChart");
  if (!ctx) return;
  
  const data = {
    datasets: [{
      data: [persen, 100 - persen],
      backgroundColor: ["#7c3aed", "#ede9fe"],
      borderWidth: 0,
    }],
  };
  if (donutChart) {
    donutChart.data = data;
    donutChart.update();
  } else {
    donutChart = new Chart(ctx, {
      type: "doughnut",
      data: data,
      options: { 
        cutout: "78%", 
        responsive: true,
        maintainAspectRatio: false,
        plugins: { 
          legend: { display: false }, 
          tooltip: { enabled: false } 
        } 
      },
    });
  }
}

function updateLineChart(grafik) {
  const ctx = document.getElementById("lineChart");
  if (!ctx) return;

  // Update the time badge in header
  if (grafik.waktu && grafik.waktu.length > 0) {
    const latestTime = grafik.waktu[grafik.waktu.length - 1];
    document.getElementById("chart-time-badge").textContent = latestTime;
  }

  const datasets = [
    { 
      label: "Organik", 
      data: grafik.organik, 
      borderColor: "#16a34a", 
      backgroundColor: "transparent", 
      tension: 0.35, 
      pointRadius: 4,
      pointBackgroundColor: "#16a34a",
      pointBorderColor: "#ffffff",
      pointBorderWidth: 2,
    },
    { 
      label: "Anorganik", 
      data: grafik.anorganik, 
      borderColor: "#2563eb", 
      backgroundColor: "transparent", 
      tension: 0.35, 
      pointRadius: 4,
      pointBackgroundColor: "#2563eb",
      pointBorderColor: "#ffffff",
      pointBorderWidth: 2,
    },
    { 
      label: "Residu", 
      data: grafik.residu, 
      borderColor: "#9ca3af", 
      backgroundColor: "transparent", 
      tension: 0.35, 
      pointRadius: 4,
      pointBackgroundColor: "#9ca3af",
      pointBorderColor: "#ffffff",
      pointBorderWidth: 2,
    },
  ];

  if (lineChart) {
    lineChart.data.labels = grafik.waktu;
    lineChart.data.datasets = datasets;
    lineChart.update();
  } else {
    lineChart = new Chart(ctx, {
      type: "line",
      data: { labels: grafik.waktu, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { 
            min: 0, 
            max: 100, 
            grid: { color: "#f1f5f9" },
            ticks: {
              stepSize: 25
            }
          },
          x: { 
            grid: { display: false } 
          },
        },
      },
    });
  }
}

function updateKlasifikasiTable(rows) {
  const body = document.getElementById("klasifikasi-body");
  if (!rows || rows.length === 0) {
    body.innerHTML = '<tr><td colspan="5" class="empty-row">Belum ada data klasifikasi</td></tr>';
    return;
  }
  body.innerHTML = rows.map((r) => {
    // Show full timestamp for riwayat e.g. 10:30:21
    const waktuFormatted = r.waktu.split(" ")[1] || r.waktu;
    return `<tr>
      <td>${waktuFormatted}</td>
      <td><span class="img-placeholder"></span></td>
      <td>${r.nama_objek}</td>
      <td><span class="jenis-tag ${jenisTagClass(r.jenis)}">${r.jenis}</span></td>
      <td>${r.confidence.toFixed(1)}%</td>
    </tr>`;
  }).join("");
}

function updateNotifList(rows) {
  const list = document.getElementById("notif-list");
  if (!rows || rows.length === 0) {
    list.innerHTML = '<div class="empty-row">Belum ada notifikasi</div>';
    return;
  }
  const iconFor = (tipe) => (tipe === "warning" ? "⚠️" : tipe === "success" ? "✅" : "ℹ️");
  const bgClassFor = (tipe) => (tipe === "warning" ? "notif-bg-warning" : tipe === "success" ? "notif-bg-success" : "notif-bg-info");
  const dotClassFor = (tipe) => (tipe === "warning" ? "dot-red" : "dot-gray");

  list.innerHTML = rows.map((n) => {
    const jam = n.waktu.split(" ")[1] || n.waktu;
    return `<div class="notif-item">
      <div class="notif-left">
        <div class="notif-icon-circle ${bgClassFor(n.tipe)}">${iconFor(n.tipe)}</div>
        <div class="notif-details">
          <div class="notif-title">${n.judul}</div>
          <div class="notif-msg">${jam} - ${n.pesan}</div>
        </div>
      </div>
      <div class="notif-dot ${dotClassFor(n.tipe)}"></div>
    </div>`;
  }).join("");
}

async function refreshDashboard() {
  try {
    const res = await fetch("/api/dashboard-data");
    if (!res.ok) throw new Error("Gagal mengambil data");
    const data = await res.json();

    updateCards(data.kapasitas);
    updateLineChart(data.grafik);
    updateKlasifikasiTable(data.klasifikasi);
    updateNotifList(data.notifikasi);
  } catch (err) {
    console.error("Gagal refresh dashboard:", err);
  }
}

refreshDashboard();
setInterval(refreshDashboard, POLL_INTERVAL_MS);
