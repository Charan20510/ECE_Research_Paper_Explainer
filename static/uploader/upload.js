(() => {
  // Drag & drop support for file input
  const dropArea = document.getElementById('drop-area');
  const fileInput = document.getElementById('file-input');
  const fileNameEl = document.getElementById('file-name');
  const uploadForm = document.querySelector('.upload-form');

  if (!dropArea || !fileInput) return;

  // Prevent default drag behaviors
  const prevent = (e) => { 
    e.preventDefault(); 
    e.stopPropagation(); 
  };

  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
    dropArea.addEventListener(evt, prevent, false);
    document.body.addEventListener(evt, prevent, false);
  });

  // Highlight drop area when dragging over it
  ['dragenter', 'dragover'].forEach(evt => {
    dropArea.addEventListener(evt, () => {
      dropArea.classList.add('dragover');
    }, false);
  });

  ['dragleave', 'drop'].forEach(evt => {
    dropArea.addEventListener(evt, () => {
      dropArea.classList.remove('dragover');
    }, false);
  });

  // Handle drop
  dropArea.addEventListener('drop', (e) => {
    dropArea.classList.remove('dragover');
    const dt = e.dataTransfer;
    if (!dt || !dt.files || dt.files.length === 0) return;
    
    const files = dt.files;
    const first = files[0];
    
    // Validate file type
    if (!validateFile(first)) {
      showError('❌ Invalid file type. Please upload PDF, images, or documents.');
      return;
    }

    // Validate file size (max 50MB)
    if (first.size > 50 * 1024 * 1024) {
      showError('❌ File too large. Maximum size is 50MB.');
      return;
    }

    // Use DataTransfer to set fileInput.files (works in modern browsers)
    try {
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(first);
      fileInput.files = dataTransfer.files;
      showFileName(first.name, first.size);
    } catch (err) {
      showFileName(first.name + ' (drop received, please click Upload files)', first.size);
    }
  }, false);

  // Handle manual file selection
  fileInput.addEventListener('change', (e) => {
    const f = fileInput.files && fileInput.files[0];
    if (f) {
      if (!validateFile(f)) {
        showError('❌ Invalid file type. Please upload PDF, images, or documents.');
        fileInput.value = '';
        return;
      }
      if (f.size > 50 * 1024 * 1024) {
        showError('❌ File too large. Maximum size is 50MB.');
        fileInput.value = '';
        return;
      }
      showFileName(f.name, f.size);
    }
  });

  // Input element is already inside the label, so clicking the label
  // naturally forwards the click to the hidden file input.  The previous
  // handler manually invoked `fileInput.click()` which caused the file
  // chooser to open twice; remove the extra listener.

  // Form submission feedback
  if (uploadForm) {
    uploadForm.addEventListener('submit', (e) => {
      const hasFile = fileInput.files && fileInput.files.length > 0;
      if (!hasFile) {
        e.preventDefault();
        showError('⚠️ Please select a file first');
      } else {
        // Show loading state
        const submitBtn = uploadForm.querySelector('button[type="submit"]');
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = '⏳ Processing...';
          submitBtn.style.opacity = '0.7';
        }
      }
    });
  }

  function validateFile(file) {
    const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/gif', 'text/plain', 
                       'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const validExtensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.txt', '.doc', '.docx'];
    
    const isValidType = validTypes.some(type => file.type.includes(type));
    const isValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
    
    return isValidType || isValidExtension;
  }

  function showFileName(name, size) {
    if (!fileNameEl) return;
    const sizeStr = formatFileSize(size);
    fileNameEl.innerHTML = `✅ Selected: <strong>${name}</strong> (${sizeStr})`;
    fileNameEl.style.color = '#10B981';
  }

  function showError(message) {
    if (!fileNameEl) return;
    fileNameEl.innerHTML = `${message}`;
    fileNameEl.style.color = '#EF4444';
    setTimeout(() => {
      fileNameEl.innerHTML = '';
    }, 5000);
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }
})();