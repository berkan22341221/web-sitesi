document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    $('#dataTable').DataTable({
        "order": [[0, "desc"]],
        "language": {
            "url": "//cdn.datatables.net/plug-ins/1.10.25/i18n/Turkish.json"
        },
        "responsive": true,
        "pageLength": 25
    });

    // Show success/error messages from data attributes
    const flashMessages = JSON.parse(document.getElementById('flash-messages').dataset.messages || '[]');
    flashMessages.forEach(({category, message}) => {
        if (category === 'success') {
            toastr.success(message);
        } else {
            toastr.error(message);
        }
    });
});
