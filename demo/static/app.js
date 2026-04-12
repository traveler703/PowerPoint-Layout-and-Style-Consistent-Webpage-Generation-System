const notes = document.getElementById("notes");
const btn = document.getElementById("btn-generate");
const statusEl = document.getElementById("status");
const preview = document.getElementById("preview");
const report = document.getElementById("report");

btn.addEventListener("click", async () => {
  statusEl.textContent = "生成中…";
  btn.disabled = true;
  report.hidden = true;
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: notes.value }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    preview.srcdoc = data.html;
    report.textContent = JSON.stringify(data.report, null, 2);
    report.hidden = false;
    statusEl.textContent = "完成";
  } catch (e) {
    console.error(e);
    statusEl.textContent = "失败，请确认 demo 服务已启动";
  } finally {
    btn.disabled = false;
  }
});
