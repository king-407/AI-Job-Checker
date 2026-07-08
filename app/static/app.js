const state = {
  sessionId: null,
  analysis: null,
};

const els = {
  resumeText: document.querySelector("#resumeText"),
  jobText: document.querySelector("#jobText"),
  resumeFile: document.querySelector("#resumeFile"),
  sampleButton: document.querySelector("#sampleButton"),
  analyzeButton: document.querySelector("#analyzeButton"),
  statusText: document.querySelector("#statusText"),
  sessionPill: document.querySelector("#sessionPill"),
  resultsLayout: document.querySelector("#resultsLayout"),
  scoreValue: document.querySelector("#scoreValue"),
  verdictText: document.querySelector("#verdictText"),
  breakdownList: document.querySelector("#breakdownList"),
  reportContent: document.querySelector("#reportContent"),
  matchedRequired: document.querySelector("#matchedRequired"),
  missingRequired: document.querySelector("#missingRequired"),
  matchedPreferred: document.querySelector("#matchedPreferred"),
  missingPreferred: document.querySelector("#missingPreferred"),
  chatForm: document.querySelector("#chatForm"),
  chatInput: document.querySelector("#chatInput"),
  chatLog: document.querySelector("#chatLog"),
};

const sampleResume = `My name is Shivam Tiwari. I am a junior AI/backend developer with around 1 year of project experience. I know Python, FastAPI, REST APIs, Pydantic, Git, OpenAI Agents SDK, Gemini API, prompt engineering, and basic React.

Projects:
- AI sales email generator using multiple agents and structured outputs.
- Research report agent using planner, search, writer, and email workflow.
- Job-fit analysis tool using FastAPI, OpenAI Agents SDK, session memory, and deterministic scoring.

I have built tools that parse user input, call LLMs, use structured Pydantic models, and generate readable reports.`;

const sampleJob = `We are hiring an AI Engineer Intern to build LLM-powered tools and backend APIs.

Required skills: Python, FastAPI, REST APIs, LLMs, Git, and prompt engineering.

Preferred skills: RAG, vector databases, LangChain, React, and cloud deployment.

Responsibilities include building AI agents, creating APIs, integrating LLM outputs into user-facing workflows, and improving evaluation quality. This is an intern or junior role.`;

function setStatus(message) {
  els.statusText.textContent = message;
}

function setBusy(isBusy) {
  els.analyzeButton.disabled = isBusy;
  els.analyzeButton.textContent = isBusy ? "Analyzing..." : "Analyze Fit";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMarkdown(markdown) {
  const lines = escapeHtml(markdown).split("\n");
  let html = "";
  let listType = null;

  const inlineMarkdown = (value) =>
    value.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  const closeList = () => {
    if (listType) {
      html += `</${listType}>`;
      listType = null;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      closeList();
      continue;
    }

    if (line.startsWith("# ")) {
      closeList();
      html += `<h1>${inlineMarkdown(line.slice(2))}</h1>`;
    } else if (line.startsWith("## ")) {
      closeList();
      html += `<h2>${inlineMarkdown(line.slice(3))}</h2>`;
    } else if (line.startsWith("### ")) {
      closeList();
      html += `<h3>${inlineMarkdown(line.slice(4))}</h3>`;
    } else if (/^[-*]\s+/.test(line)) {
      if (listType !== "ul") {
        closeList();
        html += "<ul>";
        listType = "ul";
      }
      html += `<li>${inlineMarkdown(line.replace(/^[-*]\s+/, ""))}</li>`;
    } else if (/^\d+\.\s+/.test(line)) {
      if (listType !== "ol") {
        closeList();
        html += "<ol>";
        listType = "ol";
      }
      html += `<li>${inlineMarkdown(line.replace(/^\d+\.\s+/, ""))}</li>`;
    } else {
      closeList();
      html += `<p>${inlineMarkdown(line)}</p>`;
    }
  }

  closeList();

  return html;
}

function renderList(element, values) {
  const items = values?.length ? values : ["None listed"];
  element.innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderBreakdown(breakdown) {
  const metrics = [
    ["Required skills", breakdown.required_skills, 40],
    ["Relevant experience", breakdown.relevant_experience, 25],
    ["Project/domain match", breakdown.project_domain_match, 15],
    ["Preferred skills", breakdown.preferred_skills, 10],
    ["Seniority fit", breakdown.seniority_fit, 10],
  ];

  els.breakdownList.innerHTML = metrics
    .map(([label, value, max]) => {
      const percent = Math.max(0, Math.min(100, (Number(value) / max) * 100));
      return `
        <div class="metric">
          <div class="metric-label">
            <span>${label}</span>
            <strong>${Number(value).toFixed(1)} / ${max}</strong>
          </div>
          <div class="metric-bar"><span style="width: ${percent}%"></span></div>
        </div>
      `;
    })
    .join("");
}

function renderAnalysis(data) {
  state.analysis = data;
  state.sessionId = data.session_id;
  els.sessionPill.textContent = `Session ${data.session_id}`;
  els.resultsLayout.hidden = false;

  const score = Math.round(data.deterministic_score.total_score);
  els.scoreValue.textContent = score;
  els.verdictText.textContent = data.fit_analysis.verdict.replaceAll("_", " ");
  renderBreakdown(data.deterministic_score.breakdown);

  els.reportContent.innerHTML = renderMarkdown(data.report.markdown_report);

  renderList(els.matchedRequired, data.deterministic_score.matched_required_skills);
  renderList(els.missingRequired, data.deterministic_score.missing_required_skills);
  renderList(els.matchedPreferred, data.deterministic_score.matched_preferred_skills);
  renderList(els.missingPreferred, data.deterministic_score.missing_preferred_skills);

  els.chatLog.innerHTML = `
    <div class="message assistant">
      Analysis is ready. Ask how to improve the resume, prepare for interviews, or close skill gaps.
    </div>
  `;
}

async function analyzeFit() {
  const resumeText = els.resumeText.value.trim();
  const jobDescription = els.jobText.value.trim();

  if (resumeText.length < 50 || jobDescription.length < 50) {
    setStatus("Add at least 50 characters for both resume and job description.");
    return;
  }

  setBusy(true);
  setStatus("Running agents: resume parser, job analyzer, scoring tool, fit scorer, and report writer.");

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resume_text: resumeText,
        job_description: jobDescription,
        session_id: state.sessionId,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Analysis failed");
    }

    const data = await response.json();
    renderAnalysis(data);
    setStatus("Analysis complete.");
  } catch (error) {
    setStatus(error.message);
  } finally {
    setBusy(false);
  }
}

async function uploadResumePdf(file) {
  const formData = new FormData();
  formData.append("file", file);
  setStatus("Extracting resume text from PDF...");

  try {
    const response = await fetch("/extract-resume-text", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Could not extract PDF text");
    }

    const data = await response.json();
    els.resumeText.value = data.text;
    setStatus("Resume text extracted. Add the job description and analyze.");
  } catch (error) {
    setStatus(error.message);
  }
}

function addMessage(role, content) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  if (role === "assistant") {
    message.innerHTML = renderMarkdown(content);
  } else {
    message.textContent = content;
  }
  els.chatLog.appendChild(message);
  els.chatLog.scrollTop = els.chatLog.scrollHeight;
}

async function askFollowUp(event) {
  event.preventDefault();
  const message = els.chatInput.value.trim();

  if (!message || !state.sessionId) {
    return;
  }

  els.chatInput.value = "";
  addMessage("user", message);
  els.chatForm.querySelector("button").disabled = true;

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        message,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Follow-up failed");
    }

    const data = await response.json();
    addMessage("assistant", data.answer);
  } catch (error) {
    addMessage("assistant", error.message);
  } finally {
    els.chatForm.querySelector("button").disabled = false;
  }
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));

    button.classList.add("active");
    document.querySelector(`#${button.dataset.tab}Tab`).classList.add("active");
  });
});

els.sampleButton.addEventListener("click", () => {
  els.resumeText.value = sampleResume;
  els.jobText.value = sampleJob;
  setStatus("Sample data loaded.");
});

els.analyzeButton.addEventListener("click", analyzeFit);
els.resumeFile.addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (file) {
    uploadResumePdf(file);
  }
});
els.chatForm.addEventListener("submit", askFollowUp);
