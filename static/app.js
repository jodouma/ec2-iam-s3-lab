const statusBanner = document.getElementById('statusBanner');
const summaryCard = document.getElementById('summaryCard');
const fixCard = document.getElementById('fixCard');
const diagnosticsCard = document.getElementById('diagnosticsCard');
const identityCard = document.getElementById('identityCard');
const technicalDetails = document.getElementById('technicalDetails');
const gallerySection = document.getElementById('gallerySection');
const galleryGrid = document.getElementById('galleryGrid');
const galleryCount = document.getElementById('galleryCount');
const refreshBtn = document.getElementById('refreshBtn');
const uploadBtn = document.getElementById('uploadBtn');
const fileInput = document.getElementById('fileInput');
const bucketInput = document.getElementById('bucketInput');
const applyBucketBtn = document.getElementById('applyBucketBtn');
const bucketHelpText = document.getElementById('bucketHelpText');
const appConfig = {
    bucketName: document.body.dataset.bucketName,
    defaultBucketName: document.body.dataset.defaultBucketName,
    region: document.body.dataset.region,
    uploadPrefix: document.body.dataset.uploadPrefix
};

let latestDiagnostics = null;

function bannerIcon(theme) {
    return {
        success: '🎉',
        warning: '🚧',
        danger: '🛑',
        loading: '⏳'
    }[theme] || 'ℹ️';
}

function escapeHtml(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function setStatusBanner(state) {
    statusBanner.className = `status-banner ${state.theme}`;
    statusBanner.innerHTML = `
        <div class="status-icon">${bannerIcon(state.theme)}</div>
        <div>
            <h2>${escapeHtml(state.title)}</h2>
            <p>${escapeHtml(state.summary)}</p>
        </div>
    `;
}

function renderCallouts(state) {
    summaryCard.innerHTML = `
        <div class="callout">
            <span class="callout-label">Classroom explanation</span>
            ${escapeHtml(state.summary)}
        </div>
        <div class="callout">
            <span class="callout-label">Likely missing AWS action</span>
            ${escapeHtml(state.likely_missing_action)}
        </div>
    `;

    fixCard.innerHTML = `
        <div class="callout">
            <span class="callout-label">Proposed fix</span>
            ${escapeHtml(state.proposed_fix)}
        </div>
        <div class="callout">
            <span class="callout-label">Teaching note</span>
            Change only one permission at a time so students can clearly see how each AWS action changes the app behavior.
        </div>
    `;
}

function renderDiagnostics(diag) {
    const labels = {
        credentials: 'Step A: credentials available?',
        list_bucket: 'Step B: can list the bucket?',
        read_object: 'Step C: can read an image object?',
        upload_object: 'Step D: can upload a demo image?'
    };

    diagnosticsCard.innerHTML = Object.entries(diag.steps)
        .map(([key, value]) => {
            const ok = value.ok;
            const details = value.details ? escapeHtml(JSON.stringify(value.details)) : 'No extra details';
            const error = value.error ? escapeHtml(JSON.stringify(value.error)) : '';
            return `
                <div class="diagnostic-step ${ok ? 'ok' : 'fail'}">
                    <div class="diagnostic-icon">${ok ? '✅' : '❌'}</div>
                    <div>
                        <strong>${escapeHtml(labels[key] || key)}</strong>
                        <div>${ok ? 'Succeeded' : 'Failed'}</div>
                        <small>${ok ? details : error}</small>
                    </div>
                </div>
            `;
        })
        .join('');
}

function renderIdentity(diag) {
    const identity = diag.identity || {};
    const lines = [
        `Credential source: ${diag.credential_source || 'Not detected'}`,
        `Credentials available: ${diag.credentials_available ? 'yes' : 'no'}`,
        `Bucket: ${diag.bucket}`,
        `Region: ${diag.region || 'auto/default'}`,
        ''
    ];

    if (identity.error) {
        lines.push('STS identity lookup failed:');
        lines.push(JSON.stringify(identity.error, null, 2));
    } else if (identity.arn) {
        lines.push(`Account: ${identity.account}`);
        lines.push(`ARN: ${identity.arn}`);
        lines.push(`User ID: ${identity.user_id}`);
    } else {
        lines.push('No identity information available.');
    }

    identityCard.textContent = lines.join('\n');
}

function updateBucketText(bucketName) {
    appConfig.bucketName = bucketName;
    document.body.dataset.bucketName = bucketName;
    if (bucketInput) {
        bucketInput.value = bucketName;
    }
    if (bucketHelpText) {
        bucketHelpText.innerHTML = `Active bucket: <strong>${escapeHtml(bucketName)}</strong> · Default classroom bucket: <strong>${escapeHtml(appConfig.defaultBucketName)}</strong>`;
    }
}

function renderGallery(images, canRead) {
    if (!canRead) {
        gallerySection.classList.add('hidden');
        galleryGrid.innerHTML = '';
        galleryCount.textContent = '0 images';
        return;
    }

    gallerySection.classList.remove('hidden');
    galleryCount.textContent = `${images.length} image${images.length === 1 ? '' : 's'}`;

    if (!images.length) {
        galleryGrid.innerHTML = `
            <div class="callout">
                Listing worked, but no matching image files were found in the bucket yet. Upload one to continue the demo.
            </div>
        `;
        return;
    }

    galleryGrid.innerHTML = images.map((image, index) => `
        <article class="gallery-item" style="animation-delay:${index * 50}ms">
            <img src="${encodeURI(image.url)}" alt="${escapeHtml(image.key)}" loading="lazy" />
            <div class="gallery-caption">
                <strong>${escapeHtml(image.key.split('/').pop())}</strong><br />
                <small>${escapeHtml(image.key)}</small>
            </div>
        </article>
    `).join('');
}

function renderTechnicalDetails(diag) {
    technicalDetails.textContent = JSON.stringify(diag, null, 2);
}

function updateUploadButtonState() {
    const selectedCount = (fileInput?.files || []).length;
    uploadBtn.classList.toggle('ready', selectedCount > 0);
    uploadBtn.textContent = selectedCount > 0
        ? `Upload ${selectedCount} Selected Image${selectedCount === 1 ? '' : 's'}`
        : 'Upload Selected Images';
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data?.message || 'Request failed');
    }
    return data;
}

async function loadDiagnostics() {
    refreshBtn.disabled = true;
    setStatusBanner({ title: 'Running diagnostics…', summary: 'Checking credentials and S3 permissions.', theme: 'loading' });
    try {
        const diagnostics = await fetchJson('/api/diagnostics');
        latestDiagnostics = diagnostics;
        updateBucketText(diagnostics.bucket);
        setStatusBanner(diagnostics.state);
        renderCallouts(diagnostics.state);
        renderDiagnostics(diagnostics);
        renderIdentity(diagnostics);
        renderTechnicalDetails(diagnostics);

        const canRead = diagnostics.steps.read_object.ok;
        if (canRead) {
            const imagesData = await fetchJson('/api/images');
            renderGallery(imagesData.images, true);
        } else {
            renderGallery([], false);
        }
    } catch (error) {
        setStatusBanner({
            title: 'Unexpected application error',
            summary: error.message || 'The frontend could not load diagnostics.',
            theme: 'danger'
        });
        technicalDetails.textContent = error.stack || String(error);
    } finally {
        refreshBtn.disabled = false;
    }
}

async function applyBucketChange() {
    const nextBucket = bucketInput.value.trim();
    if (!nextBucket) {
        alert('Please enter a bucket name.');
        return;
    }

    applyBucketBtn.disabled = true;
    try {
        const result = await fetchJson('/api/config/bucket', {
            method: 'POST',
            body: JSON.stringify({ bucket_name: nextBucket })
        });
        updateBucketText(result.bucket_name);
        await loadDiagnostics();
    } catch (error) {
        alert(`Could not change bucket: ${error.message}`);
    } finally {
        applyBucketBtn.disabled = false;
    }
}

async function uploadDemoImage() {
    uploadBtn.disabled = true;
    try {
        const selectedFiles = Array.from(fileInput.files || []);
        let result;

        if (selectedFiles.length) {
            const formData = new FormData();
            selectedFiles.forEach((file) => formData.append('files', file));

            const response = await fetch('/api/upload-demo-image', {
                method: 'POST',
                body: formData
            });
            result = await response.json();
            if (!response.ok) {
                throw new Error(result?.message || 'Upload failed');
            }
        } else {
            const stamp = new Date().toISOString();
            result = await fetchJson('/api/upload-demo-image', {
                method: 'POST',
                body: JSON.stringify({ text: `IAM Lab Upload\n${stamp}` })
            });
        }

        await loadDiagnostics();
        if (result.reused_existing) {
            alert(`Existing demo image reused: ${result.key}`);
        } else if (result.uploaded?.length) {
            alert(`Upload succeeded: ${result.uploaded.length} file(s) uploaded.`);
            fileInput.value = '';
            updateUploadButtonState();
        } else {
            alert(`Upload succeeded: ${result.key}`);
        }
    } catch (error) {
        alert(`Upload failed: ${error.message}`);
        await loadDiagnostics();
    } finally {
        uploadBtn.disabled = false;
    }
}

refreshBtn.addEventListener('click', loadDiagnostics);
uploadBtn.addEventListener('click', uploadDemoImage);
applyBucketBtn.addEventListener('click', applyBucketChange);
fileInput.addEventListener('change', updateUploadButtonState);
window.addEventListener('DOMContentLoaded', loadDiagnostics);