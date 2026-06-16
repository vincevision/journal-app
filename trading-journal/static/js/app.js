// ═══════════════════════════════════════════════
// SMC Trading Journal — Frontend JS
// ═══════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // File input preview
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                const maxSize = 10 * 1024 * 1024; // 10MB per file
                if (file.size > maxSize) {
                    alert('File is too large. Max 10MB per screenshot.');
                    this.value = '';
                }
            }
        });
    });
});