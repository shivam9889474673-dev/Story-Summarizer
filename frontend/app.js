const API_URL = "http://127.0.0.1:8000/api/summarize";

const storyInput = document.querySelector("#story-input");
const summarizeButton = document.querySelector("#summarize-button");
const buttonLabel = summarizeButton.querySelector(".button-label");
const errorMessage = document.querySelector("#error-message");
const resultSection = document.querySelector("#result-section");
const summaryOutput = document.querySelector("#summary-output");

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
}

function displaySummary(summary) {
  const fragment = document.createDocumentFragment();

  const plainText = summary.replace(/<\/?h[1-6]\b[^>]*>/gi, "");
  for (const line of plainText.split(/\r?\n/)) {
    const text = line
      .trim()
      .replace(/^#{1,6}\s*/, "")
      .replace(/^\*\*(.*?)\*\*$/, "$1")
      .replace(/-Bold$/, "")
      .trim();
    if (!text) {
      continue;
    }

    const isSectionHeading = /^(CHARACTER|THEME|SUMMARY)$/i.test(text);
    const isTitleHeading = /^SUMMARY\s*[—–-]\s*\S/i.test(text);
    const lineElement = document.createElement(isSectionHeading || isTitleHeading ? "h3" : "p");
    lineElement.textContent = text;
    fragment.append(lineElement);
  }

  summaryOutput.replaceChildren(fragment);
}

summarizeButton.addEventListener("click", async () => {
  const story = storyInput.value.trim();
  errorMessage.hidden = true;

  if (!story) {
    showError("Please enter a story before summarizing.");
    storyInput.focus();
    return;
  }

  summarizeButton.disabled = true;
  buttonLabel.textContent = "Summarizing...";
  resultSection.hidden = true;

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ story }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "We couldn't summarize your story. Please try again.");
    }

    displaySummary(data.summary);
    resultSection.hidden = false;
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    if (error instanceof TypeError) {
      showError("Couldn't connect to the summarization service. Check that the backend is running.");
    } else {
      showError(error.message);
    }
  } finally {
    summarizeButton.disabled = false;
    buttonLabel.textContent = "Summarize story";
  }
});
