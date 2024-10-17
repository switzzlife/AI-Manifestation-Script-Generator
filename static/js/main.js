document.addEventListener('DOMContentLoaded', function() {
    // Add any global JavaScript functionality here
    console.log('Main JavaScript loaded');
});

function previewProfilePhoto(event) {
    const reader = new FileReader();
    reader.onload = function() {
        const output = document.getElementById('profile-photo-preview');
        output.src = reader.result;
    }
    reader.readAsDataURL(event.target.files[0]);
}
