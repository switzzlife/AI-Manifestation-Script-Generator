document.addEventListener('DOMContentLoaded', function() {
    const postForm = document.getElementById('post-form');
    const commentForms = document.querySelectorAll('.comment-form');

    if (postForm) {
        postForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(postForm);
            fetch('/create_post', {
                method: 'POST',
                body: formData
            }).then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error creating post');
                }
            });
        });
    }

    commentForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(form);
            const postId = form.getAttribute('data-post-id');
            fetch(`/add_comment/${postId}`, {
                method: 'POST',
                body: formData
            }).then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error adding comment');
                }
            });
        });
    });
});
