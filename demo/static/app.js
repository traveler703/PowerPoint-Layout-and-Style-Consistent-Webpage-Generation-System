const notes = document.getElementById("notes");
const btn = document.getElementById("btn-generate");
const btnExport = document.getElementById("btn-export");
const btnCopy = document.getElementById("btn-copy");
const statusEl = document.getElementById("status");
const preview = document.getElementById("preview");
const mdPreview = document.getElementById("md-preview");
const report = document.getElementById("report");
const themeSel = document.getElementById("theme");
const formatSel = document.getElementById("format");
const useLc = document.getElementById("useLc");

let lastPayload = { content: "", format: "html" };

async function loadThemes() {
  try {
    const res = await fetch("/api/themes");
    if (!res.ok) return;
    const data = await res.json();
    themeSel.innerHTML = "";
    for (const t of data.themes || []) {
      const opt = document.createElement("option");
      opt.value = t.id;
      opt.textContent = t.id;
      themeSel.appendChild(opt);
    }
  } catch (e) {
    console.warn(e);
  }
}

function setPreview() {
  if (lastPayload.format === "markdown") {
    preview.srcdoc = "";
    preview.hidden = true;
    mdPreview.hidden = false;
    mdPreview.textContent = lastPayload.content;
  } else {
    mdPreview.hidden = true;
    preview.hidden = false;
    preview.srcdoc = lastPayload.content;
  }
}

btn.addEventListener("click", async () => {
  statusEl.textContent = "生成中…";
  btn.disabled = true;
  btnExport.disabled = true;
  btnCopy.disabled = true;
  report.hidden = true;
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: notes.value,
        theme_id: themeSel.value || "business_blue",
        output_format: formatSel.value,
        prefer_langchain: useLc.checked,
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    lastPayload = { content: data.content, format: data.format };
    setPreview();
    report.textContent = JSON.stringify(data.report, null, 2);
    report.hidden = false;
    btnExport.disabled = false;
    btnCopy.disabled = false;
    statusEl.textContent = "完成";
  } catch (e) {
    console.error(e);
    statusEl.textContent = "失败，请确认服务已启动（uvicorn demo.app:app）";
  } finally {
    btn.disabled = false;
  }
});

btnExport.addEventListener("click", () => {
  const ext = lastPayload.format === "markdown" ? "md" : "html";
  const blob = new Blob([lastPayload.content], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `deck.${ext}`;
  a.click();
  URL.revokeObjectURL(a.href);
});

btnCopy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(lastPayload.content);
    statusEl.textContent = "已复制到剪贴板";
  } catch (e) {
    statusEl.textContent = "复制失败";
  }
});

loadThemes();
