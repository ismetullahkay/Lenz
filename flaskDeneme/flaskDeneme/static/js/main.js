// main.js

function confirmDelete(detectionId, nesneAdi) {
    if (confirm(currentUserID + ' index silmek istediğinizden emin misiniz?')) {
        // Silme işlemi için bir AJAX isteği gönderin
        var currentUserID = {{ current_user_id|tojson }};
        fetch('/delete_detection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ user_id: currentUserID, detection_id: detectionId, nesne_adi: nesneAdi }),
        })
        .then(response => response.json())
        .then(data => {
            // Silme işlemi başarılıysa sayfayı yeniden yükleyin
            location.reload();
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    }
}
