const generateBtn = document.getElementById('generateBtn');
const mood = document.getElementById('mood');
const language = document.getElementById('language');
const statusBox = document.getElementById('status');
const scriptOutput = document.getElementById('scriptOutput');
const result = document.getElementById('result');
const preview = document.getElementById('preview');
const downloadLink = document.getElementById('downloadLink');

generateBtn.addEventListener('click', async () => {
  statusBox.textContent = 'Generating video... this can take 1-2 minutes.';
  result.classList.add('hidden');
  scriptOutput.textContent = '';

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mood: mood.value, language: language.value })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Generation failed');

    scriptOutput.textContent = data.script;
    preview.src = data.download_url;
    downloadLink.href = data.download_url;
    result.classList.remove('hidden');
    statusBox.textContent = 'Done. Video generated successfully.';
  } catch (err) {
    statusBox.textContent = `Error: ${err.message}`;
  }
});
