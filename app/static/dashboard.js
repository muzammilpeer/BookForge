function text(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatPercent(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function jobRow(job, selected) {
  const output = job.output_filename
    ? escapeHtml(job.output_filename)
    : '<span class="muted">Not ready</span>';
  const mimika = job.mimika_job_id ? ` · Mimika ${escapeHtml(job.mimika_job_id)}` : "";
  const chars = job.chars_per_sec ? ` · ${Number(job.chars_per_sec).toFixed(0)} chars/sec` : "";
  const started = job.started_at ? `<br>Started ${escapeHtml(job.started_at)}` : "";
  const completed = job.completed_at ? `<br>Done ${escapeHtml(job.completed_at)}` : "";
  const eta = job.eta_formatted ? `<br>ETA ${escapeHtml(job.eta_formatted)}` : "";
  const download = job.has_output
    ? `<a class="button compact primary" href="/jobs/${job.id}/download">Download</a>`
    : "";
  const cancel = job.can_cancel
    ? `<form action="/jobs/${job.id}/cancel" method="post"><button class="button compact danger" type="submit">Cancel</button></form>`
    : "";
  return `
    <tr data-job-id="${job.id}">
      <td class="select-col">
        <input form="bulk-actions" type="checkbox" name="job_ids" value="${job.id}" ${selected ? "checked" : ""} aria-label="Select ${escapeHtml(job.title)}">
      </td>
      <td><span class="badge ${escapeHtml(job.display_status || job.status)}">${escapeHtml(job.display_status || job.status)}</span></td>
      <td class="progress-col">
        <div class="progress"><span style="width: ${Number(job.progress || 0)}%"></span></div>
        <small>${formatPercent(job.progress)}${chars}</small>
      </td>
      <td>
        <a class="table-title" href="/jobs/${job.id}">${escapeHtml(job.title)}</a>
        <small>ID ${job.id}${mimika}</small>
      </td>
      <td class="file-col">${escapeHtml(job.input_filename)}</td>
      <td class="file-col">${output}</td>
      <td><strong>${escapeHtml(job.tts_model)}</strong><small>${escapeHtml(job.voice)} · ${escapeHtml(job.output_format)}</small></td>
      <td><small>Created ${escapeHtml(job.created_at)}${started}${completed}${eta}</small></td>
      <td class="row-actions">
        <a class="button compact" href="/jobs/${job.id}">Track</a>
        ${download}
        ${cancel}
      </td>
    </tr>`;
}

function selectedJobIds() {
  return new Set(
    Array.from(document.querySelectorAll('input[name="job_ids"]:checked')).map((box) => box.value),
  );
}

function updateDashboard(state) {
  if (state.health) {
    const healthState = document.getElementById("health-state");
    if (healthState) {
      healthState.textContent = state.health.ok ? "Online" : "Offline";
      healthState.className = state.health.ok ? "ok" : "bad";
    }
    text("health-detail", state.health.detail || "");
  }
  text("running-count", `${state.running_count} / ${state.max_parallel_jobs}`);
  text("available-slots", `${state.available_slots} slot${state.available_slots === 1 ? "" : "s"} available`);
  text("queued-count", state.counts.queued);
  text("completed-count", state.counts.completed);
  text("stopped-count", Number(state.counts.failed || 0) + Number(state.counts.canceled || 0));
  text("stopped-detail", `${state.counts.failed} failed, ${state.counts.canceled} canceled`);
  text("cpu-usage", `${Number(state.system?.cpu?.usage_percent || 0).toFixed(1)}%`);
  text(
    "cpu-detail",
    `${state.system?.cpu?.cores || 0} cores · load ${state.system?.cpu?.load_1m ?? "unknown"}`,
  );
  text("memory-available", state.system?.memory?.available_human || "Unknown");
  text(
    "memory-detail",
    `${state.system?.memory?.used_percent ?? "Unknown"}% used of ${state.system?.memory?.total_human || "Unknown"}`,
  );
  const gpuUsage = state.system?.gpu?.usage_percent;
  text("gpu-usage", gpuUsage === null || gpuUsage === undefined ? "N/A" : `${Number(gpuUsage).toFixed(1)}%`);
  text("gpu-detail", state.system?.gpu?.detail || "GPU metric unavailable");

  const tbody = document.getElementById("jobs-table-body");
  if (!tbody) return;
  const selected = selectedJobIds();
  if (!state.jobs.length) {
    tbody.innerHTML = '<tr data-empty-row><td colspan="9" class="empty-table">No jobs yet. Upload a book to start the queue.</td></tr>';
    return;
  }
  tbody.innerHTML = state.jobs.map((job) => jobRow(job, selected.has(String(job.id)))).join("");
}

document.querySelectorAll("[data-select-all]").forEach((toggle) => {
  toggle.addEventListener("change", () => {
    document.querySelectorAll('input[name="job_ids"]').forEach((box) => {
      box.checked = toggle.checked;
    });
  });
});

const source = new EventSource("/events/dashboard");
source.addEventListener("dashboard", (event) => {
  const state = JSON.parse(event.data);
  text("live-state", `Live updates every ${state.sse_interval_seconds}s`);
  updateDashboard(state);
});
source.onerror = () => {
  text("live-state", "Live updates reconnecting");
};
